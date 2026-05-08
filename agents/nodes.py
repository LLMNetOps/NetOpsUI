"""LangGraph node functions: supervisor + 5 specialist agents."""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone, timedelta
from typing import TYPE_CHECKING, Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_ollama import ChatOllama

from agents.loader import AgentLoader
from agents.tools import TOOL_MAP

if TYPE_CHECKING:
    from agent import NetworkOpsState

logger = logging.getLogger(__name__)

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL    = os.getenv("OLLAMA_MODEL", "gemma4:e4b")

WIB = timezone(timedelta(hours=7))

# ── Agent loader (single source of truth for tools, skills, system prompts) ───

_agent_loader = AgentLoader()

# Alias map derived from definitions (display only)
AGENT_ALIAS: dict[str, str] = {d.name: d.alias for d in _agent_loader.all()}


def _resolve_tools(agent_name: str) -> list:
    """Return callable tool list for an agent from its definition."""
    names = _agent_loader.tool_list(agent_name)
    tools = [TOOL_MAP[n] for n in names if n in TOOL_MAP]
    missing = [n for n in names if n not in TOOL_MAP]
    if missing:
        logger.warning("Agent '%s' references unknown tools: %s", agent_name, missing)
    return tools

# ── LLM factory ───────────────────────────────────────────────────────────────

def _make_llm(
    temperature: float = 0.3,
    json_mode: bool = False,
    model: str | None = None,
) -> ChatOllama:
    kwargs: dict[str, Any] = dict(
        base_url=OLLAMA_BASE_URL,
        model=model or OLLAMA_MODEL,
        temperature=temperature,
        num_predict=4096,
        num_ctx=16384,
        timeout=300,
    )
    if json_mode:
        kwargs["format"] = "json"
    return ChatOllama(**kwargs)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _now_str() -> str:
    return datetime.now(WIB).strftime("%H:%M:%S")


def _clean(text: str) -> str:
    return text.strip()


def _log(source: str, event_type: str, content: str) -> dict:
    """Build a log entry, resolving source to its display alias if defined."""
    display = AGENT_ALIAS.get(source, source)
    return {"timestamp": _now_str(), "source": display,
            "event_type": event_type, "content": content}


def _react_loop(
    llm_with_tools: Any,
    messages: list,
    tool_map: dict,
    agent_name: str,
    max_iters: int = 12,
) -> tuple[list, list]:
    """
    Run a ReAct tool-calling loop. Returns (updated_messages, log_entries).
    Stops when the LLM produces a response with no tool calls.
    """
    logs: list[dict] = []
    for _ in range(max_iters):
        response = llm_with_tools.invoke(messages)
        messages = messages + [response]

        if not getattr(response, "tool_calls", None):
            break

        for tc in response.tool_calls:
            name = tc["name"]
            args = tc.get("args", {})
            args_str = ", ".join(f"{k}={json.dumps(v)}" for k, v in args.items())
            logs.append(_log(agent_name, "tool_call", f"{name}({args_str})"))

            tool_fn = tool_map.get(name)
            if tool_fn is None:
                result = f"Error: tool '{name}' not found."
            else:
                try:
                    result = tool_fn.invoke(args)
                except Exception as exc:
                    result = f"Error: {exc}"

            preview = str(result)[:120].replace("\n", " ")
            if len(str(result)) > 120:
                preview += "…"
            logs.append(_log(agent_name, "tool_result", preview))
            messages.append(ToolMessage(content=str(result), tool_call_id=tc["id"]))

    return messages, logs


# ── Supervisor node ───────────────────────────────────────────────────────────

_SUPERVISOR_SYS = """\
{supervisor_body}

Agent tersedia:
{agent_descriptions}

Skill tersedia (nama → trigger):
{skill_list}

Balas HANYA dengan JSON valid, tanpa teks lain sebelum atau sesudah JSON.
Contoh format yang benar:
{{"next_agent":"monitor_agent","relevant_skills":[],"reasoning":"query status jaringan"}}

Field next_agent harus salah satu: {valid_agents}, END
Gunakan END jika pertanyaan sudah dijawab AI sebelumnya dalam percakapan ini.
"""


def supervisor_node(state: "NetworkOpsState") -> dict:
    from agent import _skill_lib  # noqa: PLC0415

    messages = state["messages"]

    last = messages[-1] if messages else None
    if isinstance(last, AIMessage) and _clean(last.content or ""):
        return {
            "next_agent": "END",
            "active_agent": "supervisor",
            "agent_log": [_log("supervisor", "routing", "→ END (respons sudah ada)")],
        }

    specialist_defs = [d for d in _agent_loader.all() if d.name != "supervisor"]
    agent_descriptions = "\n".join(
        f"- {d.name:20s} [{d.alias}] : {d.description}"
        for d in specialist_defs
    )
    valid_agent_names = {d.name for d in specialist_defs}
    valid_agents_str = ", ".join(sorted(valid_agent_names))

    skill_list = "\n".join(
        f"  {s.name}: {', '.join(s.triggers[:3])}"
        for s in _skill_lib.list_enabled()
    ) or "  (tidak ada skill aktif)"

    sys_msg = SystemMessage(content=_SUPERVISOR_SYS.format(
        supervisor_body=_agent_loader.system_prompt("supervisor"),
        agent_descriptions=agent_descriptions,
        skill_list=skill_list,
        valid_agents=valid_agents_str,
    ))
    recent = [m for m in messages if isinstance(m, (HumanMessage, AIMessage))][-6:]

    _supervisor_defn = _agent_loader.get("supervisor")
    _supervisor_model = _supervisor_defn.model if _supervisor_defn else None
    llm = _make_llm(temperature=0.1, json_mode=True, model=_supervisor_model)
    try:
        resp = llm.invoke([sys_msg] + recent)
        data = json.loads(_clean(resp.content))
    except Exception as exc:
        logger.warning("Supervisor routing parse error: %s", exc)
        data = {"next_agent": "monitor_agent", "relevant_skills": [], "reasoning": str(exc)}

    next_agent = data.get("next_agent", "monitor_agent")
    if next_agent not in valid_agent_names | {"END"}:
        next_agent = "monitor_agent"

    skills = data.get("relevant_skills", [])
    log_msg = f"→ {next_agent}  skills: {skills}  | {data.get('reasoning','')}"
    base_result = {
        "next_agent": next_agent,
        "active_agent": "supervisor",
        "injected_skills": skills,
        "agent_log": [_log("supervisor", "routing", log_msg)],
    }

    # Supervisor menjawab langsung jika END tapi belum ada respons AI (sapaan, pertanyaan umum)
    if next_agent == "END":
        has_ai_reply = any(
            isinstance(m, AIMessage) and _clean(m.content or "")
            for m in recent
        )
        if not has_ai_reply:
            _sup_alias = _supervisor_defn.alias if _supervisor_defn else "supervisor"
            llm_chat = _make_llm(temperature=0.5, model=_supervisor_model)
            chat_sys = SystemMessage(content=(
                f"Kamu adalah {_sup_alias.capitalize()}, supervisor operasional jaringan kampus universitas. "
                "Balas sapaan atau pertanyaan umum dengan ramah dan singkat dalam Bahasa Indonesia. "
                "Sebutkan bahwa kamu siap membantu kebutuhan operasional jaringan kampus."
            ))
            try:
                reply = llm_chat.invoke([chat_sys] + recent)
                base_result["messages"] = [reply]
            except Exception:
                pass

    return base_result


def route_from_supervisor(state: dict) -> str:
    return state.get("next_agent", "END")


# ── Specialist node factory ───────────────────────────────────────────────────

_SPECIALIST_SYS = """\
{agent_body}

Tool yang tersedia (HANYA ini yang boleh dipanggil): {tool_names}

ATURAN WAJIB — TOOL CALLING:
1. LANGSUNG panggil tool tanpa pengantar teks apapun.
2. DILARANG menulis "Mohon tunggu", "Saya akan menjalankan", "Saya akan memanggil",
   "Saya akan mensimulasikan", atau deskripsi rencana sebelum memanggil tool.
3. DILARANG mensimulasikan atau mengarang data — gunakan tool untuk mendapatkan data nyata.
4. Teks respons hanya boleh ditulis SETELAH semua tool selesai dipanggil.
5. Jika butuh data dari beberapa router, panggil tool satu per satu secara langsung.

{skill_context}
"""


def _make_specialist_node(agent_name: str, context_window: int = 10):
    defn = _agent_loader.get(agent_name)
    tools = _resolve_tools(agent_name)
    tool_map_local = {t.name: t for t in tools}
    tool_names_str = ", ".join(t.name for t in tools)
    agent_body = defn.body if defn else ""
    llm_with_tools = _make_llm(
        temperature=0.3, model=defn.model if defn else None
    ).bind_tools(tools)

    def _node(state: "NetworkOpsState") -> dict:
        from agent import _skill_lib  # noqa: PLC0415

        skill_names = state.get("injected_skills") or []
        skill_objs = [s for n in skill_names if (s := _skill_lib.get_by_name(n))]
        skill_ctx = _skill_lib.inject_context(skill_objs) if skill_objs else ""

        sys_content = _SPECIALIST_SYS.format(
            agent_body=agent_body,
            tool_names=tool_names_str,
            skill_context=skill_ctx,
        ).strip()
        sys_msg = SystemMessage(content=sys_content)

        context_msgs = list(state["messages"])[-context_window:]
        all_msgs, logs = _react_loop(
            llm_with_tools,
            [sys_msg] + context_msgs,
            tool_map_local,
            agent_name,
        )

        final_msg = all_msgs[-1]
        if isinstance(final_msg, AIMessage):
            content = _clean(final_msg.content or "")
            if content:
                final_msg = AIMessage(content=content)

        logs.append(_log(agent_name, "routing", "← kembali ke supervisor"))

        return {
            "messages": [final_msg],
            "active_agent": agent_name,
            "next_agent": "supervisor",
            "agent_log": logs,
        }

    _node.__name__ = agent_name
    return _node


# ── Config node with human-in-the-loop approval ───────────────────────────────

_config_defn = _agent_loader.get("config_agent")
_CONFIG_TOOLS = _resolve_tools("config_agent")
_CONFIG_TOOLS_MAP = {t.name: t for t in _CONFIG_TOOLS}
_CONFIG_LLM = _make_llm(
    temperature=0.3, model=_config_defn.model if _config_defn else None
).bind_tools(_CONFIG_TOOLS)
_APPROVAL_REQUIRED_TOOLS = set(
    _config_defn.approval_required_tools if _config_defn else ["backup_router_config"]
)


def config_node(state: dict) -> dict:
    """Config specialist with interrupt() gate for destructive tools."""
    from agent import _skill_lib  # noqa: PLC0415
    from langgraph.types import interrupt  # noqa: PLC0415

    skill_names = state.get("injected_skills") or []
    skill_objs = [s for n in skill_names if (s := _skill_lib.get_by_name(n))]
    skill_ctx = _skill_lib.inject_context(skill_objs) if skill_objs else ""

    _config_tool_names = ", ".join(t.name for t in _CONFIG_TOOLS)
    sys_msg = SystemMessage(content=_SPECIALIST_SYS.format(
        agent_body=_agent_loader.system_prompt("config_agent"),
        tool_names=_config_tool_names,
        skill_context=skill_ctx,
    ).strip())

    messages = [sys_msg] + list(state["messages"])[-10:]
    logs: list[dict] = []

    for _ in range(12):
        response = _CONFIG_LLM.invoke(messages)
        messages = messages + [response]

        if not getattr(response, "tool_calls", None):
            break

        for tc in response.tool_calls:
            name = tc["name"]
            args = tc.get("args", {})
            args_str = ", ".join(f"{k}={json.dumps(v)}" for k, v in args.items())
            logs.append(_log("config_agent", "tool_call", f"{name}({args_str})"))

            if name in _APPROVAL_REQUIRED_TOOLS:
                router = args.get("router_name", "router")
                approval_req = {
                    "agent": "config_agent",
                    "action": f"Backup config router '{router}'",
                    "risk_level": "medium",
                    "details": args,
                }
                logs.append(_log("config_agent", "approval_required",
                                  f"Menunggu approval: {approval_req['action']}"))
                decision = interrupt(approval_req)

                if decision != "approved":
                    result = f"Aksi dibatalkan oleh operator (keputusan: {decision})."
                    logs.append(_log("config_agent", "tool_result", result))
                    messages.append(ToolMessage(content=result, tool_call_id=tc["id"]))
                    continue

                logs.append(_log("config_agent", "tool_result", "Operator menyetujui — eksekusi backup..."))

            tool_fn = _CONFIG_TOOLS_MAP.get(name)
            if tool_fn is None:
                result = f"Error: tool '{name}' tidak ditemukan."
            else:
                try:
                    result = tool_fn.invoke(args)
                except Exception as exc:
                    result = f"Error: {exc}"

            preview = str(result)[:120].replace("\n", " ")
            if len(str(result)) > 120:
                preview += "…"
            logs.append(_log("config_agent", "tool_result", preview))
            messages.append(ToolMessage(content=str(result), tool_call_id=tc["id"]))

    final_msg = messages[-1]
    if isinstance(final_msg, AIMessage):
        content = _clean(final_msg.content or "")
        if content:
            final_msg = AIMessage(content=content)

    logs.append(_log("config_agent", "routing", "← kembali ke supervisor"))
    return {
        "messages": [final_msg],
        "active_agent": "config_agent",
        "next_agent": "supervisor",
        "agent_log": logs,
    }


# ── Exported node functions ───────────────────────────────────────────────────

monitor_node  = _make_specialist_node("monitor_agent")
diagnose_node = _make_specialist_node("diagnose_agent")
security_node = _make_specialist_node("security_agent")
document_node = _make_specialist_node("document_agent", context_window=20)
# config_node defined above with interrupt() support
