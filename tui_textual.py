#!/usr/bin/env python3
"""NetOps AI — Textual TUI.

Design: mirrors frontend/index.html NOC console aesthetic.
Run:
    python tui_textual.py
"""
from __future__ import annotations

import os
import subprocess
import tempfile
import time
import uuid
import re
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any

from rich.text import Text
from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, ScrollableContainer, Vertical
from textual.message import Message
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.widget import Widget
from textual.widgets import Button, Input, RichLog, Static

import agent as _agent
from agents.loader import AgentLoader

# ── Constants ────────────────────────────────────────────────────────────────

AGENTS_DEF: list[dict] = [
    {"name": "bambang", "role": "supervisor", "color": "#d2a8ff"},
    {"name": "eko",     "role": "monitor",    "color": "#7ee787"},
    {"name": "agus",    "role": "diagnosa",   "color": "#79c0ff"},
    {"name": "joko",    "role": "config",     "color": "#ffa657"},
    {"name": "satria",  "role": "security",   "color": "#ff7b72"},
    {"name": "budi",    "role": "dokumen",    "color": "#a8c7fa"},
]

ALIAS_MAP: dict[str, str] = {
    "monitor_agent":  "eko",
    "diagnose_agent": "agus",
    "config_agent":   "joko",
    "security_agent": "satria",
    "document_agent": "budi",
    "supervisor":     "bambang",
}

STATE_COLORS: dict[str, str] = {
    "STANDBY":  "#6c7280",
    "ANTREAN":  "#79c0ff",
    "BERJALAN": "#7ee787",
    "MENUNGGU": "#f0b85c",
    "SELESAI":  "#a8aeba",
    "GAGAL":    "#ff7b72",
}

def _build_agent_models() -> dict[str, str]:
    try:
        return {d.alias: d.model for d in AgentLoader().all() if d.alias}
    except Exception:
        return {}

_AGENT_MODELS: dict[str, str] = _build_agent_models()


def _alias(raw: str) -> str:
    m = re.search(r"\[([^\]]+)\]", raw)
    key = m.group(1) if m else raw
    return ALIAS_MAP.get(key, key)


def _now_wib() -> str:
    wib = timezone(timedelta(hours=7))
    return datetime.now(wib).strftime("%H:%M:%S")


# ── CSS ──────────────────────────────────────────────────────────────────────

APP_CSS = """
Screen {
    background: #08090b;
    layers: base modal;
}

/* ── TopBar ── */
TopBar {
    height: 2;
    background: #0e1014;
    border-bottom: tall #252932;
    layout: horizontal;
    align: left middle;
    padding: 0 1;
}
#tb-logo    { color: #e8eaee; width: auto; }
#tb-dot     { color: #7ee787; width: 2; }
#tb-thread  { color: #6c7280; width: auto; }
#tb-spacer  { width: 1fr; }
#tb-sep     { color: #454a55; width: auto; margin: 0 1; }
#tb-model   { color: #e8eaee; width: auto; }
#tb-time    { color: #6c7280; width: auto; margin-left: 2; }

/* ── Main area: takes all remaining height ── */
#main-area  { height: 1fr; }

/* ── ChatPanel ── */
ChatPanel {
    width: 1fr;
    height: 100%;
    background: #08090b;
    layout: vertical;
}
#chat-head {
    height: 2;
    background: #0e1014;
    border-bottom: tall #252932;
    layout: horizontal;
    align: left middle;
    padding: 0 1;
}
#chat-head-title  { color: #a8aeba; width: auto; margin-right: 2; }
#chat-head-status { color: #6c7280; width: 1fr; }
#chat-head-btns   { layout: horizontal; align: right middle; width: auto; height: 1; }

.btn-stop {
    background: #4a1f1f;
    color: #ff7b72;
    border: tall #ff7b72;
    height: 1;
    min-width: 8;
    margin-left: 1;
}
.btn-clear {
    background: #0e1014;
    color: #a8aeba;
    border: tall #363b46;
    height: 1;
    min-width: 7;
    margin-left: 1;
}
.btn-stop:hover  { background: #6b2b2b; }
.btn-clear:hover { background: #15181e; }

#chat-log {
    height: 1fr;
    background: #08090b;
    padding: 1 2;
    border: none;
    scrollbar-color: #252932 #08090b;
}

/* ── Composer ── */
Composer {
    height: 5;
    background: #0e1014;
    border-top: tall #252932;
    layout: horizontal;
    padding: 1 1;
    align: left middle;
}
#comp-prompt { color: #7ee787; width: 2; height: 3; content-align: left top; }
#comp-input  {
    background: #15181e;
    border: tall #252932;
    color: #e8eaee;
    height: 3;
    width: 1fr;
    margin-right: 1;
}
#comp-input:focus { border: tall #363b46; }
#btn-send {
    background: #1c2028;
    color: #e8eaee;
    border: tall #363b46;
    height: 3;
    min-width: 8;
}
#btn-send:hover    { background: #252932; }
#btn-send:disabled { opacity: 0.4; }

/* ── AgentRail ── */
AgentRail {
    width: 24;
    height: 100%;
    background: #08090b;
    border-left: tall #252932;
    layout: vertical;
}
#agent-rail-head {
    height: 2;
    background: #0e1014;
    border-bottom: tall #252932;
    layout: horizontal;
    align: left middle;
    padding: 0 1;
}
#agent-rail-title { color: #a8aeba; width: 1fr; }
#agent-rail-count { color: #6c7280; width: auto; }
#agent-list {
    height: 1fr;
    layout: vertical;
    background: #08090b;
}

/* ── AgentCard ── */
AgentCard {
    background: #0e1014;
    border-bottom: tall #252932;
    height: 4;
    padding: 0 1;
    layout: vertical;
}
AgentCard.active { background: #15181e; }
.a-row  { layout: horizontal; height: 1; align: left middle; }
.a-av   { width: 3; height: 1; content-align: center middle; }
.a-name { color: #e8eaee; width: 1fr; margin-left: 1; }
.a-role { color: #454a55; width: auto; }
.a-chip { color: #6c7280; width: auto; }
.a-ela  { color: #6c7280; width: auto; margin-left: 1; }

/* ── StatusBar ── */
StatusBar {
    height: 2;
    background: #0e1014;
    border-top: tall #252932;
    layout: horizontal;
    align: left middle;
    padding: 0 1;
}
#sb-state { color: #a8aeba; width: 1fr; }
#sb-hint  { color: #454a55; width: auto; }

/* ── ApprovalModal ── */
ApprovalModal { align: center middle; }
#dlg {
    width: 60;
    background: #0e1014;
    border: tall #f0b85c;
    layout: vertical;
    height: auto;
}
#dlg-head {
    background: #2a1f0a;
    border-bottom: tall #f0b85c;
    height: 1;
    padding: 0 1;
    color: #f0b85c;
    content-align: left middle;
}
#dlg-body { padding: 1; layout: vertical; height: auto; }
#dlg-title { color: #e8eaee; height: 1; }
.kv { layout: horizontal; height: 1; }
.kk { color: #6c7280; width: 12; }
.kv-val { color: #e8eaee; width: 1fr; }
#dlg-acts {
    layout: horizontal;
    align: right middle;
    height: 1;
    padding: 0 1;
    margin-top: 1;
    border-top: tall #252932;
}
.btn-reject {
    background: #0e1014;
    color: #a8aeba;
    border: tall #363b46;
    height: 1;
    min-width: 8;
    margin-right: 1;
}
.btn-approve {
    background: #f0b85c;
    color: #08090b;
    border: tall #f0b85c;
    height: 1;
    min-width: 18;
    text-style: bold;
}
.btn-reject:hover  { background: #15181e; }
.btn-approve:hover { background: #f5c87b; }
"""


# ── TopBar ──────────────────────────────────────────────────────────────────

class TopBar(Widget):
    _time: reactive[str] = reactive(_now_wib)
    model_name: reactive[str] = reactive("…")

    def __init__(self) -> None:
        super().__init__()
        self._thread = str(uuid.uuid4())[:8]

    def compose(self) -> ComposeResult:
        logo = Text("[NetOps", style="#e8eaee")
        logo.append("·", style="#7ee787")
        logo.append("AI]", style="#e8eaee")
        yield Static(logo, id="tb-logo")
        yield Static(" ● ", id="tb-dot")
        yield Static(f"thread/{self._thread}", id="tb-thread")
        yield Static("", id="tb-spacer")
        yield Static("·", id="tb-sep")
        yield Static("…", id="tb-model")
        yield Static("", id="tb-time")

    def on_mount(self) -> None:
        self.set_interval(1, self._tick)

    def _tick(self) -> None:
        self._time = _now_wib()

    def watch__time(self, v: str) -> None:
        self._safe_update("#tb-time", v)

    def watch_model_name(self, v: str) -> None:
        self._safe_update("#tb-model", v)

    def _safe_update(self, selector: str, text: str) -> None:
        try:
            self.query_one(selector, Static).update(text)
        except Exception:
            pass


# ── AgentCard ────────────────────────────────────────────────────────────────

@dataclass
class AgentState:
    name: str
    role: str
    color: str
    state: str = "STANDBY"
    task: str = "— idle —"
    elapsed: float = 0.0
    _start: float = field(default_factory=time.monotonic, repr=False)


class AgentCard(Widget):
    def __init__(self, st: AgentState) -> None:
        super().__init__(id=f"card-{st.name}")
        self._st = st

    def compose(self) -> ComposeResult:
        s = self._st
        sc = STATE_COLORS.get(s.state, "#6c7280")
        av = Text(f" {s.name[:2].upper()} ", style=f"bold {s.color}")
        with Horizontal(classes="a-row"):
            yield Static(av, classes="a-av")
            yield Static(s.name, classes="a-name")
            _ROLE_ABBR = {"supervisor": "SUPV", "monitor": "MON", "diagnosa": "DIAG",
                          "config": "CONF", "security": "SEC", "dokumen": "DOC"}
            yield Static(_ROLE_ABBR.get(s.role, s.role.upper()[:4]), classes="a-role")
        with Horizontal(classes="a-row"):
            yield Static(Text(f"● {s.state}", style=sc), classes="a-chip", id=f"chip-{s.name}")
            yield Static("", classes="a-ela", id=f"ela-{s.name}")

    def refresh_state(self, s: AgentState) -> None:
        self._st = s
        sc = STATE_COLORS.get(s.state, "#6c7280")
        is_active = s.state in ("BERJALAN", "MENUNGGU")
        if is_active:
            self.add_class("active")
        else:
            self.remove_class("active")
        self._su(f"#chip-{s.name}", Text(f"● {s.state}", style=sc))
        ela = f"{s.elapsed:.0f}s" if is_active and s.elapsed > 0 else ""
        self._su(f"#ela-{s.name}", ela)

    def _su(self, sel: str, val: Any) -> None:
        try:
            self.query_one(sel, Static).update(val)
        except Exception:
            pass


# ── AgentRail ────────────────────────────────────────────────────────────────

class AgentRail(Widget):
    def __init__(self) -> None:
        super().__init__()
        self._states: dict[str, AgentState] = {
            d["name"]: AgentState(d["name"], d["role"], d["color"])
            for d in AGENTS_DEF
        }
        self._cards: dict[str, AgentCard] = {}

    def compose(self) -> ComposeResult:
        with Horizontal(id="agent-rail-head"):
            yield Static("AGENTS", id="agent-rail-title")
            yield Static("0/6", id="agent-rail-count")
        with ScrollableContainer(id="agent-list"):
            for d in AGENTS_DEF:
                card = AgentCard(self._states[d["name"]])
                self._cards[d["name"]] = card
                yield card

    def set_state(self, name: str, **kwargs: Any) -> None:
        if name not in self._states:
            return
        s = self._states[name]
        for k, v in kwargs.items():
            setattr(s, k, v)
        if kwargs.get("state") == "BERJALAN":
            s._start = time.monotonic()
        if card := self._cards.get(name):
            card.refresh_state(s)
        self._upd_count()

    def reset_all(self) -> None:
        for name, s in self._states.items():
            s.state = "STANDBY"
            s.task = "— idle —"
            s.elapsed = 0.0
            if card := self._cards.get(name):
                card.refresh_state(s)
        self._upd_count()

    def tick_elapsed(self) -> None:
        for name, s in self._states.items():
            if s.state in ("BERJALAN", "MENUNGGU"):
                s.elapsed = time.monotonic() - s._start
                if card := self._cards.get(name):
                    try:
                        card.query_one(f"#ela-{name}", Static).update(f"{s.elapsed:.0f}s")
                    except Exception:
                        pass

    def _upd_count(self) -> None:
        active = sum(1 for s in self._states.values() if s.state in ("BERJALAN", "MENUNGGU"))
        try:
            self.query_one("#agent-rail-count", Static).update(f"{active}/6")
        except Exception:
            pass


# ── Composer ─────────────────────────────────────────────────────────────────

class Composer(Widget):
    class Submit(Message):
        def __init__(self, text: str) -> None:
            super().__init__()
            self.text = text

    def compose(self) -> ComposeResult:
        yield Static(">", id="comp-prompt")
        yield Input(
            placeholder="Tanya bambang… (cek status router, audit firewall, backup config DTI)",
            id="comp-input",
        )
        yield Button("Send", id="btn-send")

    @on(Button.Pressed, "#btn-send")
    def _send_btn(self, _: Button.Pressed) -> None:
        self._submit()

    @on(Input.Submitted, "#comp-input")
    def _send_enter(self, _: Input.Submitted) -> None:
        self._submit()

    def _submit(self) -> None:
        inp = self.query_one("#comp-input", Input)
        text = inp.value.strip()
        if text:
            inp.value = ""
            self.post_message(self.Submit(text))

    def set_disabled(self, v: bool) -> None:
        self.query_one("#comp-input", Input).disabled = v
        self.query_one("#btn-send", Button).disabled = v


# ── ChatPanel ────────────────────────────────────────────────────────────────

class ChatPanel(Widget):
    def __init__(self) -> None:
        super().__init__()
        self._plain_lines: list[str] = []
        self._last_ai: str = ""

    def compose(self) -> ComposeResult:
        with Horizontal(id="chat-head"):
            yield Static("AI Chat", id="chat-head-title")
            yield Static("● siap", id="chat-head-status")
            with Horizontal(id="chat-head-btns"):
                yield Button("■ Stop", classes="btn-stop", id="btn-stop")
                yield Button("Clear", classes="btn-clear", id="btn-clear")
        yield RichLog(id="chat-log", markup=False, wrap=True, auto_scroll=True, highlight=False)
        yield Composer()

    def on_mount(self) -> None:
        self.query_one("#btn-stop", Button).display = False
        msg = "NetOps AI siap. Ketik pertanyaan di bawah."
        self._plain_lines.append(msg)
        self.query_one("#chat-log", RichLog).write(Text(msg, style="#6c7280"))

    @on(Button.Pressed, "#btn-stop")
    def _stop(self, _: Button.Pressed) -> None:
        self.post_message(StopStream())

    def write_user(self, text: str) -> None:
        self._plain_lines.append(f"Anda: {text}")
        t = Text()
        t.append("Anda: ", style="#7ee787 bold")
        t.append(text, style="#e8eaee")
        self._log.write(t)

    def write_event(self, event_type: str, content: str) -> None:
        log = self._log

        if event_type == "routing":
            m = re.search(r"[→>]\s*(\w+)", content)
            raw = m.group(1) if m else content
            target = ALIAS_MAP.get(raw, raw)
            self._plain_lines.append(f"  ↳ [bambang] → {target}")
            t = Text()
            t.append("  ↳ ", style="#454a55")
            t.append(f"[bambang] → ", style="#6c7280")
            t.append(target, style="#e8eaee")
            log.write(t)

        elif event_type == "tool_call":
            agent_name = _alias(content)
            tool = re.sub(r"^\[[^\]]+\]\s*", "", content)
            self._plain_lines.append(f"  ↳ [{agent_name}] {tool}")
            t = Text()
            t.append("  ↳ ", style="#454a55")
            t.append(f"[{agent_name}] ", style="#7ee787")
            t.append(tool, style="#6c7280")
            log.write(t)

        elif event_type == "tool_result":
            agent_name = _alias(content)
            preview = re.sub(r"^\[[^\]]+\]\s*", "", content)[:80]
            self._plain_lines.append(f"  ↳ [{agent_name}] {preview}")
            t = Text()
            t.append("  ↳ ", style="#454a55")
            t.append(f"[{agent_name}]", style="#7ee787")
            t.append(f" {preview}", style="#454a55")
            log.write(t)

        elif event_type == "ai":
            self._last_ai = content or ""
            self._plain_lines.append("─" * 60)
            self._plain_lines.append(f"AI  : {content or ''}")
            self._plain_lines.append("─" * 60)
            log.write(Text("─" * 60, style="#252932"))
            lines = (content or "").split("\n")
            for i, line in enumerate(lines):
                if not line and i > 0:
                    continue
                t = Text()
                t.append("AI  : " if i == 0 else "      ", style="#f0b85c bold" if i == 0 else "")
                t.append(line, style="#e8eaee")
                log.write(t)
            log.write(Text("─" * 60, style="#252932"))

        elif event_type == "approval_required":
            try:
                d = json.loads(content)
            except Exception:
                d = {}
            agent_name = _alias(d.get("agent", "config_agent"))
            action = d.get("action", "?")
            self._plain_lines.append(f"  ⚠ {agent_name} meminta approval · {action}")
            t = Text()
            t.append("  ⚠ ", style="#f0b85c bold")
            t.append(f"{agent_name} meminta approval", style="#f0b85c")
            t.append(f" · {action}", style="#6c7280")
            log.write(t)

        elif event_type == "error":
            self._plain_lines.append(f"  ✗ error: {content}")
            t = Text()
            t.append("  ✗ error: ", style="#ff7b72")
            t.append(content, style="#ff7b72")
            log.write(t)

        elif event_type == "elapsed":
            self._plain_lines.append(f"  ↳ ⏱ {content}")
            log.write(Text(f"  ↳ ⏱ {content}", style="#454a55"))

    def set_streaming(self, streaming: bool, elapsed: float = 0) -> None:
        status = self.query_one("#chat-head-status", Static)
        stop_btn = self.query_one("#btn-stop", Button)
        composer = self.query_one(Composer)
        if streaming:
            status.update(Text(f"⠹ streaming {elapsed:.0f}s", style="#6c7280"))
            stop_btn.display = True
            composer.set_disabled(True)
        else:
            status.update(Text("● siap", style="#6c7280"))
            stop_btn.display = False
            composer.set_disabled(False)

    @property
    def _log(self) -> RichLog:
        return self.query_one("#chat-log", RichLog)


# ── StatusBar ────────────────────────────────────────────────────────────────

class StatusBar(Widget):
    def compose(self) -> ComposeResult:
        yield Static("● ready", id="sb-state")
        yield Static("↵ send  ctrl+y copy-ai  ctrl+b copy-log  ctrl+e less-view  ctrl+c quit", id="sb-hint")

    def update_state(self, text: str, style: str = "#a8aeba") -> None:
        try:
            self.query_one("#sb-state", Static).update(Text(text, style=style))
        except Exception:
            pass


# ── ApprovalModal ────────────────────────────────────────────────────────────

class ApprovalModal(ModalScreen[str]):
    BINDINGS = [
        Binding("y", "approve", "Setuju"),
        Binding("n,escape", "reject", "Tolak"),
    ]

    def __init__(self, data: dict) -> None:
        super().__init__()
        self._data = data

    def compose(self) -> ComposeResult:
        d = self._data
        details = d.get("details", {})
        action = d.get("action", "—")
        router = details.get("router_name") or details.get("name", "—")
        risk = d.get("risk_level", "medium")
        agent_name = _alias(d.get("agent", "config_agent"))
        risk_label = "TINGGI" if risk == "high" else "SEDANG"
        risk_style = "#ff7b72" if risk == "high" else "#f0b85c"

        with Vertical(id="dlg"):
            yield Static(f"⚠  APPROVAL — {agent_name.upper()} / config", id="dlg-head")
            with Vertical(id="dlg-body"):
                title = Text()
                title.append(agent_name, style="bold #ffa657")
                title.append(" → tulis ke router ", style="#e8eaee")
                title.append(router, style="bold #79c0ff")
                yield Static(title, id="dlg-title")
                for lbl, val, sty in [
                    ("AKSI",       action,                              "#e8eaee"),
                    ("TARGET",     router,                              "#e8eaee"),
                    ("RISIKO",     f"{risk_label}",                    risk_style),
                    ("REVERSIBLE", "ya",                               "#7ee787"),
                ]:
                    with Horizontal(classes="kv"):
                        yield Static(lbl, classes="kk")
                        yield Static(Text(val, style=sty), classes="kv-val")
            with Horizontal(id="dlg-acts"):
                yield Button("Tolak", classes="btn-reject", id="btn-reject")
                yield Button("Setuju, jalankan", classes="btn-approve", id="btn-approve")

    @on(Button.Pressed, "#btn-approve")
    def action_approve(self) -> None:
        self.dismiss("approved")

    @on(Button.Pressed, "#btn-reject")
    def action_reject(self) -> None:
        self.dismiss("rejected")


# ── StopStream message ────────────────────────────────────────────────────────

class StopStream(Message):
    pass


# ── Main App ─────────────────────────────────────────────────────────────────

class NetOpsApp(App):
    CSS = APP_CSS
    TITLE = "NetOps AI"
    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit", priority=True),
        Binding("ctrl+y", "copy_last_ai", "Copy AI", show=False),
        Binding("ctrl+b", "copy_full_log", "Copy Log", show=False),
        Binding("ctrl+e", "open_log_modal", "View Log", show=False),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._graph, self._config = _agent.create_agent(thread_id=str(uuid.uuid4()))
        self._current_worker = None
        self._stream_active = False
        self._stream_start = 0.0

    def compose(self) -> ComposeResult:
        yield TopBar()
        with Horizontal(id="main-area"):
            yield ChatPanel()
            yield AgentRail()
        yield StatusBar()

    def on_mount(self) -> None:
        self.set_interval(1, self._tick)
        self._fetch_model()

    def _tick(self) -> None:
        if self._stream_active:
            elapsed = time.monotonic() - self._stream_start
            self.query_one(ChatPanel).set_streaming(True, elapsed)
        self.query_one(AgentRail).tick_elapsed()

    def _fetch_model(self) -> None:
        model = _AGENT_MODELS.get("bambang", "?")
        self.query_one(TopBar).model_name = model

    # ── Copy / View actions ───────────────────────────────────────────────

    def _sys_copy(self, text: str) -> bool:
        """Copy via xsel/wl-copy; return True on success."""
        for cmd in (["xsel", "--clipboard", "--input"], ["wl-copy"], ["xclip", "-selection", "clipboard"]):
            try:
                r = subprocess.run(cmd, input=text.encode(), timeout=3, capture_output=True)
                if r.returncode == 0:
                    return True
            except (FileNotFoundError, subprocess.TimeoutExpired):
                continue
        return False

    def action_copy_last_ai(self) -> None:
        chat = self.query_one(ChatPanel)
        if not chat._last_ai:
            self.notify("Belum ada response AI", severity="warning")
            return
        if not self._sys_copy(chat._last_ai):
            self.copy_to_clipboard(chat._last_ai)
        self.notify("✓ AI response di-copy ke clipboard")

    def action_copy_full_log(self) -> None:
        chat = self.query_one(ChatPanel)
        if not chat._plain_lines:
            self.notify("Log kosong", severity="warning")
            return
        text = "\n".join(chat._plain_lines)
        if not self._sys_copy(text):
            self.copy_to_clipboard(text)
        self.notify(f"✓ {len(chat._plain_lines)} baris di-copy ke clipboard")

    async def action_open_log_modal(self) -> None:
        chat = self.query_one(ChatPanel)
        content = "\n".join(chat._plain_lines) if chat._plain_lines else "(log kosong)"
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".log", prefix="netops_", delete=False
        ) as f:
            f.write(content)
            tmpfile = f.name
        try:
            async with self.suspend():
                subprocess.run(["less", "-R", "--quit-if-one-screen", tmpfile])
        finally:
            try:
                os.unlink(tmpfile)
            except OSError:
                pass

    # ── Send / Stream ─────────────────────────────────────────────────────

    @on(Composer.Submit)
    def _on_send(self, event: Composer.Submit) -> None:
        if self._stream_active:
            return
        rail = self.query_one(AgentRail)
        rail.reset_all()
        rail.set_state("bambang", state="BERJALAN", task="⠹ routing…")
        self.query_one(ChatPanel).write_user(event.text)
        self._stream_active = True
        self._stream_start = time.monotonic()
        self._current_worker = self._run_stream(event.text)

    @work(thread=True, exclusive=True)
    def _run_stream(self, text: str) -> None:
        t0 = time.monotonic()
        try:
            for etype, content in _agent.stream_agent_response(self._graph, self._config, text):
                self.call_from_thread(self._on_event, etype, content)
                if etype == "approval_required":
                    return
            self.call_from_thread(self._on_done, time.monotonic() - t0, False)
        except Exception as exc:
            self.call_from_thread(self._on_event, "error", str(exc))
            self.call_from_thread(self._on_done, time.monotonic() - t0, False)

    @on(StopStream)
    def _on_stop(self, _: StopStream) -> None:
        if self._current_worker:
            self._current_worker.cancel()
        self._on_done(time.monotonic() - self._stream_start, True)

    @on(Button.Pressed, "#btn-clear")
    def _on_clear_btn(self, _: Button.Pressed) -> None:
        if self._stream_active:
            return
        chat = self.query_one(ChatPanel)
        chat._plain_lines.clear()
        chat._last_ai = ""
        self.query_one("#chat-log", RichLog).clear()
        self.query_one(AgentRail).reset_all()
        self._graph, self._config = _agent.create_agent(thread_id=str(uuid.uuid4()))

    # ── Resume after approval ─────────────────────────────────────────────

    @work(thread=True)
    def _run_resume(self, decision: str) -> None:
        t0 = time.monotonic()
        try:
            for etype, content in _agent.resume_after_approval(self._graph, self._config, decision):
                self.call_from_thread(self._on_event, etype, content)
                if etype == "approval_required":
                    return
            self.call_from_thread(self._on_done, time.monotonic() - t0, False)
        except Exception as exc:
            self.call_from_thread(self._on_event, "error", str(exc))
            self.call_from_thread(self._on_done, time.monotonic() - t0, False)

    # ── Event dispatch ────────────────────────────────────────────────────

    def _on_event(self, etype: str, content: str) -> None:
        chat = self.query_one(ChatPanel)
        rail = self.query_one(AgentRail)
        chat.write_event(etype, content)

        if etype == "routing":
            rail.set_state("bambang", state="SELESAI", task="✓ routed")
            m = re.search(r"[→>]\s*(\w+)", content)
            if m:
                target = ALIAS_MAP.get(m.group(1), m.group(1))
                if target and target != "END":
                    rail.set_state(target, state="BERJALAN", task="⠹ berjalan…")
                    if model := _AGENT_MODELS.get(target):
                        self.query_one(TopBar).model_name = model

        elif etype == "tool_call":
            agent_name = _alias(content)
            tool = re.sub(r"^\[[^\]]+\]\s*", "", content)
            rail.set_state(agent_name, state="BERJALAN", task=f"⠹ {tool}")

        elif etype == "tool_result":
            agent_name = _alias(content)
            preview = re.sub(r"^\[[^\]]+\]\s*", "", content)[:28]
            rail.set_state(agent_name, task=f"✓ {preview}")

        elif etype == "ai":
            for name, s in rail._states.items():
                if s.state == "BERJALAN":
                    rail.set_state(name, state="SELESAI", task="✓ selesai")

        elif etype == "approval_required":
            try:
                d = json.loads(content)
            except Exception:
                d = {}
            agent_name = _alias(d.get("agent", "config_agent"))
            rail.set_state(agent_name, state="MENUNGGU", task=f"⊙ {d.get('action','approval')}")
            self.call_later(self._show_modal, d)

        elif etype == "error":
            for name, s in rail._states.items():
                if s.state == "BERJALAN":
                    rail.set_state(name, state="GAGAL", task="✗ error")

        self.query_one(StatusBar).update_state(
            "⊙ APPROVAL PENDING" if etype == "approval_required"
            else f"⠹ streaming…",
            "#f0b85c" if etype == "approval_required" else "#6c7280",
        )

    def _on_done(self, elapsed: float, cancelled: bool) -> None:
        self._stream_active = False
        chat = self.query_one(ChatPanel)
        rail = self.query_one(AgentRail)
        verb = "dibatalkan" if cancelled else "selesai"
        chat.write_event("elapsed", f"{verb} dalam {elapsed:.1f}s")
        chat.set_streaming(False)
        self.query_one(StatusBar).update_state("● ready", "#a8aeba")
        for name, s in rail._states.items():
            if s.state == "BERJALAN":
                rail.set_state(name, state="SELESAI", task="✓ selesai")

    def _show_modal(self, data: dict) -> None:
        def _cb(decision: str | None) -> None:
            d = decision or "rejected"
            agent_name = _alias(data.get("agent", "config_agent"))
            rail = self.query_one(AgentRail)
            if d == "approved":
                rail.set_state(agent_name, state="BERJALAN", task="⠹ executing…")
                self.query_one(StatusBar).update_state("⠹ streaming…", "#6c7280")
            else:
                rail.set_state(agent_name, state="GAGAL", task="✗ ditolak")
                self.query_one(StatusBar).update_state("● ready", "#a8aeba")
            self._run_resume(d)

        self.push_screen(ApprovalModal(data), _cb)


# ── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    NetOpsApp().run()
