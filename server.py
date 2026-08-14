#!/usr/bin/env python3
"""NetOps AI — Web Server.

Exposes agent.py public API over HTTP for the web frontend.

Run:
    python server.py
    # or: uvicorn server:app --reload
"""
from __future__ import annotations

import asyncio
import json
import logging
import uuid
from pathlib import Path
from typing import Any, AsyncGenerator, Iterator

import yaml
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
log = logging.getLogger(__name__)

FRONTEND_DIR = Path(__file__).parent / "frontend"


class _IndentedYamlDumper(yaml.Dumper):
    """Indents list items under their parent key (PyYAML's default doesn't),
    matching the style already used by every hand-authored .md frontmatter
    in this repo — keeps round-tripped saves diff-clean against originals."""
    def increase_indent(self, flow=False, indentless=False):
        return super().increase_indent(flow, False)

import agent as _agent
from tools.db import (
    db_create_thread, db_list_threads, db_touch_thread, db_archive_thread,
    db_delete_thread, db_rename_thread,
    db_get_llm_config, db_set_llm_config,
    db_list_llm_profiles, db_add_llm_profile, db_update_llm_profile,
    db_delete_llm_profile, db_activate_llm_profile, db_deactivate_llm_profile,
    db_get_ssh_config, db_set_ssh_config, db_get_router,
)

app = FastAPI(title="NetOps AI", docs_url=None, redoc_url=None)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Session store ─────────────────────────────────────────────────────────────
_sessions: dict[str, tuple[Any, Any]] = {}


def _get_or_create_session(thread_id: str) -> tuple[Any, Any]:
    if thread_id not in _sessions:
        log.info("New session: %s", thread_id)
        graph, config = _agent.create_agent(thread_id=thread_id)
        _sessions[thread_id] = (graph, config)
    return _sessions[thread_id]


# ── Async streaming helper ────────────────────────────────────────────────────

async def _stream_events(gen: Iterator[tuple[str, str]]) -> AsyncGenerator[str, None]:
    """Wrap sync generator → async SSE lines with heartbeat.

    Runs the blocking generator in a thread pool and forwards events via an
    asyncio.Queue using call_soon_threadsafe so the queue is only touched from
    the event-loop thread.

    Sends a SSE comment (:ping) every 3 s while the generator is busy so the
    browser connection stays alive and the user sees activity.
    """
    loop = asyncio.get_event_loop()
    queue: asyncio.Queue[tuple[str, str] | None] = asyncio.Queue()

    def _produce() -> None:
        try:
            for event_type, content in gen:
                loop.call_soon_threadsafe(queue.put_nowait, (event_type, content))
        finally:
            loop.call_soon_threadsafe(queue.put_nowait, None)

    future = loop.run_in_executor(None, _produce)
    # Keep ONE queue.get() task alive across timeout/heartbeat cycles. The
    # previous implementation (asyncio.wait_for(asyncio.shield(queue.get()),
    # timeout=3.0)) started a brand new queue.get() call on every retry;
    # shield kept the timed-out call alive in the background instead of
    # cancelling it, so after a few heartbeats several orphaned queue.get()
    # calls were all waiting on the same queue. An item could land on one of
    # those orphaned calls instead of the one actually being awaited and get
    # silently dropped — more likely the longer a run takes (more heartbeat
    # cycles), which is exactly why the final "ai" message tended to vanish
    # on longer multi-tool-call runs.
    get_task = asyncio.ensure_future(queue.get())
    try:
        while True:
            done, _pending = await asyncio.wait({get_task}, timeout=3.0)
            if not done:
                yield ": ping\n\n"  # SSE comment — keeps connection alive, browser ignores
                continue
            item = get_task.result()
            get_task = asyncio.ensure_future(queue.get())
            if item is None:
                break
            event_type, content = item
            payload = json.dumps({"type": event_type, "content": content})
            yield f"data: {payload}\n\n"
    finally:
        get_task.cancel()
    await future


# ── Request models ────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    thread_id: str
    message: str


class ApproveRequest(BaseModel):
    thread_id: str
    decision: str  # "approved" | "rejected"


# ── API endpoints ─────────────────────────────────────────────────────────────

@app.post("/chat")
async def chat(req: ChatRequest) -> StreamingResponse:
    graph, config = _get_or_create_session(req.thread_id)
    db_touch_thread(req.thread_id, req.message[:120])
    gen = _agent.stream_agent_response(graph, config, req.message)
    return StreamingResponse(
        _stream_events(gen),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/approve")
async def approve(req: ApproveRequest) -> StreamingResponse:
    if req.thread_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session tidak ditemukan")
    graph, config = _sessions[req.thread_id]
    db_touch_thread(req.thread_id)
    gen = _agent.resume_after_approval(graph, config, req.decision)
    return StreamingResponse(
        _stream_events(gen),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/info")
def info() -> dict:
    import os
    return {
        "model": os.getenv("OLLAMA_MODEL", "unknown"),
        "ollama_host": os.getenv("OLLAMA_BASE_URL", ""),
    }


@app.get("/metrics")
def metrics(n: int = 100) -> list[dict]:
    return _agent.get_token_metrics(n)


@app.post("/session/new")
def new_session() -> dict:
    thread_id = str(uuid.uuid4())
    _get_or_create_session(thread_id)
    db_create_thread(thread_id)
    return {"thread_id": thread_id}


@app.get("/api/sessions")
def list_sessions(limit: int = 50) -> dict:
    """Return persisted thread list for frontend to restore on page reload."""
    return {"sessions": db_list_threads(limit=limit)}


@app.get("/api/threads/{thread_id}/messages")
def thread_messages(thread_id: str) -> dict:
    """Replay conversation history (user/agent text only, no tool-call trace)
    for a thread from LangGraph's checkpoint store, so switching to an old
    thread in the UI shows what was discussed instead of a blank chat."""
    import re
    from langchain_core.messages import HumanMessage, AIMessage

    graph, config = _get_or_create_session(thread_id)
    state = graph.get_state(config)
    raw_messages = state.values.get("messages", []) if state and state.values else []

    messages = []
    for m in raw_messages:
        if isinstance(m, HumanMessage) and m.content:
            messages.append({"role": "user", "content": m.content})
        elif isinstance(m, AIMessage) and m.content:
            content = re.sub(r"<think>.*?</think>", "", m.content, flags=re.DOTALL).strip()
            if content:
                messages.append({"role": "agent", "content": content})

    return {"messages": messages}


@app.get("/api/threads/{thread_id}/log")
def thread_log(thread_id: str) -> dict:
    """Full audit trail for a thread: every routing/tool_call/tool_result/
    approval entry with its real timestamp, read straight from LangGraph's
    checkpoint store (agent_log is an append-only state channel — see
    NetworkOpsState in agent.py). This is the durable, server-side audit
    source; the browser's live 'Process Console' is only a UI convenience
    cache and is not suitable for audit (per-browser, user-clearable)."""
    graph, config = _get_or_create_session(thread_id)
    state = graph.get_state(config)
    agent_log = state.values.get("agent_log", []) if state and state.values else []
    return {"log": agent_log}


class RenameThreadRequest(BaseModel):
    title: str


@app.put("/api/threads/{thread_id}")
def api_rename_thread(thread_id: str, req: RenameThreadRequest) -> dict:
    title = req.title.strip()[:120] or "New Chat"
    db_rename_thread(thread_id, title)
    return {"status": "renamed", "thread_id": thread_id, "title": title}


@app.delete("/api/threads/{thread_id}")
def api_delete_thread(thread_id: str) -> dict:
    """Permanently delete a thread — its metadata row and its LangGraph
    checkpoint state (messages, agent_log, everything). Not recoverable."""
    _agent.delete_thread(thread_id)
    db_delete_thread(thread_id)
    _sessions.pop(thread_id, None)
    return {"status": "deleted", "thread_id": thread_id}


# ── Additional API endpoints ──────────────────────────────────────────────────

from agents.tools import TOOL_MAP


@app.get("/api/status")
def api_status() -> dict:
    return _agent.get_agent_status()


class ResetRequest(BaseModel):
    thread_id: str


@app.post("/api/reset")
def api_reset(req: ResetRequest) -> dict:
    _agent.reset_agent(req.thread_id)
    _sessions.pop(req.thread_id, None)
    return {"status": "ok"}


class LLMTestRequest(BaseModel):
    model: str | None = None
    base_url: str | None = None
    api_key: str | None = None


@app.post("/api/llm/test")
def api_llm_test(req: LLMTestRequest) -> dict:
    """Ping LLM endpoint (Ollama/OpenAI-compatible) untuk verifikasi konektivitas dari Settings."""
    return _agent.test_llm_connection(model=req.model, base_url=req.base_url, api_key=req.api_key)


# ── Tools: Direct invocation ─────────────────────────────────────────────────


class RouterRequest(BaseModel):
    router_name: str


class SearchRequest(BaseModel):
    query: str


@app.get("/api/tool-names")
def api_tool_names():
    return {"tools": sorted(TOOL_MAP.keys())}


@app.get("/api/tools/routers")
def api_routers():
    return {"result": TOOL_MAP["list_routers"].invoke({})}


@app.post("/api/tools/reachability")
def api_reachability(req: RouterRequest):
    return {"result": TOOL_MAP["check_reachability"].invoke({"router_name": req.router_name})}


@app.post("/api/tools/reachability/all")
def api_reachability_all():
    from tools.base import get_unique_router_entries
    results = {}
    for entry in get_unique_router_entries():
        try:
            r = TOOL_MAP["check_reachability"].invoke({"router_name": entry["name"]})
            results[entry["name"]] = r
        except Exception as e:
            results[entry["name"]] = f"Error: {e}"
    return {"results": results}


@app.post("/api/tools/system-info")
def api_system_info(req: RouterRequest):
    return {"result": TOOL_MAP["get_system_info"].invoke({"router_name": req.router_name})}


@app.post("/api/tools/traffic")
def api_traffic(req: RouterRequest):
    return {"result": TOOL_MAP["get_traffic_summary"].invoke({"router_name": req.router_name})}


@app.get("/api/tools/traffic/all")
def api_traffic_all():
    return {"result": TOOL_MAP["get_traffic_all"].invoke({})}


@app.get("/api/tools/dhcp/audit")
def api_dhcp_audit():
    return {"result": TOOL_MAP["audit_dhcp"].invoke({})}


@app.post("/api/tools/dhcp/search")
def api_dhcp_search(req: SearchRequest):
    return {"result": TOOL_MAP["search_device"].invoke({"query": req.query})}


@app.post("/api/tools/dhcp/leases")
def api_dhcp_leases(req: RouterRequest):
    return {"result": TOOL_MAP["get_router_leases"].invoke({"router_name": req.router_name})}


@app.post("/api/tools/security/audit")
def api_security_audit(req: RouterRequest):
    return {"result": TOOL_MAP["audit_security"].invoke({"router_name": req.router_name})}


@app.post("/api/tools/interface-stats")
def api_interface_stats(req: RouterRequest):
    return {"result": TOOL_MAP["get_interface_stats"].invoke({"router_name": req.router_name})}


@app.post("/api/tools/router-log")
def api_router_log(req: RouterRequest):
    return {"result": TOOL_MAP["get_router_log"].invoke({"router_name": req.router_name})}


# ── Skills ───────────────────────────────────────────────────────────────────

SKILLS_DIR = FRONTEND_DIR.parent / "skills"
PENDING_DIR = SKILLS_DIR / ".pending"
# Kept outside skills/ (which SkillLibrary rglobs recursively) so stashed
# defaults are never mistaken for real skills or trigger watcher churn.
SKILLS_DEFAULTS_DIR = FRONTEND_DIR.parent / "data" / "defaults" / "skills"


def _stash_default(path: Path, defaults_dir: Path) -> None:
    """Back up the pristine (repo-shipped) file the first time it's edited.

    Subsequent edits are no-ops here so the original default is preserved
    permanently, letting the UI offer a "restore to default" action.
    """
    if not path.exists():
        return
    defaults_dir.mkdir(parents=True, exist_ok=True)
    stash = defaults_dir / path.name
    if not stash.exists():
        stash.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")


class SkillRequest(BaseModel):
    name: str
    domain: str
    triggers: list[str] = []
    tools: list[str] = []
    approval_required: bool = False
    enabled: bool = True
    body: str = ""


def _skill_markdown(req: "SkillRequest") -> str:
    fm = {
        "name": req.name,
        "domain": req.domain,
        "triggers": req.triggers,
        "tools": req.tools,
        "approval_required": req.approval_required,
        "enabled": req.enabled,
    }
    fm_yaml = yaml.dump(fm, Dumper=_IndentedYamlDumper, sort_keys=False, default_flow_style=False, allow_unicode=True)
    return f"---\n{fm_yaml}---\n\n{req.body.strip()}\n"


@app.get("/api/skills")
def api_skills():
    from agent import _skill_lib
    return {"skills": [
        {**s.summary(), "has_default": (SKILLS_DEFAULTS_DIR / f"{s.name}.md").exists()}
        for s in _skill_lib.list_all()
    ]}


@app.get("/api/skills/pending")
def api_skills_pending():
    if not PENDING_DIR.exists():
        return {"pending": []}
    items = []
    for f in PENDING_DIR.rglob("*.md"):
        items.append({"name": f.stem, "path": str(f.relative_to(PENDING_DIR))})
    return {"pending": items}


@app.get("/api/skills/{name}")
def api_skill_detail(name: str):
    from agent import _skill_lib
    skill = _skill_lib.get_by_name(name)
    if not skill:
        raise HTTPException(404, f"Skill '{name}' tidak ditemukan.")
    return {
        **skill.summary(), "body": skill.body, "path": str(skill.path),
        "has_default": (SKILLS_DEFAULTS_DIR / f"{name}.md").exists(),
    }


@app.post("/api/skills")
def api_create_skill(req: SkillRequest):
    from agent import _skill_lib
    if _skill_lib.get_by_name(req.name):
        raise HTTPException(400, f"Skill '{req.name}' sudah ada.")
    target_dir = SKILLS_DIR / req.domain
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"{req.name}.md"
    target.write_text(_skill_markdown(req), encoding="utf-8")
    _skill_lib._reload_file(target)
    return {"status": "created", "name": req.name, "path": str(target)}


@app.put("/api/skills/{name}")
def api_update_skill(name: str, req: SkillRequest):
    from agent import _skill_lib
    skill = _skill_lib.get_by_name(name)
    if not skill:
        raise HTTPException(404, f"Skill '{name}' tidak ditemukan.")
    old_path = skill.path
    _stash_default(old_path, SKILLS_DEFAULTS_DIR)
    target_dir = SKILLS_DIR / req.domain
    target_dir.mkdir(parents=True, exist_ok=True)
    new_path = target_dir / f"{req.name}.md"
    new_path.write_text(_skill_markdown(req), encoding="utf-8")
    _skill_lib._reload_file(new_path)
    if new_path != old_path:
        old_path.unlink(missing_ok=True)
        _skill_lib._reload_file(old_path)
    return {"status": "updated", "name": req.name, "path": str(new_path)}


@app.post("/api/skills/{name}/restore")
def api_restore_skill(name: str):
    from agent import _skill_lib
    stash = SKILLS_DEFAULTS_DIR / f"{name}.md"
    if not stash.exists():
        raise HTTPException(400, f"Skill '{name}' belum pernah diubah dari default.")
    stash_text = stash.read_text(encoding="utf-8")
    fm_end = stash_text.find("---", 3)
    fm = yaml.safe_load(stash_text[3:fm_end]) or {} if fm_end != -1 else {}
    domain = fm.get("domain", "general")
    target_dir = SKILLS_DIR / domain
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"{name}.md"

    skill = _skill_lib.get_by_name(name)
    if skill and skill.path != target:
        skill.path.unlink(missing_ok=True)
        _skill_lib._reload_file(skill.path)

    target.write_text(stash_text, encoding="utf-8")
    _skill_lib._reload_file(target)
    return {"status": "restored", "name": name, "path": str(target)}


@app.delete("/api/skills/{name}")
def api_delete_skill(name: str):
    from agent import _skill_lib
    skill = _skill_lib.get_by_name(name)
    if not skill:
        raise HTTPException(404, f"Skill '{name}' tidak ditemukan.")
    path = skill.path
    path.unlink()
    _skill_lib._reload_file(path)
    return {"status": "deleted", "name": name}


@app.post("/api/skills/pending/{name}/approve")
def api_approve_pending_skill(name: str):
    from agent import _skill_lib
    matches = list(PENDING_DIR.rglob(f"{name}.md"))
    if not matches:
        raise HTTPException(404, f"Pending skill '{name}' tidak ditemukan.")
    path = matches[0]
    text = path.read_text(encoding="utf-8")
    clean = text
    if clean.startswith("<!--"):
        clean = clean[clean.index("-->\n") + 4:]
    fm_end = clean.find("---", 3)
    fm = yaml.safe_load(clean[3:fm_end]) if fm_end != -1 else {}
    domain = (fm or {}).get("domain", path.parent.name)
    target_dir = SKILLS_DIR / domain
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / path.name
    target.write_text(clean, encoding="utf-8")
    path.unlink()
    try:
        path.parent.rmdir()
    except OSError:
        pass
    _skill_lib._reload_file(target)
    return {"status": "approved", "name": name, "path": str(target)}


@app.post("/api/skills/pending/{name}/reject")
def api_reject_pending_skill(name: str):
    matches = list(PENDING_DIR.rglob(f"{name}.md"))
    if not matches:
        raise HTTPException(404, f"Pending skill '{name}' tidak ditemukan.")
    path = matches[0]
    path.unlink()
    try:
        path.parent.rmdir()
    except OSError:
        pass
    return {"status": "rejected", "name": name}


# ── Agents ───────────────────────────────────────────────────────────────────
# Live-edited via data/netops.db (tools.db.db_update_agent) — agents/definitions/*.md
# is only the one-time seed and is never written back to. See tools/db.py docstring.

@app.get("/api/agents")
def api_agents():
    from tools.db import db_list_agents
    return {"agents": [
        {
            "name": d["name"], "alias": d["alias"], "description": d["description"],
            "model": d["model"], "num_ctx": d["num_ctx"], "num_predict": d["num_predict"],
            "context_window": d["context_window"], "timeout": d["timeout"],
            "tools": d["tools"], "skills": d["skills"], "reasoning": d["reasoning"],
            "enabled": d["enabled"], "has_default": d["has_default"],
        }
        for d in db_list_agents()
    ]}


@app.get("/api/agents/{name}")
def api_agent_detail(name: str):
    from tools.db import db_get_agent
    defn = db_get_agent(name)
    if not defn:
        raise HTTPException(404, f"Agent '{name}' tidak ditemukan.")
    return defn


class AgentUpdateRequest(BaseModel):
    description: str
    model: str
    tools: list[str] = []
    skills: list[str] = []
    num_ctx: int = 8192
    num_predict: int = 2048
    context_window: int = 10
    timeout: int = 300
    ollama_host: str = ""
    reasoning: bool = False
    max_iters: int = 20
    enabled: bool = True
    body: str = ""


@app.put("/api/agents/{name}")
def api_update_agent(name: str, req: AgentUpdateRequest):
    from tools.db import db_get_agent, db_update_agent
    from agents.nodes import _agent_loader
    if not db_get_agent(name):
        raise HTTPException(404, f"Agent '{name}' tidak ditemukan.")
    db_update_agent(
        name,
        description=req.description, model=req.model, tools=req.tools, skills=req.skills,
        num_ctx=req.num_ctx, num_predict=req.num_predict, context_window=req.context_window,
        timeout=req.timeout, ollama_host=req.ollama_host, reasoning=req.reasoning,
        max_iters=req.max_iters, enabled=req.enabled, body=req.body.strip(),
    )
    _agent_loader.reload()
    return {"status": "updated", "name": name, "restart_required": True}


@app.post("/api/agents/{name}/restore")
def api_restore_agent(name: str):
    from tools.db import db_get_agent, db_restore_agent_default
    from agents.nodes import _agent_loader
    defn = db_get_agent(name)
    if not defn:
        raise HTTPException(404, f"Agent '{name}' tidak ditemukan.")
    if not defn["has_default"]:
        raise HTTPException(400, f"Agent '{name}' belum pernah diubah dari default.")
    db_restore_agent_default(name)
    _agent_loader.reload()
    return {"status": "restored", "name": name, "restart_required": True}


# ── Reports & Backups ────────────────────────────────────────────────────────

@app.get("/api/reports")
def api_reports():
    return {"result": TOOL_MAP["list_reports"].invoke({})}


@app.get("/api/reports/{filename}")
def api_report_content(filename: str):
    return {"result": TOOL_MAP["get_report"].invoke({"filename": filename})}


@app.get("/api/reports/{filename}/toc")
def api_report_toc(filename: str):
    return {"result": TOOL_MAP["get_report_toc"].invoke({"filename": filename})}


@app.get("/api/backups")
def api_backups():
    return {"result": TOOL_MAP["list_backups"].invoke({})}


@app.get("/api/backups/diff")
def api_backups_diff(router: str, file_a: str, file_b: str):
    return {"result": TOOL_MAP["diff_config"].invoke({
        "router_name": router, "file_a": file_a, "file_b": file_b,
    })}


# ── Config CRUD ──────────────────────────────────────────────────────────────

@app.get("/api/config/llm")
def api_config_llm() -> dict:
    cfg = db_get_llm_config()
    api_key = cfg.pop("api_key", "") or ""
    cfg["api_key_set"] = bool(api_key)
    cfg["api_key_preview"] = f"••••{api_key[-4:]}" if len(api_key) >= 4 else ("••••" if api_key else "")
    return cfg


class UpdateLLMConfigRequest(BaseModel):
    base_url: str | None = None
    model: str | None = None
    api_key: str | None = None


@app.put("/api/config/llm")
def api_config_update_llm(req: UpdateLLMConfigRequest) -> dict:
    if req.base_url is None and req.model is None and req.api_key is None:
        raise HTTPException(400, "base_url, model, atau api_key harus diisi")
    # Blank api_key means "leave unchanged" — frontend never re-sends the real
    # secret, only a masked preview, so an empty string here isn't intentional clearing.
    api_key = req.api_key if req.api_key else None
    cfg = db_set_llm_config(base_url=req.base_url, model=req.model, api_key=api_key)
    stored_key = cfg.pop("api_key", "") or ""
    cfg["api_key_set"] = bool(stored_key)
    cfg["api_key_preview"] = f"••••{stored_key[-4:]}" if len(stored_key) >= 4 else ("••••" if stored_key else "")
    return cfg


@app.get("/api/config/llm/profiles")
def api_list_llm_profiles() -> dict:
    profiles = db_list_llm_profiles()
    for p in profiles:
        key = p.pop("api_key", "") or ""
        p["api_key_set"] = bool(key)
        p["api_key_preview"] = f"••••{key[-4:]}" if len(key) >= 4 else ("••••" if key else "")
    return {"profiles": profiles}


class LLMProfileRequest(BaseModel):
    name: str
    base_url: str
    model: str
    api_key: str = ""


@app.post("/api/config/llm/profiles")
def api_add_llm_profile(req: LLMProfileRequest) -> dict:
    try:
        profile = db_add_llm_profile(req.name, req.base_url, req.model, req.api_key)
        key = profile.pop("api_key", "") or ""
        profile["api_key_set"] = bool(key)
        profile["api_key_preview"] = f"••••{key[-4:]}" if len(key) >= 4 else ("••••" if key else "")
        return profile
    except Exception as e:
        raise HTTPException(400, str(e))


class UpdateLLMProfileRequest(BaseModel):
    name: str | None = None
    base_url: str | None = None
    model: str | None = None
    api_key: str | None = None


@app.put("/api/config/llm/profiles/{profile_id}")
def api_update_llm_profile(profile_id: int, req: UpdateLLMProfileRequest) -> dict:
    api_key = req.api_key if req.api_key else None
    profile = db_update_llm_profile(profile_id, req.name, req.base_url, req.model, api_key)
    if not profile:
        raise HTTPException(404, "Profile tidak ditemukan")
    key = profile.pop("api_key", "") or ""
    profile["api_key_set"] = bool(key)
    profile["api_key_preview"] = f"••••{key[-4:]}" if len(key) >= 4 else ("••••" if key else "")
    return profile


@app.delete("/api/config/llm/profiles/{profile_id}")
def api_delete_llm_profile(profile_id: int) -> dict:
    rows = db_delete_llm_profile(profile_id)
    if not rows:
        raise HTTPException(404, "Profile tidak ditemukan")
    return {"ok": True}


@app.post("/api/config/llm/profiles/{profile_id}/activate")
def api_activate_llm_profile(profile_id: int) -> dict:
    cfg = db_activate_llm_profile(profile_id)
    if not cfg:
        raise HTTPException(404, "Profile tidak ditemukan")
    key = cfg.pop("api_key", "") or ""
    cfg["api_key_set"] = bool(key)
    cfg["api_key_preview"] = f"••••{key[-4:]}" if len(key) >= 4 else ("••••" if key else "")
    return cfg


@app.post("/api/config/llm/profiles/{profile_id}/deactivate")
def api_deactivate_llm_profile(profile_id: int) -> dict:
    profile = db_deactivate_llm_profile(profile_id)
    if not profile:
        raise HTTPException(404, "Profile tidak ditemukan")
    key = profile.pop("api_key", "") or ""
    profile["api_key_set"] = bool(key)
    profile["api_key_preview"] = f"••••{key[-4:]}" if len(key) >= 4 else ("••••" if key else "")
    return profile


@app.get("/api/config/routers")
def api_config_routers():
    from tools.base import get_unique_router_entries, ssh_creds
    try:
        entries = get_unique_router_entries()
        creds = ssh_creds()
        routers = []
        for e in entries:
            r = dict(e)
            password = r.pop("ssh_password", "") or ""
            r["ssh_password_set"] = bool(password)
            routers.append(r)
        return {
            "routers": routers,
            "ssh_username": creds.get("username", ""),
        }
    except Exception as e:
        raise HTTPException(500, str(e))


class AddRouterRequest(BaseModel):
    name: str
    host: str
    ros_version: int = 7
    role: str = "backbone"
    network: str = "kampus"
    ssh_username: str = ""
    ssh_password: str = ""


@app.post("/api/config/routers")
def api_config_add_router(req: AddRouterRequest):
    result = TOOL_MAP["add_router_to_config"].invoke({
        "name": req.name, "host": req.host, "ros_version": req.ros_version,
        "role": req.role, "network": req.network,
    })
    if req.ssh_username and req.ssh_password:
        from tools.db import db_update_router_field
        from tools.base import reload_config
        db_update_router_field(req.name, "ssh_username", req.ssh_username)
        db_update_router_field(req.name, "ssh_password", req.ssh_password)
        reload_config()
    return {"result": result}


class UpdateRouterRequest(BaseModel):
    host: str | None = None
    role: str | None = None
    network: str | None = None
    ros_version: int | None = None
    ssh_username: str | None = None
    ssh_password: str | None = None


@app.put("/api/config/routers/{name}")
def api_config_update_router(name: str, req: UpdateRouterRequest):
    from tools.db import db_update_router_field
    from tools.base import reload_config

    existing = db_get_router(name)
    if not existing:
        raise HTTPException(404, "Router tidak ditemukan")

    fields = req.model_dump(exclude_unset=True)
    # Blank password means "leave unchanged" — the edit form never re-sends the
    # real stored password, only a masked preview, so an empty string here
    # isn't intentional clearing (unlike ssh_username, which is shown in full
    # and can legitimately be cleared to fall back to the global default).
    if "ssh_password" in fields and not fields["ssh_password"]:
        fields.pop("ssh_password")
    if not fields:
        raise HTTPException(400, "Tidak ada field untuk diupdate")

    for field, value in fields.items():
        db_update_router_field(name, field, value)
    reload_config()
    return {"result": f"Router '{name}' diperbarui."}


@app.delete("/api/config/routers/{name}")
def api_config_remove_router(name: str):
    result = TOOL_MAP["remove_router_from_config"].invoke({"router_name": name})
    return {"result": result}


@app.get("/api/config/ssh")
def api_config_ssh() -> dict:
    cfg = db_get_ssh_config()
    password = cfg.pop("password", "") or ""
    cfg["password_set"] = bool(password)
    cfg["password_preview"] = f"••••{password[-2:]}" if len(password) >= 2 else ("••••" if password else "")
    return cfg


class UpdateSSHConfigRequest(BaseModel):
    username: str | None = None
    password: str | None = None
    port: int | None = None
    timeout: int | None = None


@app.put("/api/config/ssh")
def api_config_update_ssh(req: UpdateSSHConfigRequest) -> dict:
    if req.username is None and req.password is None and req.port is None and req.timeout is None:
        raise HTTPException(400, "Minimal satu field harus diisi")
    # Blank password means "leave unchanged", same convention as the LLM api_key field.
    password = req.password if req.password else None
    cfg = db_set_ssh_config(username=req.username, password=password, port=req.port, timeout=req.timeout)
    from tools.base import reload_config
    reload_config()
    stored = cfg.pop("password", "") or ""
    cfg["password_set"] = bool(stored)
    cfg["password_preview"] = f"••••{stored[-2:]}" if len(stored) >= 2 else ("••••" if stored else "")
    return cfg


# ── NetBox ───────────────────────────────────────────────────────────────────

@app.get("/api/netbox/devices")
def api_netbox_devices():
    return {"result": TOOL_MAP["get_netbox_devices"].invoke({})}


@app.get("/api/netbox/devices/{name}/interfaces")
def api_netbox_interfaces(name: str):
    return {"result": TOOL_MAP["get_netbox_device_interfaces"].invoke({"device_name": name})}


@app.get("/api/netbox/devices/{name}/ips")
def api_netbox_ips(name: str):
    return {"result": TOOL_MAP["get_netbox_device_ips"].invoke({"device_name": name})}


@app.get("/api/netbox/drift/{name}")
def api_netbox_drift(name: str):
    return {"result": TOOL_MAP["get_netbox_drift_report"].invoke({"router_name": name})}


@app.get("/api/netbox/vlans")
def api_netbox_vlans():
    return {"result": TOOL_MAP["get_netbox_vlan_groups"].invoke({})}


@app.get("/api/netbox/bgp/drift")
def api_netbox_bgp_drift():
    return {"result": TOOL_MAP["get_netbox_bgp_drift"].invoke({})}


# ── Agent Memory ─────────────────────────────────────────────────────────────

@app.get("/api/memory")
def api_memory_all():
    return {"result": TOOL_MAP["recall_all_router_facts"].invoke({})}


@app.get("/api/memory/{router}")
def api_memory_router(router: str):
    return {"result": TOOL_MAP["recall_router_facts"].invoke({"router_name": router})}


@app.delete("/api/memory/{router}")
def api_memory_forget(router: str):
    return {"result": TOOL_MAP["forget_router_facts"].invoke({"router_name": router})}


# ── Static files ──────────────────────────────────────────────────────────────

app.mount("/fonts", StaticFiles(directory=FRONTEND_DIR / "fonts"), name="fonts")
app.mount("/assets", StaticFiles(directory=FRONTEND_DIR / "assets"), name="assets")
app.mount("/css", StaticFiles(directory=FRONTEND_DIR / "css"), name="css")
app.mount("/js", StaticFiles(directory=FRONTEND_DIR / "js"), name="js")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=False, log_level="info")
