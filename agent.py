#!/usr/bin/env python3
"""NetOps AI — public API for TUI. All LLM and agent logic lives here."""

from __future__ import annotations

import json
import os
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


# ── SkillLibrary singleton ─────────────────────────────────────────────────────

from skills import SkillLibrary  # noqa: E402

_skill_lib = SkillLibrary(Path(__file__).parent / "skills")
_skill_lib.start_watcher()

# ── Graph cache ────────────────────────────────────────────────────────────────

_DB_PATH = Path(__file__).parent / "data" / "checkpoints.db"
_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
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
    # Overwrite state with empty messages untuk reset percakapan
    graph.update_state(config, {"messages": [], "agent_log": [], "next_agent": "",
                                 "active_agent": "", "injected_skills": [],
                                 "pending_approval": None, "approval_decision": None})
    return graph, config


def stream_agent_response(
    graph: Any,
    config: RunnableConfig,
    message: str,
) -> Iterator[tuple[str, str]]:
    """
    Stream agent events for a user message.

    Yields (event_type, content) where event_type is one of:
      "routing"          — supervisor routing decision
      "tool_call"        — tool being invoked by a specialist
      "tool_result"      — tool returned result (preview)
      "ai"               — final AI text response
      "approval_required"— waiting for operator approval
      "error"            — unrecoverable error
    """
    try:
        for chunk in graph.stream(
            {"messages": [HumanMessage(content=message)]},
            config=config,
            stream_mode="updates",
        ):
            for node_name, node_output in chunk.items():
                if node_name == "__interrupt__":
                    # Human-in-the-loop pause
                    payload = node_output[0].value if node_output else {}
                    yield "approval_required", json.dumps(payload)
                    return

                # Emit agent_log entries as streaming events
                for entry in node_output.get("agent_log") or []:
                    yield entry["event_type"], f"[{entry['source']}] {entry['content']}"

                # Emit new AI messages
                for msg in node_output.get("messages") or []:
                    from langchain_core.messages import AIMessage  # noqa: PLC0415
                    if isinstance(msg, AIMessage) and msg.content:
                        import re
                        content = re.sub(r"<think>.*?</think>", "", msg.content, flags=re.DOTALL).strip()
                        if content:
                            yield "ai", content

    except Exception as exc:
        yield "error", str(exc)


def submit_approval(
    graph: Any,
    config: RunnableConfig,
    decision: str,
) -> None:
    """Resume a paused graph after human approval. decision: 'approved' | 'rejected'."""
    graph.invoke(Command(resume=decision), config=config)


def get_available_skills() -> list[dict]:
    """Return list of enabled skill summaries for TUI display."""
    return [s.summary() for s in _skill_lib.list_enabled()]


def get_agent_status() -> dict:
    return {
        "skills_loaded": len(_skill_lib),
        "model": os.getenv("OLLAMA_MODEL", "gemma4:e4b"),
        "ollama_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
    }
