"""LangGraph node functions: supervisor + 5 specialist agents."""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone, timedelta
from typing import TYPE_CHECKING, Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_ollama import ChatOllama

from agents.tools import (
    MONITOR_TOOLS, DIAGNOSE_TOOLS, CONFIG_TOOLS, SECURITY_TOOLS, DOCUMENT_TOOLS,
)

if TYPE_CHECKING:
    from agent import NetworkOpsState

logger = logging.getLogger(__name__)

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL    = os.getenv("OLLAMA_MODEL", "gemma4:e4b")

WIB = timezone(timedelta(hours=7))

# ── Agent alias mapping (display only — tidak mempengaruhi routing/kode) ──────

AGENT_ALIAS: dict[str, str] = {
    "supervisor":    "bambang",
    "monitor_agent": "eko",
    "diagnose_agent": "agus",
    "config_agent":  "joko",
    "security_agent": "satria",
    "document_agent": "budi",
}

# ── LLM factory ───────────────────────────────────────────────────────────────

def _make_llm(temperature: float = 0.3, json_mode: bool = False) -> ChatOllama:
    kwargs: dict[str, Any] = dict(
        base_url=OLLAMA_BASE_URL,
        model=OLLAMA_MODEL,
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
Kamu adalah supervisor operasional jaringan kampus. Tugasmu menganalisis permintaan \
operator dan memutuskan agent yang menanganinya.

Agent tersedia:
- monitor_agent  [eko]    : status jaringan, health check, DHCP overview, interface stats
- diagnose_agent [agus]   : masalah konektivitas, ping/traceroute, DHCP client gagal, packet loss
- config_agent   [joko]   : baca konfigurasi router, config backup, eksport config
- security_agent [satria] : audit keamanan, user accounts, NTP sync, firewall check
- document_agent [budi]   : tulis dokumen laporan ke file, baca/buat template, kurasi hasil agent lain

Untuk laporan komprehensif yang butuh data multi-domain: gunakan monitor_agent atau
security_agent terlebih dahulu untuk mengumpulkan data, baru route ke document_agent
untuk kompilasi dan penulisan dokumen ke file.

Skill tersedia (nama → trigger):
{skill_list}

Balas HANYA dengan JSON valid, tanpa teks lain sebelum atau sesudah JSON.
Contoh format yang benar:
{{"next_agent":"monitor_agent","relevant_skills":[],"reasoning":"query status jaringan"}}

Field next_agent harus salah satu: monitor_agent, diagnose_agent, config_agent, security_agent, document_agent, END
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

    skill_list = "\n".join(
        f"  {s.name}: {', '.join(s.triggers[:3])}"
        for s in _skill_lib.list_enabled()
    ) or "  (tidak ada skill aktif)"

    sys_msg = SystemMessage(content=_SUPERVISOR_SYS.format(skill_list=skill_list))
    recent = [m for m in messages if isinstance(m, (HumanMessage, AIMessage))][-6:]

    llm = _make_llm(temperature=0.1, json_mode=True)
    try:
        resp = llm.invoke([sys_msg] + recent)
        data = json.loads(_clean(resp.content))
    except Exception as exc:
        logger.warning("Supervisor routing parse error: %s", exc)
        data = {"next_agent": "monitor_agent", "relevant_skills": [], "reasoning": str(exc)}

    next_agent = data.get("next_agent", "monitor_agent")
    if next_agent not in ("monitor_agent", "diagnose_agent", "config_agent", "security_agent", "document_agent", "END"):
        next_agent = "monitor_agent"

    skills = data.get("relevant_skills", [])
    log_msg = f"→ {next_agent}  skills: {skills}  | {data.get('reasoning','')}"
    base_result = {
        "next_agent": next_agent,
        "active_agent": "supervisor",
        "injected_skills": skills,
        "agent_log": [_log("supervisor", "routing", log_msg)],
    }

    # Bambang menjawab langsung jika END tapi belum ada respons AI (sapaan, pertanyaan umum)
    if next_agent == "END":
        has_ai_reply = any(
            isinstance(m, AIMessage) and _clean(m.content or "")
            for m in recent
        )
        if not has_ai_reply:
            llm_chat = _make_llm(temperature=0.5)
            chat_sys = SystemMessage(content=(
                "Kamu adalah Bambang, supervisor operasional jaringan kampus universitas. "
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
Kamu adalah {role} untuk jaringan kampus universitas.
Infrastruktur menggunakan MikroTik RouterOS v6/v7. Jawab dalam Bahasa Indonesia,
teknis dan ringkas. Gunakan backtick untuk istilah teknis.

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

_AGENT_ROLES = {
    "monitor_agent":  "agen monitoring jaringan — bertugas menganalisis status, health, dan statistik jaringan",
    "diagnose_agent": "agen diagnostik jaringan — bertugas menginvestigasi dan mendiagnosa masalah konektivitas",
    "config_agent":   "agen konfigurasi — bertugas membaca dan memverifikasi konfigurasi router",
    "security_agent": "agen keamanan jaringan — bertugas mengaudit postur keamanan router dan akun",
    "document_agent": "agen dokumentasi — bertugas membuat laporan terstruktur, mengelola template, dan mengkurasi hasil agent lain menjadi dokumen laporan yang tersimpan di file",
}


def _make_specialist_node(agent_name: str, tools: list, context_window: int = 10):
    tool_map_local = {t.name: t for t in tools}
    tool_names_str = ", ".join(t.name for t in tools)
    llm_with_tools = _make_llm(temperature=0.3).bind_tools(tools)

    def _node(state: "NetworkOpsState") -> dict:
        from agent import _skill_lib  # noqa: PLC0415

        skill_names = state.get("injected_skills") or []
        skill_objs = [s for n in skill_names if (s := _skill_lib.get_by_name(n))]
        skill_ctx = _skill_lib.inject_context(skill_objs) if skill_objs else ""

        sys_content = _SPECIALIST_SYS.format(
            role=_AGENT_ROLES[agent_name],
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

# Tools that require operator approval before execution
_APPROVAL_REQUIRED_TOOLS = {"backup_router_config"}

_CONFIG_TOOLS_MAP = {t.name: t for t in CONFIG_TOOLS}
_CONFIG_LLM = _make_llm(temperature=0.3).bind_tools(CONFIG_TOOLS)


def config_node(state: dict) -> dict:
    """Config specialist with interrupt() gate for destructive tools."""
    from agent import _skill_lib  # noqa: PLC0415
    from langgraph.types import interrupt  # noqa: PLC0415

    skill_names = state.get("injected_skills") or []
    skill_objs = [s for n in skill_names if (s := _skill_lib.get_by_name(n))]
    skill_ctx = _skill_lib.inject_context(skill_objs) if skill_objs else ""

    _config_tool_names = ", ".join(t.name for t in CONFIG_TOOLS)
    sys_msg = SystemMessage(content=_SPECIALIST_SYS.format(
        role=_AGENT_ROLES["config_agent"],
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

monitor_node  = _make_specialist_node("monitor_agent",  MONITOR_TOOLS)
diagnose_node = _make_specialist_node("diagnose_agent", DIAGNOSE_TOOLS)
security_node = _make_specialist_node("security_agent", SECURITY_TOOLS)
document_node = _make_specialist_node("document_agent", DOCUMENT_TOOLS, context_window=20)
# config_node defined above with interrupt() support
