#!/usr/bin/env python3
"""NetOps AI — public API for TUI. All LLM and agent logic lives here."""

from __future__ import annotations

import atexit
import json
import os
import threading
from pathlib import Path
from typing import Annotated, Any, Iterator, TypedDict

from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph.message import add_messages
from langgraph.types import Command
import sqlite3
from langgraph.checkpoint.sqlite import SqliteSaver

# ── Load .env ──────────────────────────────────────────────────────────────────

def _load_dotenv() -> None:
    env_file = Path(__file__).parent / ".env"
    if not env_file.exists():
        return
    with open(env_file, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key = key.strip()
            if key and key not in os.environ:
                os.environ[key] = val.strip()


_load_dotenv()

# ── Shared state types ─────────────────────────────────────────────────────────

class AgentLogEntry(TypedDict):
    timestamp: str
    source: str        # "supervisor" | "monitor_agent" | ...
    event_type: str    # "routing" | "tool_call" | "tool_result" | "approval"
    content: str


class ApprovalRequest(TypedDict):
    agent: str
    action: str
    risk_level: str   # "medium" | "high"
    details: dict


def _append(existing: list, new: list) -> list:
    return (existing or []) + (new or [])


class NetworkOpsState(TypedDict):
    messages:          Annotated[list, add_messages]
    next_agent:        str
    active_agent:      str
    injected_skills:   list[str]
    agent_log:         Annotated[list[AgentLogEntry], _append]
    pending_approval:  ApprovalRequest | None
    approval_decision: str | None
    original_intent:   str


# ── SkillLibrary singleton ─────────────────────────────────────────────────────

from skills import SkillLibrary  # noqa: E402

_skill_lib = SkillLibrary(Path(__file__).parent / "skills")
_skill_lib.start_watcher()
atexit.register(_skill_lib.stop_watcher)

# ── Graph cache ────────────────────────────────────────────────────────────────

_DB_PATH = Path(__file__).parent / "data" / "checkpoints.db"
_DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# WAL checkpoint saat startup agar WAL tidak tumbuh tak terbatas
_wal_conn = sqlite3.connect(str(_DB_PATH), check_same_thread=False)
_wal_conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
_wal_conn.close()

_checkpointer = SqliteSaver(sqlite3.connect(str(_DB_PATH), check_same_thread=False))
_graph: Any = None


def _get_graph() -> Any:
    global _graph
    if _graph is None:
        from agents.graph import build_graph  # noqa: PLC0415
        _graph = build_graph(_checkpointer)
    return _graph


# ── Public API ─────────────────────────────────────────────────────────────────

def create_agent(thread_id: str) -> tuple[Any, RunnableConfig]:
    """Return (compiled_graph, config) for a new or resumed conversation thread."""
    graph = _get_graph()
    config: RunnableConfig = {
        "configurable": {"thread_id": thread_id},
        "recursion_limit": 30,
    }
    return graph, config


def reset_agent(thread_id: str) -> tuple[Any, RunnableConfig]:
    """Clear conversation history for thread_id and return fresh (graph, config)."""
    graph = _get_graph()
    config: RunnableConfig = {
        "configurable": {"thread_id": thread_id},
        "recursion_limit": 30,
    }
    graph.update_state(config, {
        "messages": [], "agent_log": [], "next_agent": "",
        "active_agent": "", "injected_skills": [],
        "pending_approval": None, "approval_decision": None,
        "original_intent": "",
    })
    return graph, config


def cleanup_orphaned_checkpoints() -> int:
    """
    Hapus checkpoint lama dari thread dengan ID numerik (warisan id(self) yang tidak stabil).
    Simpan hanya thread 'tui-*', 'headless', dan thread yang dibuat dalam 7 hari terakhir.
    Return jumlah thread yang dihapus.
    """
    import re as _re
    conn = sqlite3.connect(str(_DB_PATH), check_same_thread=False)
    try:
        cur = conn.execute("SELECT DISTINCT thread_id FROM checkpoints")
        all_threads = [r[0] for r in cur.fetchall()]
        orphan_threads = [
            t for t in all_threads
            if _re.fullmatch(r"\d+", t) or _re.fullmatch(r"\d+-\d+", t)
        ]
        if orphan_threads:
            placeholders = ",".join("?" * len(orphan_threads))
            conn.execute(f"DELETE FROM checkpoints WHERE thread_id IN ({placeholders})", orphan_threads)
            conn.execute(f"DELETE FROM writes WHERE thread_id IN ({placeholders})", orphan_threads)
            conn.commit()
        return len(orphan_threads)
    finally:
        conn.close()
    # VACUUM harus di luar connection yang ada transaksi
    if orphan_threads:
        vconn = sqlite3.connect(str(_DB_PATH), check_same_thread=False)
        vconn.execute("VACUUM")
        vconn.close()


def delete_thread(thread_id: str) -> None:
    """Permanently purge a thread's LangGraph checkpoint state (messages,
    agent_log, pending_approval, etc.) — see tools.db.db_delete_thread() for
    the companion thread-metadata row."""
    conn = sqlite3.connect(str(_DB_PATH), check_same_thread=False)
    try:
        conn.execute("DELETE FROM checkpoints WHERE thread_id = ?", (thread_id,))
        conn.execute("DELETE FROM writes WHERE thread_id = ?", (thread_id,))
        conn.commit()
    finally:
        conn.close()


# agent_log event types already streamed live via the custom writer inside
# _react_loop/config_node (see agents/nodes.py _emit). Skip them when replaying
# a node's batched agent_log from stream_mode="updates" so the UI doesn't see
# each tool call twice — once live, once again when the node returns.
_LIVE_STREAMED_TYPES = {"tool_call", "tool_result", "approval_required"}


def _drain_graph_stream(
    graph: Any,
    config: RunnableConfig,
    stream_input: Any,
    cancel_event: threading.Event | None = None,
) -> Iterator[tuple[str, str]]:
    """Shared consumer for stream_agent_response / resume_after_approval.

    Consumes both "custom" (live per-tool-call events pushed via
    get_stream_writer() from inside nodes) and "updates" (per-node batched
    output, needed for interrupts and final AI messages) stream modes so the
    UI sees each tool call as it happens instead of only after the whole node
    (which may loop over many tool calls) returns.

    If cancel_event is set (operator pressed Stop), the check happens between
    graph steps — before the next node/tool-call is computed — not mid-step,
    since a step already in flight (e.g. an SSH command) can't be interrupted
    cooperatively. Closing the underlying stream iterator stops the graph from
    scheduling any further steps.
    """
    it = iter(graph.stream(stream_input, config=config, stream_mode=["updates", "custom"]))
    while True:
        if cancel_event is not None and cancel_event.is_set():
            it.close()
            yield "stopped", "Dihentikan oleh operator."
            return
        try:
            mode, chunk = next(it)
        except StopIteration:
            return

        if mode == "custom":
            entry = chunk
            yield entry["event_type"], f"[{entry['source']}] {entry['content']}"
            continue

        for node_name, node_output in chunk.items():
            if node_name == "__interrupt__":
                # Human-in-the-loop pause
                payload = node_output[0].value if node_output else {}
                yield "approval_required", json.dumps(payload)
                return

            # Emit agent_log entries not already streamed live (e.g. routing)
            for entry in node_output.get("agent_log") or []:
                if entry["event_type"] in _LIVE_STREAMED_TYPES:
                    continue
                yield entry["event_type"], f"[{entry['source']}] {entry['content']}"

            # Emit new AI messages
            for msg in node_output.get("messages") or []:
                from langchain_core.messages import AIMessage  # noqa: PLC0415
                if isinstance(msg, AIMessage) and msg.content:
                    import re
                    content = re.sub(r"<think>.*?</think>", "", msg.content, flags=re.DOTALL).strip()
                    if content:
                        yield "ai", content


def stream_agent_response(
    graph: Any,
    config: RunnableConfig,
    message: str,
    cancel_event: threading.Event | None = None,
) -> Iterator[tuple[str, str]]:
    """
    Stream agent events for a user message.

    Yields (event_type, content) where event_type is one of:
      "routing"          — supervisor routing decision
      "tool_call"        — tool being invoked by a specialist
      "tool_result"      — tool returned result (preview)
      "ai"               — final AI text response
      "approval_required"— waiting for operator approval
      "stopped"          — operator cancelled the run via cancel_event
      "error"            — unrecoverable error
    """
    try:
        yield from _drain_graph_stream(
            graph, config, {"messages": [HumanMessage(content=message)]},
            cancel_event=cancel_event,
        )
    except Exception as exc:
        yield "error", str(exc)


def submit_approval(
    graph: Any,
    config: RunnableConfig,
    decision: str,
) -> None:
    """Resume a paused graph after human approval. decision: 'approved' | 'rejected'.
    Headless / non-streaming variant — use resume_after_approval for TUI streaming."""
    graph.invoke(Command(resume=decision), config=config)


def resume_after_approval(
    graph: Any,
    config: RunnableConfig,
    decision: str,
    cancel_event: threading.Event | None = None,
) -> Iterator[tuple[str, str]]:
    """Resume after approval, streaming events back to caller.
    Yields same (event_type, content) tuples as stream_agent_response.
    May yield another 'approval_required' if a subsequent tool also needs approval.
    """
    try:
        yield from _drain_graph_stream(graph, config, Command(resume=decision), cancel_event=cancel_event)
    except Exception as exc:
        yield "error", str(exc)


def get_token_metrics(n: int = 100) -> list[dict]:
    """Return last n entries from data/metrics.jsonl, newest last."""
    from agents.metrics import METRICS_PATH  # noqa: PLC0415
    if not METRICS_PATH.exists():
        return []
    lines = METRICS_PATH.read_text(encoding="utf-8").splitlines()
    entries = []
    for line in lines[-n:]:
        try:
            entries.append(json.loads(line))
        except Exception:
            pass
    return entries


def get_available_skills() -> list[dict]:
    """Return list of enabled skill summaries for TUI display."""
    return [s.summary() for s in _skill_lib.list_enabled()]


def get_agent_status() -> dict:
    from agents.nodes import _agent_loader  # noqa: PLC0415
    from tools.db import db_get_llm_config  # noqa: PLC0415

    cfg = db_get_llm_config()
    defn = _agent_loader.get("supervisor")
    model = defn.model if defn else (cfg.get("model") or os.getenv("OLLAMA_MODEL", "gemma4:e4b"))
    return {
        "skills_loaded": len(_skill_lib),
        "model": model,
        "ollama_url": cfg.get("base_url") or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
    }


def test_llm_connection(
    model: str | None = None, base_url: str | None = None, api_key: str | None = None,
) -> dict:
    """Kirim satu pesan ping ke LLM untuk verifikasi konektivitas dari halaman Settings.

    Menggunakan pabrik LLM yang sama dengan agent (_make_llm) agar hasil test
    mencerminkan koneksi yang benar-benar dipakai saat runtime.
    """
    import time
    from agents.nodes import _make_llm  # noqa: PLC0415
    from tools.db import db_get_llm_config  # noqa: PLC0415

    cfg = db_get_llm_config()
    model = model or cfg.get("model") or os.getenv("OLLAMA_MODEL", "")
    base_url = base_url or cfg.get("base_url") or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    api_key = api_key or cfg.get("api_key") or os.getenv("OLLAMA_API_KEY", "")
    started = time.monotonic()
    try:
        llm = _make_llm(
            temperature=0,
            model=model,
            num_predict=8,
            timeout=10,
            base_url=base_url,
            api_key=api_key,
            agent_name="connection_test",
            max_retries=0,
        )
        llm.invoke([HumanMessage(content="ping")])
        return {
            "ok": True,
            "model": model,
            "base_url": base_url,
            "latency_ms": round((time.monotonic() - started) * 1000),
        }
    except Exception as e:
        return {
            "ok": False,
            "model": model,
            "base_url": base_url,
            "latency_ms": round((time.monotonic() - started) * 1000),
            "error": str(e),
        }


def list_llm_models(base_url: str | None = None, api_key: str | None = None) -> dict:
    """List model id yang tersedia dari endpoint OpenAI-compatible (GET /models).

    Dipakai Settings untuk isi dropdown model tanpa operator harus tahu nama
    model persis lebih dulu — cukup base_url + api_key untuk cek koneksi.
    """
    import time
    from openai import OpenAI  # noqa: PLC0415
    from tools.db import db_get_llm_config  # noqa: PLC0415

    cfg = db_get_llm_config()
    base_url = base_url or cfg.get("base_url") or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    api_key = api_key or cfg.get("api_key") or os.getenv("OLLAMA_API_KEY", "") or "sk-placeholder"
    started = time.monotonic()
    try:
        client = OpenAI(base_url=base_url, api_key=api_key, timeout=10, max_retries=0)
        resp = client.models.list()
        models = sorted(m.id for m in resp.data)
        return {
            "ok": True,
            "base_url": base_url,
            "models": models,
            "latency_ms": round((time.monotonic() - started) * 1000),
        }
    except Exception as e:
        return {
            "ok": False,
            "base_url": base_url,
            "models": [],
            "latency_ms": round((time.monotonic() - started) * 1000),
            "error": str(e),
        }
