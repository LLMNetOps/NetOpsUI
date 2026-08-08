"""LangGraph node functions: supervisor + 5 specialist agents."""

from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime, timezone, timedelta
from typing import TYPE_CHECKING, Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI

from pathlib import Path

from agents.loader import AgentLoader
from agents.tools import TOOL_MAP
from tools.db import db_get_llm_config

# ── Pedoman agent — global conduct rules loaded from editable Markdown ─────────

def _load_pedoman() -> str:
    """Load pedoman-agent.md, strip YAML frontmatter, return body only."""
    path = Path(__file__).parent.parent / "skills" / "pedoman-agent.md"
    try:
        text = path.read_text(encoding="utf-8")
        if text.startswith("---"):
            end = text.find("---", 3)
            return text[end + 3:].strip() if end != -1 else text
        return text.strip()
    except FileNotFoundError:
        logger.warning("pedoman-agent.md tidak ditemukan — pedoman kosong")
        return ""

_PEDOMAN = _load_pedoman()

if TYPE_CHECKING:
    from agent import NetworkOpsState

logger = logging.getLogger(__name__)

OLLAMA_API_KEY  = os.getenv("OLLAMA_API_KEY", "sk-placeholder")


def _ollama_defaults() -> tuple[str, str, str]:
    """Base URL, model & API key resolved live from Settings → Environment (DB),
    falling back to .env when the DB row is blank (e.g. never saved via UI)."""
    cfg = db_get_llm_config()
    base_url = cfg.get("base_url") or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    model = cfg.get("model") or os.getenv("OLLAMA_MODEL", "qwen3.6:27b")
    api_key = cfg.get("api_key") or OLLAMA_API_KEY
    return base_url, model, api_key

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
    api_key: str | None = None,
    reasoning: bool = False,  # kept for API compat; ignored (OpenAI API doesn't support it)
    max_retries: int = 2,
) -> ChatOpenAI:
    from agents.metrics import TokenMetricsCallback  # noqa: PLC0415
    default_base_url, default_model, default_api_key = _ollama_defaults()
    model_kwargs: dict[str, Any] = {}
    if json_mode:
        model_kwargs["response_format"] = {"type": "json_object"}
    return ChatOpenAI(
        base_url=base_url or default_base_url,
        api_key=api_key or default_api_key,
        model=model or default_model,
        temperature=temperature,
        max_tokens=num_predict,
        timeout=timeout,
        max_retries=max_retries,
        # extra_body lets Ollama pick up num_ctx without triggering openai client validation
        extra_body={"options": {"num_ctx": num_ctx}},
        model_kwargs=model_kwargs,
        callbacks=[TokenMetricsCallback(agent_name or "unknown", num_ctx, num_predict)],
    )


# ── Helpers ───────────────────────────────────────────────────────────────────

def _now_str() -> str:
    return datetime.now(WIB).strftime("%H:%M:%S")


def _clean(text: str) -> str:
    return text.strip()


def _visible_content(raw: str) -> str:
    """What would actually be shown after <think>...</think> stripping
    (mirrors the regex agent.py applies when streaming to the UI). Also
    strips a dangling *unclosed* <think> block — e.g. a reasoning model that
    hit num_predict mid-thought and never reached its answer — so callers can
    detect a reply that is genuinely empty of visible content, not just one
    that happens to be full of hidden reasoning."""
    text = re.sub(r"<think>.*?</think>", "", raw or "", flags=re.DOTALL)
    text = re.sub(r"<think>.*$", "", text, flags=re.DOTALL)
    return text.strip()


def _log(source: str, event_type: str, content: str) -> dict:
    """Build a log entry, resolving source to its display alias if defined."""
    display = AGENT_ALIAS.get(source, source)
    return {"timestamp": _now_str(), "source": display,
            "event_type": event_type, "content": content}


def _get_writer():
    """Return a LangGraph custom-stream writer, or a no-op if unavailable
    (e.g. called outside a graph.stream(..., stream_mode='custom') context).
    Lets nodes push tool_call/tool_result events to the UI the instant they
    happen, instead of only after the whole node (which may loop over many
    tool calls) returns."""
    try:
        from langgraph.config import get_stream_writer  # noqa: PLC0415
        return get_stream_writer()
    except Exception:
        return lambda *_a, **_kw: None


def _last_specialist_from_log(state: dict, valid_agent_names: set[str]) -> str | None:
    """Scan agent_log backwards to find the last specialist that ran."""
    agent_log = state.get("agent_log", [])
    if not agent_log:
        return None
    alias_to_agent = {alias: name for name, alias in AGENT_ALIAS.items()}
    for entry in reversed(agent_log):
        source = entry.get("source", "")
        agent_name = alias_to_agent.get(source, source)
        if agent_name in valid_agent_names:
            return agent_name
    return None


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
    writer = _get_writer()
    logs: list[dict] = []

    def _emit(event_type: str, content: str) -> None:
        entry = _log(agent_name, event_type, content)
        logs.append(entry)
        writer(entry)

    for _ in range(max_iters):
        response = llm_with_tools.invoke(messages)
        messages = messages + [response]

        if not getattr(response, "tool_calls", None):
            break

        for tc in response.tool_calls:
            name = tc["name"]
            args = tc.get("args", {})
            args_str = ", ".join(f"{k}={json.dumps(v)}" for k, v in args.items())
            _emit("tool_call", f"{name}({args_str})")

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
            _emit("tool_result", preview)
            messages.append(ToolMessage(content=str(result), tool_call_id=tc["id"]))

    return messages, logs


# ── Supervisor helpers ────────────────────────────────────────────────────────

import re as _re

_GREETING_PATTERNS: list[str] = [
    "halo", "hallo", "hi", "hello", "hey", "hai",
    "selamat pagi", "selamat siang", "selamat sore", "selamat malam",
    "siapa kamu", "siapa anda", "kamu siapa", "anda siapa",
    "kamu apa", "kamu bisa apa", "anda bisa apa",
    "perkenalkan", "perkenalan",
]


def _is_greeting(messages: list) -> bool:
    """Return True if the last human message is a simple greeting or identity question."""
    last_human = next(
        (m.content for m in reversed(messages) if isinstance(m, HumanMessage)), ""
    )
    text = last_human.strip().lower()
    # Must be short (≤ 60 chars) to avoid false positives on "halo, cek router..."
    if len(text) > 60:
        return False
    return any(re.search(rf'\b{re.escape(pat)}\b', text) for pat in _GREETING_PATTERNS)


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


# ── Intent continuation (deterministic, no LLM) ──────────────────────────────

_MONITORING_KW = {"cek", "status", "check", "monitor", "kondisi", "health",
                  "ping", "sistem", "uptime", "resource", "reachability"}
_DIAGNOSE_KW   = {"diagnosa", "analisis", "bgp", "ospf", "routing",
                  "troubleshoot", "kenapa", "masalah", "lambat", "putus"}


def _intent_continuation(intent: str, prev_agent: str, valid_agents: set[str]) -> str | None:
    """
    Setelah prev_agent selesai, cek apakah original_intent belum terpenuhi.
    Return nama agent berikutnya, atau None jika intent sudah selesai (→ END).
    Deterministic — tidak memanggil LLM.
    """
    if not intent or not prev_agent:
        return None
    t = intent.lower()
    # Setelah config_agent (discovery/tambah router): lanjut ke monitoring/diagnosa jika itu intent-nya
    if prev_agent == "config_agent":
        if any(kw in t for kw in _MONITORING_KW) and "monitor_agent" in valid_agents:
            return "monitor_agent"
        if any(kw in t for kw in _DIAGNOSE_KW) and "diagnose_agent" in valid_agents:
            return "diagnose_agent"
    # Setelah netbox_agent (discovery): lanjut ke monitoring jika intent adalah monitoring
    if prev_agent == "netbox_agent":
        if any(kw in t for kw in _MONITORING_KW) and "monitor_agent" in valid_agents:
            return "monitor_agent"
    return None


# ── Supervisor node ───────────────────────────────────────────────────────────

_SUPERVISOR_SYS = """\
{supervisor_body}

Agent tersedia:
{agent_descriptions}

Skill tersedia (nama → trigger):
{skill_list}

Router yang terdaftar di config.yaml:
{router_list}

Jika operator menyebut nama router yang TIDAK ada dalam daftar di atas, inject skill
'router-discovery' dan route ke config_agent — jangan langsung END atau tanya klarifikasi.

Balas HANYA dengan JSON valid, tanpa teks lain sebelum atau sesudah JSON.
Contoh format yang benar:
{{"next_agent":"monitor_agent","relevant_skills":[],"reasoning":"query status jaringan"}}

Field next_agent harus salah satu: {valid_agents}, END
Gunakan END jika pertanyaan sudah dijawab AI sebelumnya dalam percakapan ini.
{intent_context}
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
        _early_intent = state.get("original_intent", "")

        # Priority 1: Jika intent awal belum terpenuhi, lanjut ke agent berikutnya
        _early_valid = {d.name for d in _agent_loader.all() if d.name != "supervisor"}
        _continuation = _intent_continuation(_early_intent, _early_prev, _early_valid)
        if _continuation and _continuation != _early_prev:
            _cont_log = (
                f"→ {_continuation}  skills: []  | "
                f"intent-continuation: '{_early_intent[:60]}' belum terpenuhi setelah {_early_prev}"
            )
            _cont_msg = HumanMessage(content=(
                f"Lanjutkan task awal operator: {_early_intent}\n"
                f"Agent sebelumnya ({_early_prev}) sudah selesai. "
                f"Sekarang kerjakan bagian yang belum: {_early_intent}"
            ))
            return {
                "next_agent": _continuation,
                "active_agent": "supervisor",
                "injected_skills": [],
                "messages": [_cont_msg],
                "agent_log": [_log("supervisor", "routing", _cont_log)],
            }

        # Priority 2: Jika data-agent baru selesai dan user minta file → route ke document_agent
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

        # Priority 3: post-validasi routing — setelah wati selesai, baca delegation string.
        # HARUS ada di early-return block karena supervisor selalu early-return saat last == AIMessage.
        if _early_prev == "validasi_agent":
            _wati_txt = _clean(last.content or "")
            if "delegasikan ke config_agent" in _wati_txt and "config_agent" in _early_valid:
                _wati_log = "→ config_agent  skills: []  | validasi-delegation: wati → config_agent"
                return {
                    "next_agent": "config_agent",
                    "active_agent": "supervisor",
                    "injected_skills": [],
                    "original_intent": _early_intent,
                    "messages": [HumanMessage(content=(
                        "Wati (validasi_agent) sudah memverifikasi action items. "
                        "Lihat verdict validasi di atas — eksekusi item KONFIRMASI sesuai rekomendasi Wati. "
                        "Minta approval operator sebelum setiap operasi write."
                    ))],
                    "agent_log": [_log("supervisor", "routing", _wati_log)],
                }
            elif "delegasikan ke diagnose_agent" in _wati_txt and "diagnose_agent" in _early_valid:
                _wati_log = "→ diagnose_agent  skills: []  | validasi-delegation: wati → diagnose_agent"
                return {
                    "next_agent": "diagnose_agent",
                    "active_agent": "supervisor",
                    "injected_skills": [],
                    "original_intent": _early_intent,
                    "messages": [HumanMessage(content=(
                        "Wati (validasi_agent) sudah memverifikasi action items — root cause dari item KONFIRMASI tidak jelas. "
                        "Lakukan investigasi lebih dalam berdasarkan verdict Wati di atas."
                    ))],
                    "agent_log": [_log("supervisor", "routing", _wati_log)],
                }
            else:
                return {
                    "next_agent": "END",
                    "active_agent": "supervisor",
                    "agent_log": [_log("supervisor", "routing", "→ END (validasi: tidak perlu tindakan)")],
                }

        # Priority 4: validasi trigger — setelah data-agent selesai dengan SEGERA items.
        # HARUS ada di early-return block; kode serupa di bawah (line ~522) tidak pernah dicapai
        # karena early-return block selalu return lebih dulu.
        _DATA_AGENTS_EARLY = {"monitor_agent", "diagnose_agent", "security_agent"}
        if (_early_prev in _DATA_AGENTS_EARLY
                and "validasi_agent" in _early_valid
                and not _early_wants_file):
            _segera_txt = _clean(last.content or "")
            if "🚨 **SEGERA**" in _segera_txt:
                _val_log = (
                    f"→ validasi_agent  skills: ['action-validation']  | "
                    f"validasi-trigger: {_early_prev} produced SEGERA items"
                )
                return {
                    "next_agent": "validasi_agent",
                    "active_agent": "supervisor",
                    "injected_skills": ["action-validation"],
                    "original_intent": _early_intent,
                    "agent_log": [_log("supervisor", "routing", _val_log)],
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

    # Fast-path: simple greetings / identity questions → answer directly, no LLM routing needed
    if _is_greeting(messages):
        _supervisor_defn_g = _agent_loader.get("supervisor")
        _chat_prompt_g = (
            _supervisor_defn_g.chat_prompt
            if _supervisor_defn_g and _supervisor_defn_g.chat_prompt
            else (
                "Kamu adalah Bambang, supervisor operasional jaringan kampus universitas. "
                "Balas sapaan atau pertanyaan umum dengan ramah dan singkat dalam Bahasa Indonesia. "
                "Sebutkan bahwa kamu siap membantu kebutuhan operasional jaringan kampus."
            )
        )
        _recent_g = [m for m in messages if isinstance(m, (HumanMessage, AIMessage))][-6:]
        _llm_g = _make_llm(
            temperature=0.5,
            model=_supervisor_defn_g.model if _supervisor_defn_g else None,
            num_ctx=_supervisor_defn_g.num_ctx if _supervisor_defn_g else 8192,
            num_predict=1536,  # short reply expected, but a thinking model needs headroom to reason first
            timeout=_supervisor_defn_g.timeout if _supervisor_defn_g else 60,
            agent_name="supervisor",
            base_url=(_supervisor_defn_g.ollama_host if _supervisor_defn_g else "") or None,
            reasoning=False,
        )
        _greeting_result: dict = {
            "next_agent": "END",
            "active_agent": "supervisor",
            "agent_log": [_log("supervisor", "routing", "→ END (sapaan/pertanyaan umum, jawab langsung)")],
        }
        try:
            _reply_g = _llm_g.invoke([SystemMessage(content=_chat_prompt_g)] + _recent_g)
            if not _visible_content(_reply_g.content or ""):
                raise ValueError(
                    f"empty visible content (finish_reason={_reply_g.response_metadata.get('finish_reason')}, "
                    f"usage={_reply_g.response_metadata.get('token_usage')})"
                )
            _greeting_result["messages"] = [_reply_g]
        except Exception as exc:
            # Jangan biarkan kegagalan LLM di fast-path ini membuat operator
            # menerima balasan kosong — safety net yang sama seperti specialist node.
            logger.warning("Greeting fast-path gagal (supervisor): %s", exc)
            _greeting_result["messages"] = [AIMessage(
                content="Halo! Saya Bambang, supervisor operasional jaringan kampus. "
                        "Ada yang bisa saya bantu terkait jaringan kampus?"
            )]
            _greeting_result["agent_log"].append(
                _log("supervisor", "tool_result", f"(fallback: balasan sapaan gagal — {exc})")
            )
        return _greeting_result

    skill_list = "\n".join(
        f"  {s.name}: {', '.join(s.triggers[:3])}"
        for s in _skill_lib.list_enabled()
    ) or "  (tidak ada skill aktif)"

    from tools.base import get_router_names as _get_router_names  # noqa: PLC0415
    router_list = "  " + ", ".join(_get_router_names()) if _get_router_names() else "  (kosong)"

    # Simpan original_intent dari HumanMessage pertama jika belum ada
    _current_intent = state.get("original_intent", "")
    if not _current_intent:
        _first_human = next((m for m in messages if isinstance(m, HumanMessage)), None)
        _current_intent = (_first_human.content or "").strip() if _first_human else ""

    # Inject intent context ke prompt hanya jika ada dan ada agent yang sudah selesai
    _prev_for_intent = state.get("active_agent", "")
    if _current_intent and _prev_for_intent and _prev_for_intent != "supervisor":
        _intent_ctx = (
            f"\nIntent awal operator: \"{_current_intent}\"\n"
            f"Agent terakhir yang selesai: {_prev_for_intent}\n"
            f"Cek apakah intent ini sudah terpenuhi. Jika belum, route ke agent yang tepat. "
            f"Jika sudah → END."
        )
    else:
        _intent_ctx = ""

    _supervisor_defn = _agent_loader.get("supervisor")
    _supervisor_model = _supervisor_defn.model if _supervisor_defn else None

    sys_msg = SystemMessage(content=_SUPERVISOR_SYS.format(
        supervisor_body=_agent_loader.system_prompt("supervisor"),
        agent_descriptions=agent_descriptions,
        skill_list=skill_list,
        router_list=router_list,
        valid_agents=valid_agents_str,
        intent_context=_intent_ctx,
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
        context_agent = (
            _last_specialist_from_log(state, valid_agent_names)
            if not keyword_agent else None
        )
        fallback = keyword_agent or context_agent or "END"
        route_type = "context" if context_agent and not keyword_agent else "keyword"
        data = {"next_agent": fallback, "relevant_skills": [],
                "reasoning": f"{route_type}-fallback({fallback}): {exc}"}

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

    # NOTE: Validasi trigger dan post-validasi routing di bawah ini adalah SECONDARY FALLBACK
    # untuk kasus supervisor LLM dipanggil ulang setelah user kirim pesan baru (HumanMessage).
    # Kasus primer (agent baru selesai → last == AIMessage) sudah ditangani di early-return
    # block (Priority 3 dan 4) — kode di bawah tidak pernah dicapai untuk kasus itu.
    _DATA_AGENTS = {"monitor_agent", "diagnose_agent", "security_agent"}
    if (next_agent == "END"
            and _prev_agent in _DATA_AGENTS
            and "validasi_agent" in valid_agent_names):
        _last_ai_msg = next((m for m in reversed(messages) if isinstance(m, AIMessage)), None)
        _last_ai_txt = (_last_ai_msg.content or "") if _last_ai_msg else ""
        if "🚨 **SEGERA**" in _last_ai_txt and not _wants_file:
            next_agent = "validasi_agent"
            data["reasoning"] = (
                f"validasi-trigger (llm-path): {_prev_agent} produced SEGERA items → validasi_agent"
            )
            _existing_skills = data.get("relevant_skills") or []
            if "action-validation" not in _existing_skills:
                data["relevant_skills"] = ["action-validation"] + list(_existing_skills)

    if _prev_agent == "validasi_agent":
        _last_ai_msg = next((m for m in reversed(messages) if isinstance(m, AIMessage)), None)
        _wati_txt = (_last_ai_msg.content or "") if _last_ai_msg else ""
        if "delegasikan ke config_agent" in _wati_txt and "config_agent" in valid_agent_names:
            next_agent = "config_agent"
            data["reasoning"] = "validasi-delegation (llm-path): wati delegated to config_agent"
        elif "delegasikan ke diagnose_agent" in _wati_txt and "diagnose_agent" in valid_agent_names:
            next_agent = "diagnose_agent"
            data["reasoning"] = "validasi-delegation (llm-path): wati delegated to diagnose_agent"
        else:
            next_agent = "END"
            data["reasoning"] = "validasi-delegation (llm-path): no action needed → END"

    # Router discovery override: jika ada error "tidak dikenal" dari validate_router(),
    # route ke config_agent/netbox_agent dengan skill router-discovery untuk auto-discover.
    if next_agent == "END":
        _recent_content = " ".join(
            (m.content or "") for m in messages[-6:]
            if hasattr(m, "content") and isinstance(m.content, str)
        )
        _router_error = "tidak dikenal" in _recent_content or "tidak ditemukan" in _recent_content
        _discovery_agent = next(
            (a for a in ("config_agent", "netbox_agent") if a in valid_agent_names),
            None,
        )
        if _router_error and _discovery_agent and _prev_agent != _discovery_agent:
            next_agent = _discovery_agent
            data["reasoning"] = (
                f"router-discovery override: error 'tidak dikenal' → {_discovery_agent}"
            )
            data["relevant_skills"] = ["router-discovery"]

    skills = data.get("relevant_skills", [])
    log_msg = f"→ {next_agent}  skills: {skills}  | {data.get('reasoning','')}"
    base_result = {
        "next_agent": next_agent,
        "active_agent": "supervisor",
        "injected_skills": skills,
        "original_intent": _current_intent,
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
                if not _visible_content(reply.content or ""):
                    raise ValueError(
                        f"empty visible content (finish_reason={reply.response_metadata.get('finish_reason')}, "
                        f"usage={reply.response_metadata.get('token_usage')})"
                    )
                base_result["messages"] = [reply]
            except Exception as exc:
                logger.warning("END fast-path gagal (supervisor): %s", exc)
                base_result["messages"] = [AIMessage(
                    content="Maaf, saya belum bisa menyusun jawaban untuk itu. Bisa dicoba lagi atau "
                            "diperjelas maksudnya?"
                )]
                base_result["agent_log"].append(
                    _log("supervisor", "tool_result", f"(fallback: balasan END gagal — {exc})")
                )

    return base_result


def route_from_supervisor(state: dict) -> str:
    return state.get("next_agent", "END")


# ── Specialist node factory ───────────────────────────────────────────────────

_SPECIALIST_SYS = """\
{agent_body}

Tool yang tersedia (HANYA ini yang boleh dipanggil): {tool_names}

{pedoman}

{skill_context}
"""


def _make_specialist_node(agent_name: str):
    defn = _agent_loader.get(agent_name)
    tools = _resolve_tools(agent_name)
    _tool_names = [t.name for t in tools]
    tool_names_str = ", ".join(_tool_names)
    agent_body = defn.body if defn else ""
    context_window = defn.context_window if defn else 10
    _model = defn.model if defn else None
    _num_ctx = defn.num_ctx if defn else 8192
    _num_predict = defn.num_predict if defn else 2048
    _timeout = defn.timeout if defn else 300
    _ollama_host = defn.ollama_host if defn else ""
    _reasoning = defn.reasoning if defn else False
    _max_iters = defn.max_iters if defn else 20
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

        _pedoman_skill = _skill_lib.get_by_name("pedoman-agent")
        pedoman = _pedoman_skill.body if _pedoman_skill else _PEDOMAN

        sys_content = _SPECIALIST_SYS.format(
            agent_body=agent_body,
            tool_names=tool_names_str,
            pedoman=pedoman,
            skill_context=skill_ctx,
        ).strip()
        sys_msg = SystemMessage(content=sys_content)

        context_msgs = list(state["messages"])[-context_window:]
        _current_tool_map = {n: TOOL_MAP[n] for n in _tool_names if n in TOOL_MAP}
        all_msgs, logs = _react_loop(
            llm_with_tools,
            [sys_msg] + context_msgs,
            _current_tool_map,
            agent_name,
            max_iters=_max_iters,
        )
        _writer = _get_writer()

        def _emit(event_type: str, content: str) -> None:
            entry = _log(agent_name, event_type, content)
            logs.append(entry)
            _writer(entry)

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
                    _emit("tool_result", "(forced summary generated)")
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
            _emit("tool_result", "(safety net: paksa AIMessage dari tool result)")

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

    _pedoman_skill = _skill_lib.get_by_name("pedoman-agent")
    _pedoman = _pedoman_skill.body if _pedoman_skill else _PEDOMAN

    _config_tool_names = ", ".join(t.name for t in _CONFIG_TOOLS)
    sys_msg = SystemMessage(content=_SPECIALIST_SYS.format(
        agent_body=_agent_loader.system_prompt("config_agent"),
        tool_names=_config_tool_names,
        pedoman=_pedoman,
        skill_context=skill_ctx,
    ).strip())

    messages = [sys_msg] + list(state["messages"])[-10:]
    writer = _get_writer()
    logs: list[dict] = []
    _backed_up_routers: set[str] = set()

    def _emit(event_type: str, content: str) -> None:
        entry = _log("config_agent", event_type, content)
        logs.append(entry)
        writer(entry)

    def _auto_backup(router: str) -> bool:
        """Trigger backup approval + execution. Return True if approved and done."""
        approval_req = {
            "agent": "config_agent",
            "action": f"Backup otomatis sebelum write — router '{router}'",
            "risk_level": "medium",
            "details": {"router_name": router},
        }
        _emit("approval_required", f"Backup sebelum write: {router}")
        decision = interrupt(approval_req)
        if decision != "approved":
            _emit("tool_result", f"Backup ditolak — write ke '{router}' dibatalkan.")
            return False
        backup_fn = _CONFIG_TOOLS_MAP.get("backup_router_config")
        if backup_fn:
            try:
                res = backup_fn.invoke({"router_name": router})
                _emit("tool_result", str(res)[:120])
            except Exception as exc:
                _emit("tool_result", f"Backup error: {exc}")
        _backed_up_routers.add(router)
        return True

    for _ in range(12):
        response = _CONFIG_LLM.invoke(messages)
        messages = messages + [response]

        if not getattr(response, "tool_calls", None):
            break

        for tc in response.tool_calls:
            name = tc["name"]
            args = tc.get("args", {})
            args_str = ", ".join(f"{k}={json.dumps(v)}" for k, v in args.items())
            _emit("tool_call", f"{name}({args_str})")

            router = args.get("router_name", "router")

            # Track LLM-initiated backups so auto-backup can skip them
            if name == "backup_router_config" and router:
                _backed_up_routers.add(router)

            # Enforce backup before first write to each router
            if name == "run_command_write" and router and router not in _backed_up_routers:
                if not _auto_backup(router):
                    result = "Write dibatalkan: operator menolak backup."
                    messages.append(ToolMessage(content=result, tool_call_id=tc["id"]))
                    continue

            if name in _APPROVAL_REQUIRED_TOOLS:
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
                _emit("approval_required", f"Menunggu approval: {approval_req['action']}")
                decision = interrupt(approval_req)

                if decision != "approved":
                    result = f"Aksi dibatalkan oleh operator (keputusan: {decision})."
                    _emit("tool_result", result)
                    messages.append(ToolMessage(content=result, tool_call_id=tc["id"]))
                    continue

                _emit("tool_result", f"Operator menyetujui — eksekusi {name}...")

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
            _emit("tool_result", preview)
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

monitor_node   = _make_specialist_node("monitor_agent")
diagnose_node  = _make_specialist_node("diagnose_agent")
security_node  = _make_specialist_node("security_agent")
document_node  = _make_specialist_node("document_agent")
validasi_node  = _make_specialist_node("validasi_agent")
netbox_node   = _make_specialist_node("netbox_agent")
# config_node defined above with interrupt() support
