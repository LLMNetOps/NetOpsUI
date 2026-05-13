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
    num_ctx: int = 8192,
    num_predict: int = 2048,
    timeout: int = 300,
    agent_name: str | None = None,
    base_url: str | None = None,
    reasoning: bool = False,
) -> ChatOllama:
    from agents.metrics import TokenMetricsCallback  # noqa: PLC0415
    kwargs: dict[str, Any] = dict(
        base_url=base_url or OLLAMA_BASE_URL,
        model=model or OLLAMA_MODEL,
        temperature=temperature,
        num_predict=num_predict,
        num_ctx=num_ctx,
        timeout=timeout,
        reasoning=reasoning,
        callbacks=[TokenMetricsCallback(agent_name or "unknown", num_ctx, num_predict)],
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
    max_iters: int = 20,
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


# ── Supervisor helpers ────────────────────────────────────────────────────────

import re as _re

_KEYWORD_ROUTES: list[tuple[list[str], str]] = [
    (["status", "monitor", "ping", "reachability", "traffic", "bandwidth",
      "interface", "brief", "ringkasan", "uptime", "latency", "packet loss",
      "cek jaringan", "cek router", "kondisi jaringan"], "monitor_agent"),
    (["diagnos", "troubleshoot", "error", "down", "gangguan", "masalah",
      "ospf", "bgp", "routing", "neighbor", "tidak bisa", "putus", "lambat",
      "analisis"], "diagnose_agent"),
    (["backup", "restore", "konfigurasi", "config", "setting", "ubah",
      "ganti", "terapkan"], "config_agent"),
    (["security", "keamanan", "firewall", "intrusion", "audit keamanan",
      "serangan", "vulnerability", "port scan"], "security_agent"),
    (["laporan", "report", "dokumen", "tulis laporan", "buat laporan",
      "dokumentasi", "skill"], "document_agent"),
]


def _keyword_route(messages: list, valid_agents: set[str]) -> str | None:
    """Keyword fallback routing dari pesan user terakhir. None jika tidak cocok."""
    last_human = next(
        (m.content for m in reversed(messages) if isinstance(m, HumanMessage)), ""
    )
    text = last_human.lower()
    for keywords, agent in _KEYWORD_ROUTES:
        if any(k in text for k in keywords) and agent in valid_agents:
            return agent
    return None


def _parse_supervisor_response(raw: str) -> dict | None:
    """Extract JSON dari respons supervisor, toleran terhadap think-tags dan teks extra."""
    text = _re.sub(r"<think>.*?</think>", "", raw, flags=_re.DOTALL).strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = _re.search(r'\{[^{}]+\}', text, _re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return None


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
        _early_save_kw = {"simpan", "tulis file", "buat laporan", "buatkan laporan",
                          "buat dokumen", "buatkan dokumen", "catat ke file",
                          "write report", "save", "write file", "laporan routing",
                          "laporan bgp", "laporan ospf", "laporan jaringan"}
        _early_human = next((m for m in reversed(messages) if isinstance(m, HumanMessage)), None)
        _early_wants_file = bool(_early_human and any(
            kw in (_early_human.content or "").lower() for kw in _early_save_kw
        ))
        _early_prev = state.get("active_agent", "")
        # Jika data-agent baru selesai dan user minta file → langsung route ke document_agent
        if _early_wants_file and _early_prev in ("monitor_agent", "security_agent", "diagnose_agent"):
            _doc_log = f"→ document_agent  skills: ['document-writing']  | file-save: {_early_prev} selesai, route ke document_agent"
            # Deteksi tipe laporan untuk memilih template yang tepat
            _orig_req = (_early_human.content or "").lower() if _early_human else ""
            if any(kw in _orig_req for kw in ("bgp", "ospf", "routing")):
                _template_hint = "routing-bgp-ospf"
                _router_hint = ""
                # Cari nama router dari permintaan asli
                import re as _re
                _rm = _re.search(r'(gate-\S+|router\s+(\S+))', _orig_req, _re.IGNORECASE)
                if _rm:
                    _router_hint = f" untuk router {_rm.group(0).strip()}"
                _doc_content = (
                    f"Analisis routing BGP/OSPF dari Agus sudah lengkap{_router_hint}. "
                    "Buat laporan file menggunakan template `routing-bgp-ospf`. "
                    "WAJIB panggil: get_current_time(), get_system_info(), get_bgp_sessions(), get_ospf_neighbors() "
                    "untuk mendapatkan data tabel yang akurat. "
                    "Gunakan analisis di atas (cross-reference, root cause, rekomendasi) untuk bagian teks analisis. "
                    "Simpan dengan write_document() — file HARUS tersimpan ke disk."
                )
            else:
                _doc_content = (
                    "Data dari agent sebelumnya sudah lengkap. "
                    "Simpan sekarang ke file menggunakan tool `write_document`. "
                    "Mulai dengan `list_templates`, pilih template yang sesuai, lalu panggil `write_document`. "
                    "JANGAN hanya menulis teks — file HARUS tersimpan ke disk."
                )
            _doc_instruction = HumanMessage(content=_doc_content)
            return {
                "next_agent": "document_agent",
                "active_agent": "supervisor",
                "injected_skills": ["document-writing"],
                "messages": [_doc_instruction],
                "agent_log": [_log("supervisor", "routing", _doc_log)],
            }
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

    _supervisor_defn = _agent_loader.get("supervisor")
    _supervisor_model = _supervisor_defn.model if _supervisor_defn else None

    sys_msg = SystemMessage(content=_SUPERVISOR_SYS.format(
        supervisor_body=_agent_loader.system_prompt("supervisor"),
        agent_descriptions=agent_descriptions,
        skill_list=skill_list,
        valid_agents=valid_agents_str,
    ))
    _sup_ctx_window = _supervisor_defn.context_window if _supervisor_defn else 6
    recent = [m for m in messages if isinstance(m, (HumanMessage, AIMessage))][-_sup_ctx_window:]
    llm = _make_llm(
        temperature=0.1,
        json_mode=True,
        model=_supervisor_model,
        num_ctx=_supervisor_defn.num_ctx if _supervisor_defn else 4096,
        num_predict=_supervisor_defn.num_predict if _supervisor_defn else 256,
        timeout=_supervisor_defn.timeout if _supervisor_defn else 60,
        agent_name="supervisor",
        base_url=(_supervisor_defn.ollama_host if _supervisor_defn else "") or None,
        reasoning=False,
    )
    try:
        resp = llm.invoke([sys_msg] + recent)
        logger.debug("Supervisor raw content: %r | metadata: %s",
                     resp.content[:300] if resp.content else "(empty)",
                     getattr(resp, "response_metadata", {}))
        data = _parse_supervisor_response(resp.content) or {}
        if not data:
            raise ValueError("empty or unparseable supervisor response")
    except Exception as exc:
        logger.warning("Supervisor routing parse error: %s", exc)
        keyword_agent = _keyword_route(messages, valid_agent_names)
        fallback = keyword_agent or "END"
        data = {"next_agent": fallback, "relevant_skills": [],
                "reasoning": f"keyword-fallback({fallback}): {exc}"}

    next_agent = data.get("next_agent", "END")
    if next_agent not in valid_agent_names | {"END"}:
        next_agent = _keyword_route(messages, valid_agent_names) or "END"

    _save_kw = {"simpan", "tulis file", "buat laporan", "buatkan laporan",
                "buat dokumen", "buatkan dokumen", "catat ke file",
                "write report", "save", "write file", "laporan routing",
                "laporan bgp", "laporan ospf", "laporan jaringan"}
    _last_human = next((m for m in reversed(messages) if isinstance(m, HumanMessage)), None)
    _wants_file = bool(_last_human and any(
        kw in (_last_human.content or "").lower() for kw in _save_kw
    ))
    _prev_agent = state.get("active_agent", "")

    # Override END → document_agent jika user minta simpan file dan data-agent baru selesai
    if next_agent == "END" and "document_agent" in valid_agent_names:
        if _wants_file and _prev_agent in ("monitor_agent", "security_agent", "diagnose_agent"):
            next_agent = "document_agent"
            data["reasoning"] = f"file-save override: {_prev_agent} returned data, routing to document_agent"

    # Override → END jika document_agent baru selesai (cegah loop)
    # document_agent selalu terminal (handoff_to: []) — apapun yang ditulis, selalu END
    if next_agent != "END" and _prev_agent == "document_agent":
        next_agent = "END"
        data["reasoning"] = "document_agent selesai, routing ke END"

    # Loop guard: jangan route ke specialist yang sama yang baru saja selesai.
    # Cegah skenario: specialist → supervisor (empty JSON) → keyword-fallback → specialist sama → loop
    if next_agent == _prev_agent and _prev_agent in valid_agent_names:
        next_agent = "END"
        data["reasoning"] = f"loop guard: {_prev_agent} baru selesai, cegah re-route ke agent sama"

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
        # Cari posisi HumanMessage terakhir — cek AI reply hanya setelah itu
        last_human_idx = max(
            (i for i, m in enumerate(recent) if isinstance(m, HumanMessage)),
            default=-1,
        )
        has_ai_reply = any(
            isinstance(m, AIMessage) and _clean(m.content or "")
            for m in recent[last_human_idx + 1:]
        )
        if not has_ai_reply:
            _chat_prompt = (
                _supervisor_defn.chat_prompt if _supervisor_defn and _supervisor_defn.chat_prompt
                else (
                    f"Kamu adalah {_supervisor_defn.alias.capitalize() if _supervisor_defn else 'Supervisor'}, "
                    "supervisor operasional jaringan kampus universitas. "
                    "Balas sapaan atau pertanyaan umum dengan ramah dan singkat dalam Bahasa Indonesia."
                )
            )
            llm_chat = _make_llm(
                temperature=0.5,
                model=_supervisor_model,
                num_ctx=_supervisor_defn.num_ctx if _supervisor_defn else 8192,
                num_predict=_supervisor_defn.num_predict if _supervisor_defn else 2048,
                timeout=_supervisor_defn.timeout if _supervisor_defn else 60,
                agent_name="supervisor",
                base_url=(_supervisor_defn.ollama_host if _supervisor_defn else "") or None,
                reasoning=False,
            )
            chat_sys = SystemMessage(content=_chat_prompt)
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
6. Setelah menerima hasil tool, jika masih ada tugas berikutnya, LANGSUNG panggil tool
   berikutnya tanpa menulis teks konfirmasi, ringkasan, atau "Lanjut ke langkah X".

{skill_context}
"""


def _make_specialist_node(agent_name: str):
    defn = _agent_loader.get(agent_name)
    tools = _resolve_tools(agent_name)
    tool_map_local = {t.name: t for t in tools}
    tool_names_str = ", ".join(t.name for t in tools)
    agent_body = defn.body if defn else ""
    context_window = defn.context_window if defn else 10
    _model = defn.model if defn else None
    _num_ctx = defn.num_ctx if defn else 8192
    _num_predict = defn.num_predict if defn else 2048
    _timeout = defn.timeout if defn else 300
    _ollama_host = defn.ollama_host if defn else ""
    _reasoning = defn.reasoning if defn else False
    llm_with_tools = _make_llm(
        temperature=0.3,
        model=_model,
        num_ctx=_num_ctx,
        num_predict=_num_predict,
        timeout=_timeout,
        agent_name=agent_name,
        base_url=_ollama_host or None,
        reasoning=_reasoning,
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
        need_summary = True
        if isinstance(final_msg, AIMessage):
            content = _clean(final_msg.content or "")
            if content:
                final_msg = AIMessage(content=content)
                need_summary = False

        if need_summary:
            # AIMessage kosong ATAU ToolMessage (max_iters tercapai) — force summary
            try:
                llm_plain = _make_llm(
                    temperature=0.3, model=_model,
                    num_ctx=_num_ctx, num_predict=_num_predict, timeout=_timeout,
                    agent_name=agent_name,
                    base_url=_ollama_host or None,
                    reasoning=False,
                )
                summary = llm_plain.invoke(all_msgs)
                summary_content = _clean(summary.content or "")
                if summary_content:
                    final_msg = AIMessage(content=summary_content)
                    logs.append(_log(agent_name, "tool_result", "(forced summary generated)"))
            except Exception as exc:
                logger.warning("Forced summary failed for %s: %s", agent_name, exc)

        # Safety net: final_msg HARUS selalu AIMessage dengan content.
        # Jika masih ToolMessage atau AIMessage kosong, ekstrak hasil tool terpanjang
        # (biasanya paling informatif, hindari ambil tool terakhir yang arbitrary).
        if not (isinstance(final_msg, AIMessage) and _clean(getattr(final_msg, "content", "") or "")):
            tool_msgs = [m for m in all_msgs if isinstance(m, ToolMessage)]
            if tool_msgs:
                best = max(tool_msgs, key=lambda m: len(m.content or ""))
                raw = best.content
            else:
                raw = "(tidak ada data)"
            final_msg = AIMessage(content=f"Hasil:\n{raw}")
            logs.append(_log(agent_name, "tool_result", "(safety net: paksa AIMessage dari tool result)"))

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
    temperature=0.3,
    model=_config_defn.model if _config_defn else None,
    num_ctx=_config_defn.num_ctx if _config_defn else 8192,
    num_predict=_config_defn.num_predict if _config_defn else 2048,
    timeout=_config_defn.timeout if _config_defn else 180,
    agent_name="config_agent",
    base_url=(_config_defn.ollama_host if _config_defn else "") or None,
    reasoning=_config_defn.reasoning if _config_defn else False,
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
                if name == "backup_router_config":
                    action_desc = f"Backup config router '{router}'"
                    risk = "medium"
                elif name == "run_command_write":
                    cmd = args.get("command", "")
                    action_desc = f"Write command di '{router}': {cmd}"
                    risk = "high"
                else:
                    action_desc = f"Operasi write di '{router}' via {name}"
                    risk = "medium"
                approval_req = {
                    "agent": "config_agent",
                    "action": action_desc,
                    "risk_level": risk,
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

                logs.append(_log("config_agent", "tool_result", f"Operator menyetujui — eksekusi {name}..."))

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
document_node = _make_specialist_node("document_agent")
# config_node defined above with interrupt() support
