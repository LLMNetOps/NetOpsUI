#!/usr/bin/env python3
"""Campus Network Operations Platform TUI."""

from __future__ import annotations

import curses
import datetime as dt
import os
import re
import subprocess
import threading
import time
from pathlib import Path
from typing import Any


WORKDIR = Path(__file__).parent
LAPORAN_DIR = WORKDIR / "laporan"
BACKUPS_DIR = WORKDIR / "backups"
CONFIG_FILE = WORKDIR / "config.yaml"
LOG_FILE = WORKDIR / "schedule.log"
MENU_WIDTH = 18
REFRESH_INTERVAL = 5
MIN_ROWS, MIN_COLS = 24, 60
TITLE = "NetOps AI — Campus Network Operations"


def _load_dotenv() -> None:
    """Load .env file into os.environ if present (tanpa dependency python-dotenv)."""
    env_file = WORKDIR / ".env"
    if not env_file.exists():
        return
    with open(env_file, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip()
            if key and key not in os.environ:  # jangan override env var yang sudah ada
                os.environ[key] = val


_load_dotenv()

C_HEADER = 1
C_MENU = 2
C_MENU_SEL = 3
C_OK = 4
C_ERR = 5
C_WARN = 6
C_TITLE = 7
C_DIM = 8

SPINNER = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"

MENU = [
    ("1", "Dashboard"),
    ("2", "Skills"),
    ("3", "Reachability"),
    ("4", "Laporan"),
    ("5", "Log"),
    ("6", "AI Chat"),
    ("7", "Aktivitas Agent"),
    ("8", "Status Agent"),
    ("9", "Token Metrics"),
]

# ── Agent module ─────────────────────────────────────────────────────────────
_HAS_AGENT = False
_agent_mod = None
try:
    import agent as _agent_mod
    _HAS_AGENT = True
except Exception:
    pass

# Shared activity log: written by AIScreen, read by AgentActivityScreen + KanbanScreen
_agent_activity_log: list[dict] = []

# ── Kanban state ──────────────────────────────────────────────────────────────

AGENT_INFO: dict[str, str] = {
    "bambang": "supervisor",
    "eko":     "monitor",
    "agus":    "diagnosa",
    "joko":    "config",
    "satria":  "security",
    "budi":    "dokumen",
}

_ROLE_TO_ALIAS: dict[str, str] = {
    "monitor_agent":  "eko",
    "diagnose_agent": "agus",
    "config_agent":   "joko",
    "security_agent": "satria",
    "document_agent": "budi",
    "supervisor":     "bambang",
}

KANBAN_COLS: list[tuple[str, str]] = [
    ("standby",  "STANDBY"),
    ("antrean",  "ANTREAN"),
    ("berjalan", "BERJALAN"),
    ("menunggu", "MENUNGGU"),
    ("selesai",  "SELESAI"),
    ("gagal",    "GAGAL"),
]

_KANBAN_COL_COLOR: dict[str, int] = {
    "standby":  C_DIM,
    "antrean":  C_WARN,
    "berjalan": C_OK,
    "menunggu": C_WARN,
    "selesai":  C_TITLE,
    "gagal":    C_ERR,
}

_kanban_lock = threading.Lock()


def _kanban_blank() -> dict:
    return {"col": "standby", "col_since": time.time(), "tool_count": 0, "last_tool": ""}


def _set_col(agents: dict, alias: str, col: str) -> None:
    """Set agent column and record transition timestamp."""
    agents[alias]["col"] = col
    agents[alias]["col_since"] = time.time()


_kanban_state: dict = {
    "query":       "",
    "query_start": time.time(),
    "agents":      {alias: _kanban_blank() for alias in AGENT_INFO},
}


def _kanban_reset(query: str) -> None:
    with _kanban_lock:
        now = time.time()
        _kanban_state["query"] = query[:60]
        _kanban_state["query_start"] = now
        _kanban_state["agents"] = {alias: _kanban_blank() for alias in AGENT_INFO}
        _kanban_state["agents"]["bambang"]["col"] = "berjalan"
        _kanban_state["agents"]["bambang"]["col_since"] = now


def _kanban_update(event_type: str, content: str) -> None:
    m = re.match(r'^\[(\w+)\]\s*(.*)', content, re.DOTALL)
    if not m:
        # approval_required content is JSON — map config_agent → joko
        if event_type == "approval_required":
            with _kanban_lock:
                _set_col(_kanban_state["agents"], "joko", "menunggu")
        return

    alias, msg = m.group(1).strip(), m.group(2).strip()

    with _kanban_lock:
        agents = _kanban_state["agents"]
        if alias not in agents:
            return

        if event_type == "routing":
            if msg.startswith("→"):
                target_role = msg.lstrip("→").strip().split()[0]
                if target_role == "END" or "END" in target_role:
                    _set_col(agents, "bambang", "selesai")
                else:
                    _set_col(agents, "bambang", "selesai")
                    target = _ROLE_TO_ALIAS.get(target_role, "")
                    if target:
                        _set_col(agents, target, "berjalan")
            elif "←" in msg:
                _set_col(agents, alias, "selesai")

        elif event_type == "tool_call":
            agents[alias]["col"] = "berjalan"
            agents[alias]["tool_count"] += 1
            agents[alias]["last_tool"] = re.split(r'[\s(]', msg)[0] if msg else ""

        elif event_type == "error":
            _set_col(agents, alias, "gagal")

_HAS_COLORS = False


def cp(pair_id: int) -> int:
    """Return curses color pair attr or normal attr when colors are unavailable."""
    return curses.color_pair(pair_id) if _HAS_COLORS else curses.A_NORMAL


def safe_addstr(win: Any, row: int, col: int, text: str, attr: int = 0) -> None:
    """Write text safely and ignore curses boundary errors."""
    try:
        if attr:
            win.attron(attr)
        win.addstr(row, col, text)
        if attr:
            win.attroff(attr)
    except curses.error:
        pass


def run_cmd(args: list[str], cwd: Path | None = None, timeout: int = 10) -> str:
    """Run command and return combined stdout+stderr, or empty string on error."""
    try:
        res = subprocess.run(
            args,
            cwd=str(cwd) if cwd else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=timeout,
            check=False,
        )
        return res.stdout or ""
    except Exception:
        return ""


def tail_file(path: Path, n: int = 30) -> list[str]:
    """Return the last n lines from a file, or empty list when missing."""
    try:
        with path.open("r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        return [line.rstrip("\n") for line in lines[-n:]]
    except OSError:
        return []


def strip_markdown(text: str) -> str:
    """Remove common markdown syntax for clean terminal display."""
    import re as _re

    # Bold/italic: **text** -> text, *text* -> text, __text__ -> text
    text = _re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = _re.sub(r"__(.+?)__", r"\1", text)
    text = _re.sub(r"\*(.+?)\*", r"\1", text)
    text = _re.sub(r"_(.+?)_", r"\1", text)
    # Headers: ## Title -> Title (keep text, remove #)
    text = _re.sub(r"^#{1,6}\s+", "", text, flags=_re.MULTILINE)
    # Inline code: `code` -> code (keep text, remove backticks)
    # But we KEEP backticks since the system prompt instructs AI to use them for technical terms
    # text = _re.sub(r'`(.+?)`', r'\1', text)  # commented out intentionally
    # Horizontal rules: --- or === alone on line -> empty line
    text = _re.sub(r"^[-=]{3,}\s*$", "", text, flags=_re.MULTILINE)
    # Bullet/list markers: "* item" or "- item" or "1. item" -> "• item"
    text = _re.sub(r"^\s*[\*\-]\s+", "• ", text, flags=_re.MULTILINE)
    text = _re.sub(r"^\s*\d+\.\s+", "  ", text, flags=_re.MULTILINE)
    # Blockquote: > text -> text
    text = _re.sub(r"^\s*>\s*", "", text, flags=_re.MULTILINE)
    # Clean up excessive blank lines (more than 2 -> 1)
    text = _re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


class Screen:
    """Base screen for refresh/draw/key handling."""

    def __init__(self) -> None:
        self.data: dict[str, Any] = {}
        self._lock = threading.Lock()

    def refresh(self) -> None:
        """Gather fresh data for the screen."""

    def handle_key(self, key: int, app: "App") -> bool:
        """Handle key. Return True when consumed."""
        return False

    def draw(self, win: Any, rows: int, cols: int) -> None:
        """Draw screen content into window."""


class DashboardScreen(Screen):
    """System overview: agent status, routers, laporan, skills."""

    def refresh(self) -> None:
        # Agent status
        agent_status: dict = {}
        if _HAS_AGENT and _agent_mod is not None:
            try:
                agent_status = _agent_mod.get_agent_status()
            except Exception:
                pass

        # Routers dari config.yaml
        routers: list[str] = []
        if CONFIG_FILE.exists():
            try:
                import yaml as _yaml
                cfg = _yaml.safe_load(CONFIG_FILE.read_text())
                routers = [r.get("name", "?") for r in cfg.get("routers", [])]
            except Exception:
                pass

        # Laporan files
        laporan = sorted(
            LAPORAN_DIR.glob("*.md"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        ) if LAPORAN_DIR.exists() else []

        # Backups
        backup_count = len(list(BACKUPS_DIR.rglob("*.rsc"))) if BACKUPS_DIR.exists() else 0

        with self._lock:
            self.data["agent_status"] = agent_status
            self.data["routers"] = routers
            self.data["laporan"] = [p.name for p in laporan]
            self.data["laporan_count"] = len(laporan)
            self.data["backup_count"] = backup_count
            self.data["config_ok"] = CONFIG_FILE.exists()

    def draw(self, win: Any, rows: int, cols: int) -> None:
        with self._lock:
            data = dict(self.data)

        safe_addstr(win, 0, 1, "Dashboard — NetOps AI", cp(C_TITLE) | curses.A_BOLD)
        safe_addstr(win, 1, 1, "─" * max(1, cols - 2), cp(C_DIM))

        row = 2

        # ── Agent ──
        safe_addstr(win, row, 2, "Agent", cp(C_TITLE) | curses.A_BOLD)
        row += 1
        status = data.get("agent_status", {})
        if status:
            model   = status.get("model", "?")
            skills  = status.get("skills_loaded", 0)
            url     = status.get("ollama_url", "?")
            safe_addstr(win, row,     2, f"  Model   : {model}", cp(C_OK))
            safe_addstr(win, row + 1, 2, f"  Skills  : {skills} loaded", cp(C_OK))
            safe_addstr(win, row + 2, 2, f"  Ollama  : {url}", cp(C_DIM))
            row += 3
        else:
            safe_addstr(win, row, 2, "  Agent tidak tersedia", cp(C_ERR))
            row += 1

        row += 1
        safe_addstr(win, row, 2, "─" * max(1, cols - 4), cp(C_DIM))
        row += 1

        # ── Config & Routers ──
        safe_addstr(win, row, 2, "Konfigurasi", cp(C_TITLE) | curses.A_BOLD)
        row += 1
        config_ok = data.get("config_ok", False)
        cfg_label = "✓ config.yaml" if config_ok else "✗ config.yaml tidak ditemukan"
        cfg_color = C_OK if config_ok else C_ERR
        safe_addstr(win, row, 2, f"  {cfg_label}", cp(cfg_color))
        row += 1

        routers = data.get("routers", [])
        if routers:
            safe_addstr(win, row, 2, f"  Routers  : {', '.join(routers)}", cp(C_DIM))
        else:
            safe_addstr(win, row, 2, "  Routers  : (belum dikonfigurasi)", cp(C_WARN))
        row += 2

        safe_addstr(win, row, 2, "─" * max(1, cols - 4), cp(C_DIM))
        row += 1

        # ── Laporan ──
        safe_addstr(win, row, 2, "Laporan", cp(C_TITLE) | curses.A_BOLD)
        row += 1
        lcount   = data.get("laporan_count", 0)
        bcount   = data.get("backup_count", 0)
        safe_addstr(win, row,     2, f"  .md files : {lcount}", cp(C_DIM))
        safe_addstr(win, row + 1, 2, f"  Backups   : {bcount} .rsc", cp(C_DIM))
        row += 2

        laporan = data.get("laporan", [])[:min(5, rows - row - 2)]
        if laporan:
            safe_addstr(win, row, 2, "  Terbaru:", cp(C_DIM))
            row += 1
            for name in laporan:
                if row >= rows - 1:
                    break
                maxw = max(4, cols - 7)
                show = name if len(name) <= maxw else name[: maxw - 3] + "..."
                safe_addstr(win, row, 4, show, cp(C_DIM))
                row += 1

        safe_addstr(win, rows - 1, 2, "[R] Refresh", cp(C_MENU))


class SkillsScreen(Screen):
    """Daftar semua skill yang loaded — domain, trigger, tools."""

    def __init__(self) -> None:
        super().__init__()
        self.scroll = 0

    def refresh(self) -> None:
        skills: list[dict] = []
        if _HAS_AGENT and _agent_mod is not None:
            try:
                skills = _agent_mod.get_available_skills()
            except Exception:
                pass
        with self._lock:
            self.data["skills"] = skills

    def handle_key(self, key: int, app: "App") -> bool:
        ch = chr(key) if 0 < key < 256 else ""
        with self._lock:
            n = len(self.data.get("skills", []))

        if key in (curses.KEY_UP, ord("k"), ord("K")):
            self.scroll = max(0, self.scroll - 1)
            return True
        if key in (curses.KEY_DOWN, ord("j"), ord("J")):
            self.scroll = min(max(0, n - 1), self.scroll + 1)
            return True
        if ch in ("r", "R"):
            self.refresh()
            app._wake.set()
            return True
        return False

    def draw(self, win: Any, rows: int, cols: int) -> None:
        with self._lock:
            skills = list(self.data.get("skills", []))

        enabled  = sum(1 for s in skills if s.get("enabled"))
        safe_addstr(win, 0, 1,
                    f"Skills  ({enabled} aktif / {len(skills)} total)",
                    cp(C_TITLE) | curses.A_BOLD)
        safe_addstr(win, 1, 1, "─" * max(1, cols - 2), cp(C_DIM))

        if not skills:
            safe_addstr(win, 3, 2, "Belum ada skill — pastikan agent tersedia.", cp(C_WARN))
            safe_addstr(win, rows - 1, 2, "[R] Refresh", cp(C_MENU))
            return

        card_h   = 3
        content_rows = max(1, rows - 4)
        max_scroll   = max(0, len(skills) - content_rows // card_h)
        self.scroll  = min(self.scroll, max_scroll)
        start = self.scroll
        row = 2
        for skill in skills[start:]:
            if row + card_h > rows - 2:
                break
            enabled = skill.get("enabled", True)
            color   = C_OK if enabled else C_DIM
            name    = skill.get("name", "?")
            domain  = skill.get("domain", "?")
            tools   = skill.get("tools", [])
            triggers = skill.get("triggers", [])
            trigger_str = ", ".join(triggers[:3])
            if len(triggers) > 3:
                trigger_str += f" +{len(triggers)-3}"
            status = "✓" if enabled else "✗"
            safe_addstr(win, row,     2,
                        f"{status} {name}  [{domain}]  tools: {len(tools)}"[: cols - 3],
                        cp(color) | curses.A_BOLD)
            safe_addstr(win, row + 1, 4,
                        f"triggers: {trigger_str}"[: cols - 5],
                        cp(C_DIM))
            safe_addstr(win, row + 2, 2, "·" * max(1, cols - 4), cp(C_DIM))
            row += card_h

        safe_addstr(win, rows - 1, 2, "[J/K] Scroll  [R] Refresh", cp(C_MENU))


_PING_SCRIPT = r"""\
import sys, re, subprocess, yaml
from pathlib import Path
cfg_file = Path(sys.argv[1])
if not cfg_file.exists():
    print("config.yaml tidak ditemukan.")
    sys.exit(1)
cfg = yaml.safe_load(cfg_file.read_text())
routers = cfg.get("routers", [])
if not routers:
    print("Tidak ada router di config.yaml.")
    sys.exit(0)
print(f"Ping {len(routers)} router...")
print()
for r in routers:
    name = r.get("name", "?")
    host = r.get("host", "")
    if not host:
        print(f"  {name:<14} (no host)")
        continue
    try:
        res = subprocess.run(
            ["ping", "-c", "2", "-W", "3", host],
            capture_output=True, text=True, timeout=8,
        )
        ok  = res.returncode == 0
        rtt = "-"
        m   = re.search(r"rtt.*?= [\d.]+/([\d.]+)", res.stdout)
        if m: rtt = f"{m.group(1)}ms avg"
        status = "✓ UP  " if ok else "✗ DOWN"
        print(f"  {name:<14} {host:<18} {status}  {rtt}")
    except Exception as e:
        print(f"  {name:<14} {host:<18} ✗ error: {e}")
print()
print("Selesai.")
"""


class ReachabilityScreen(Screen):
    """Ping check semua router di config.yaml."""

    def __init__(self) -> None:
        super().__init__()
        with self._lock:
            self.data["state"] = "IDLE"
            self.data["lines"] = []
            self.data["proc"] = None
            self.data["start"] = None
            self.data["elapsed"] = 0.0
            self.data["exit_code"] = None

    def refresh(self) -> None:
        with self._lock:
            proc  = self.data.get("proc")
            start = self.data.get("start")
            state = self.data.get("state", "IDLE")
            if state == "RUNNING" and proc is not None:
                if proc.poll() is None and start is not None:
                    self.data["elapsed"] = time.time() - float(start)

    def _start_ping(self, app: "App") -> None:
        with self._lock:
            proc = self.data.get("proc")
            if proc is not None and proc.poll() is None:
                return
            self.data["state"] = "RUNNING"
            self.data["lines"] = []
            self.data["start"] = time.time()
            self.data["elapsed"] = 0.0
            self.data["exit_code"] = None

        try:
            proc = subprocess.Popen(
                ["python3", "-c", _PING_SCRIPT, str(CONFIG_FILE)],
                cwd=str(WORKDIR),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
        except Exception as exc:
            with self._lock:
                self.data["state"] = "FAILED"
                self.data["lines"] = [f"Gagal: {exc}"]
                self.data["exit_code"] = -1
            app._wake.set()
            return

        with self._lock:
            self.data["proc"] = proc

        def reader() -> None:
            try:
                if proc.stdout is not None:
                    for line in proc.stdout:
                        with self._lock:
                            lines = list(self.data.get("lines", []))
                            lines.append(line.rstrip())
                            self.data["lines"] = lines[-40:]
                            start = self.data.get("start")
                            if start is not None:
                                self.data["elapsed"] = time.time() - float(start)
                        app._wake.set()
                proc.wait()
                with self._lock:
                    start = self.data.get("start")
                    if start is not None:
                        self.data["elapsed"] = time.time() - float(start)
                    self.data["exit_code"] = proc.returncode
                    self.data["state"] = "DONE" if proc.returncode == 0 else "FAILED"
            except Exception as exc:
                with self._lock:
                    self.data["state"] = "FAILED"
                    lines = list(self.data.get("lines", []))
                    lines.append(f"Error: {exc}")
                    self.data["lines"] = lines[-40:]
                    self.data["exit_code"] = -1
            finally:
                app._wake.set()

        threading.Thread(target=reader, daemon=True).start()

    def handle_key(self, key: int, app: "App") -> bool:
        ch = chr(key) if 0 < key < 256 else ""
        if ch in ("r", "R"):
            with self._lock:
                state = self.data.get("state", "IDLE")
            if state != "RUNNING":
                self._start_ping(app)
            return True
        return False

    def draw(self, win: Any, rows: int, cols: int) -> None:
        with self._lock:
            state    = self.data.get("state", "IDLE")
            lines    = list(self.data.get("lines", []))
            elapsed  = float(self.data.get("elapsed", 0.0))
            exit_code = self.data.get("exit_code")

        safe_addstr(win, 0, 1, "Reachability — Ping Semua Router", cp(C_TITLE) | curses.A_BOLD)
        safe_addstr(win, 1, 1, "─" * max(1, cols - 2), cp(C_DIM))

        if state == "IDLE":
            safe_addstr(win, 3, 2, "Ping semua router dari config.yaml.", cp(C_DIM))
            safe_addstr(win, 4, 2, "Menampilkan status UP/DOWN dan RTT.", cp(C_DIM))
            safe_addstr(win, 6, 2, "[R] Mulai ping check", cp(C_MENU) | curses.A_BOLD)
            return

        if state == "RUNNING":
            spin = SPINNER[int(time.time() * 8) % len(SPINNER)]
            safe_addstr(win, 3, 2, f"{spin} Pinging...  {elapsed:.0f}s",
                        cp(C_WARN) | curses.A_BOLD)
            view = lines[-(rows - 6):]
            for idx, line in enumerate(view):
                safe_addstr(win, 5 + idx, 2, line[: cols - 3])
            return

        hdr_color = C_OK if state == "DONE" else C_ERR
        hdr = "✓ Selesai" if state == "DONE" else f"✗ Gagal (exit {exit_code})"
        safe_addstr(win, 3, 2, f"{hdr}  ({elapsed:.0f}s)", cp(hdr_color) | curses.A_BOLD)
        view = lines[-(rows - 6):]
        for idx, line in enumerate(view):
            color = C_OK if "✓" in line else C_ERR if "✗" in line else 0
            safe_addstr(win, 5 + idx, 2, line[: cols - 3], cp(color) if color else 0)
        safe_addstr(win, rows - 1, 2, "[R] Ulangi", cp(C_MENU))


class LaporanScreen(Screen):
    """Daftar file laporan di laporan/ — dibuat oleh document_agent via AI Chat."""

    def __init__(self) -> None:
        super().__init__()
        self.scroll = 0
        with self._lock:
            self.data["files"] = []

    def refresh(self) -> None:
        files = sorted(
            LAPORAN_DIR.glob("*.md"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        ) if LAPORAN_DIR.exists() else []
        with self._lock:
            self.data["files"] = files

    def handle_key(self, key: int, app: "App") -> bool:
        ch = chr(key) if 0 < key < 256 else ""
        with self._lock:
            n = len(self.data.get("files", []))

        if key in (curses.KEY_UP, ord("k"), ord("K")):
            self.scroll = max(0, self.scroll - 1)
            return True
        if key in (curses.KEY_DOWN, ord("j"), ord("J")):
            self.scroll = min(max(0, n - 1), self.scroll + 1)
            return True
        if ch in ("r", "R"):
            self.refresh()
            app._wake.set()
            return True
        return False

    def draw(self, win: Any, rows: int, cols: int) -> None:
        with self._lock:
            files = list(self.data.get("files", []))

        safe_addstr(win, 0, 1, f"Laporan  ({len(files)} file)", cp(C_TITLE) | curses.A_BOLD)
        safe_addstr(win, 1, 1, "─" * max(1, cols - 2), cp(C_DIM))

        if not files:
            safe_addstr(win, 3, 2, "Belum ada laporan.", cp(C_DIM))
            safe_addstr(win, 4, 2, "Gunakan [6] AI Chat untuk meminta document_agent", cp(C_DIM))
            safe_addstr(win, 5, 2, "membuat dan menyimpan laporan.", cp(C_DIM))
            safe_addstr(win, rows - 1, 2, "[R] Refresh", cp(C_MENU))
            return

        visible = max(1, rows - 4)
        max_scroll = max(0, len(files) - visible)
        self.scroll = min(self.scroll, max_scroll)
        view = files[self.scroll: self.scroll + visible]

        name_w = max(8, cols - 22)
        for idx, p in enumerate(view):
            ts   = dt.datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
            name = p.name if len(p.name) <= name_w else p.name[: name_w - 3] + "..."
            size = f"{p.stat().st_size / 1024:.0f}K"
            line = f"{name:<{name_w}}  {ts}  {size:>5}"
            safe_addstr(win, 2 + idx, 2, line[: cols - 3])

        safe_addstr(win, rows - 1, 2, "[J/K] Scroll  [R] Refresh  (laporan dibuat via AI Chat)", cp(C_MENU))


class LogScreen(Screen):
    """Tail schedule.log with scroll support."""

    def __init__(self) -> None:
        super().__init__()
        self.scroll = 0

    def refresh(self) -> None:
        lines = tail_file(LOG_FILE, 50)
        with self._lock:
            self.data["lines"] = lines
            max_scroll = max(0, len(lines) - 1)
            self.scroll = min(self.scroll, max_scroll)

    def handle_key(self, key: int, app: "App") -> bool:
        with self._lock:
            lines = list(self.data.get("lines", []))
            max_scroll = max(0, len(lines) - 1)

        if key in (curses.KEY_UP, ord("k"), ord("K")):
            with self._lock:
                self.scroll = max(0, self.scroll - 1)
            return True

        if key in (curses.KEY_DOWN, ord("j"), ord("J")):
            with self._lock:
                self.scroll = min(max_scroll, self.scroll + 1)
            return True

        ch = chr(key) if 0 < key < 256 else ""
        if ch in ("r", "R"):
            self.refresh()
            app._wake.set()
            return True

        return False

    def draw(self, win: Any, rows: int, cols: int) -> None:
        with self._lock:
            lines = list(self.data.get("lines", []))
            scroll = self.scroll

        safe_addstr(
            win,
            0,
            1,
            f"Log  ({len(lines)} baris, scroll ↑↓)",
            cp(C_TITLE) | curses.A_BOLD,
        )
        safe_addstr(win, 1, 1, "─" * max(1, cols - 2), cp(C_DIM))

        visible_rows = max(0, rows - 4)
        if not lines:
            safe_addstr(win, 3, 2, "schedule.log belum ada.", cp(C_DIM))
        else:
            start = min(scroll, max(0, len(lines) - visible_rows))
            view = lines[start : start + visible_rows]
            for idx, line in enumerate(view):
                safe_addstr(win, 2 + idx, 2, line[: cols - 3])

        safe_addstr(win, rows - 1, 2, "[R] Refresh  [J/K] Scroll", cp(C_MENU))


class AgentActivityScreen(Screen):
    """Real-time agent routing and tool activity monitor."""

    _EVENT_ICONS = {
        "routing":          ("→", C_WARN),
        "tool_call":        ("⚙", C_OK),
        "tool_result":      ("✓", C_DIM),
        "approval_required":("⚠", C_ERR),
        "error":            ("✗", C_ERR),
    }

    def handle_key(self, key: int, app: "App") -> bool:
        ch = chr(key) if 0 < key < 256 else ""
        if ch in ("c", "C"):
            _agent_activity_log.clear()
            return True
        return False

    def draw(self, win: Any, rows: int, cols: int) -> None:
        safe_addstr(win, 0, 1, "Agent Activity", cp(C_TITLE) | curses.A_BOLD)
        safe_addstr(win, 1, 1, "─" * max(1, cols - 2), cp(C_DIM))

        if _HAS_AGENT and _agent_mod is not None:
            status = _agent_mod.get_agent_status()
            model  = status.get("model", "?")
            skills = status.get("skills_loaded", 0)
            safe_addstr(win, 2, 1, f"Model: {model}   Skills: {skills} loaded", cp(C_DIM))
        else:
            safe_addstr(win, 2, 1, "Agent tidak tersedia.", cp(C_ERR))

        safe_addstr(win, 3, 1, "─" * max(1, cols - 2), cp(C_DIM))

        log = list(_agent_activity_log)
        content_rows = rows - 6
        if not log:
            safe_addstr(win, 5, 2, "Belum ada aktivitas.", cp(C_DIM))
            safe_addstr(win, 6, 2, "Kirim pesan di [6] AI Chat untuk melihat aktivitas.", cp(C_DIM))
        else:
            start = max(0, len(log) - content_rows)
            for i, entry in enumerate(log[start:]):
                if i >= content_rows:
                    break
                evt   = entry.get("event_type", "")
                icon, color = self._EVENT_ICONS.get(evt, ("·", C_DIM))
                ts    = entry.get("time", "--:--:--")
                text  = entry.get("content", "")
                line  = f"[{ts}] {icon} {text}"
                safe_addstr(win, 4 + i, 2, line[: cols - 4], cp(color))

        safe_addstr(win, rows - 1, 2, "[C] Hapus log", cp(C_MENU))


class KanbanScreen(Screen):
    """Real-time Kanban board — agents as cards, lifecycle columns."""

    def handle_key(self, key: int, app: "App") -> bool:
        ch = chr(key) if 0 < key < 256 else ""
        if ch in ("r", "R"):
            return True
        return False

    def draw(self, win: Any, rows: int, cols: int) -> None:
        now = time.time()
        with _kanban_lock:
            query        = _kanban_state["query"]
            query_start  = _kanban_state["query_start"]
            agents       = {k: dict(v) for k, v in _kanban_state["agents"].items()}

        total_elapsed = now - query_start

        safe_addstr(win, 0, 1, "Status Agent", cp(C_TITLE) | curses.A_BOLD)
        if query:
            elapsed_str = f" [{total_elapsed:.0f}s]"
            safe_addstr(win, 0, 14, f" ← {query[: cols - 22]}", cp(C_DIM))
            safe_addstr(win, 0, max(14, cols - len(elapsed_str) - 1), elapsed_str, cp(C_WARN))
        safe_addstr(win, 1, 1, "─" * max(1, cols - 2), cp(C_DIM))

        n_cols   = len(KANBAN_COLS)
        col_w    = max(10, (cols - 2) // n_cols)
        header_y = 2
        cards_y  = 4

        # Column headers
        for ci, (col_id, col_label) in enumerate(KANBAN_COLS):
            x = 1 + ci * col_w
            color = _KANBAN_COL_COLOR.get(col_id, C_DIM)
            hdr = col_label.center(col_w - 1)[: col_w - 1]
            safe_addstr(win, header_y, x, hdr, cp(color) | curses.A_BOLD)
            safe_addstr(win, header_y + 1, x, "─" * (col_w - 1), cp(C_DIM))

        # Agent cards per column
        col_counts: dict[str, int] = {c: 0 for c, _ in KANBAN_COLS}
        for alias, info in AGENT_INFO.items():
            state   = agents[alias]
            col_id  = state["col"]
            color   = _KANBAN_COL_COLOR.get(col_id, C_DIM)
            ci      = next((i for i, (c, _) in enumerate(KANBAN_COLS) if c == col_id), 0)
            x       = 1 + ci * col_w
            y       = cards_y + col_counts[col_id] * 3
            elapsed = now - state.get("col_since", now)

            if y + 2 >= rows - 1:
                continue

            # Line 1: alias/role + elapsed time right-aligned inside col_w
            name_part    = f" {alias}/{info}"
            elapsed_part = f"{elapsed:.0f}s "
            pad = col_w - 1 - len(name_part) - len(elapsed_part)
            card_name = (name_part + " " * max(0, pad) + elapsed_part)[: col_w - 1]
            safe_addstr(win, y, x, card_name, cp(color) | curses.A_BOLD)

            # Line 2: tool count + last tool
            if state["tool_count"]:
                detail = f" ⚙{state['tool_count']} {state['last_tool']}"
            else:
                detail = ""
            safe_addstr(win, y + 1, x, detail[: col_w - 1], cp(C_DIM))
            safe_addstr(win, y + 2, x, "·" * (col_w - 2), cp(C_DIM))

            col_counts[col_id] += 1

        safe_addstr(win, rows - 1, 2, "[R] Refresh  (otomatis update saat AI Chat aktif)", cp(C_MENU))


class TokenMetricsScreen(Screen):
    """Token utilization monitor — ctx%, predict%, tps, done_reason per agent."""

    def handle_key(self, key: int, app: "App") -> bool:
        ch = chr(key) if 0 < key < 256 else ""
        if ch in ("r", "R"):
            return True
        if ch in ("c", "C"):
            if _HAS_AGENT and _agent_mod is not None:
                try:
                    from agents.metrics import METRICS_PATH  # noqa: PLC0415
                    if METRICS_PATH.exists():
                        METRICS_PATH.unlink()
                except Exception:
                    pass
            return True
        return False

    def draw(self, win: Any, rows: int, cols: int) -> None:
        safe_addstr(win, 0, 1, "Token Utilization", cp(C_TITLE) | curses.A_BOLD)
        safe_addstr(win, 1, 1, "─" * max(1, cols - 2), cp(C_DIM))

        entries: list[dict] = []
        if _HAS_AGENT and _agent_mod is not None and hasattr(_agent_mod, "get_token_metrics"):
            try:
                entries = _agent_mod.get_token_metrics(100)
            except Exception:
                pass

        if not entries:
            safe_addstr(win, 3, 2, "Belum ada data. Kirim pesan di [6] AI Chat untuk mulai merekam.", cp(C_DIM))
            safe_addstr(win, rows - 1, 2, "[R] Refresh   [C] Hapus data", cp(C_MENU))
            return

        # ── Per-agent summary ─────────────────────────────────────────────────
        row = 2
        safe_addstr(win, row, 1, "Per-Agent Summary", cp(C_DIM) | curses.A_BOLD)
        row += 1

        hdr = f"{'Agent':<20} {'Calls':>5}  {'ctx_avg':>7}  {'predict_avg':>11}  {'tps_avg':>7}  {'⚠':>3}"
        safe_addstr(win, row, 2, hdr[: cols - 4], cp(C_DIM) | curses.A_UNDERLINE)
        row += 1

        # Aggregate per agent
        from collections import defaultdict  # noqa: PLC0415
        agg: dict[str, dict] = defaultdict(lambda: {"n": 0, "ctx": 0.0, "pred": 0.0, "tps": 0.0, "warn": 0})
        for e in entries:
            a = e.get("agent", "?")
            agg[a]["n"]    += 1
            agg[a]["ctx"]  += e.get("ctx_util", 0)
            agg[a]["pred"] += e.get("predict_util", 0)
            agg[a]["tps"]  += e.get("tps", 0)
            if e.get("done_reason") == "length":
                agg[a]["warn"] += 1

        for agent, d in sorted(agg.items()):
            n = d["n"]
            ctx_avg  = d["ctx"]  / n
            pred_avg = d["pred"] / n
            tps_avg  = d["tps"]  / n
            warn     = d["warn"]
            color = C_ERR if warn else C_OK
            warn_s = f"{warn} ⚠" if warn else "  -"
            line = f"{agent:<20} {n:>5}  {ctx_avg:>6.1f}%  {pred_avg:>10.1f}%  {tps_avg:>7.1f}  {warn_s:>4}"
            safe_addstr(win, row, 2, line[: cols - 4], cp(color))
            row += 1
            if row >= rows - 7:
                break

        row += 1
        safe_addstr(win, row, 1, "─" * max(1, cols - 2), cp(C_DIM))
        row += 1

        # ── Recent calls ──────────────────────────────────────────────────────
        safe_addstr(win, row, 1, "Recent Calls", cp(C_DIM) | curses.A_BOLD)
        row += 1

        col_hdr = f"{'Time':<8}  {'Agent':<20} {'ctx%':>5}  {'predict%':>8}  {'reason':<9}  {'tps':>5}  {'ms':>6}"
        safe_addstr(win, row, 2, col_hdr[: cols - 4], cp(C_DIM) | curses.A_UNDERLINE)
        row += 1

        recent = entries[-max(1, rows - row - 2):]
        for e in reversed(recent):
            if row >= rows - 1:
                break
            ts          = e.get("ts", "")[-8:]   # HH:MM:SS
            agent       = e.get("agent", "?")
            ctx_u       = e.get("ctx_util", 0)
            pred_u      = e.get("predict_util", 0)
            done        = e.get("done_reason", "?")
            tps         = e.get("tps", 0)
            ms          = e.get("total_ms", 0)
            is_warn     = done == "length"
            color       = C_ERR if is_warn else C_OK
            reason_s    = f"{done} ⚠" if is_warn else done
            line = f"{ts:<8}  {agent:<20} {ctx_u:>4.1f}%  {pred_u:>7.1f}%  {reason_s:<9}  {tps:>5.1f}  {ms:>6.0f}"
            safe_addstr(win, row, 2, line[: cols - 4], cp(color))
            row += 1

        safe_addstr(win, rows - 1, 2, "[R] Refresh   [C] Hapus data", cp(C_MENU))


class AIScreen(Screen):
    """Interactive AI chat powered by NetOps multi-agent."""

    def __init__(self) -> None:
        super().__init__()
        with self._lock:
            self.data["history"] = []
            self.data["state"] = "IDLE"
            self.data["scroll"] = 0
            self.data["input_buf"] = ""
            self.data["input_mode"] = True
            self.data["pending_approval"] = None
            self.data["exec_start"] = None
        self._agent: Any = None
        self._agent_config: dict[str, Any] = {}
        if _HAS_AGENT and _agent_mod is not None:
            try:
                self._agent, self._agent_config = \
                    _agent_mod.create_agent(thread_id=str(id(self)))
            except Exception as exc:
                self.data["history"].append({
                    "role": "assistant",
                    "content": f"⚠ Agent init gagal: {exc}",
                })

    def refresh(self) -> None:
        pass

    def _send_message(self, app: "App") -> None:
        with self._lock:
            buf = self.data.get("input_buf", "").strip()
            if not buf:
                return
            self.data["history"].append({"role": "user", "content": buf})
            self.data["input_buf"] = ""
            self.data["state"] = "WAITING"
            self.data["scroll"] = 999999
            user_msg = buf

        threading.Thread(
            target=self._call_agent,
            args=(user_msg, app),
            daemon=True,
        ).start()

    def _call_agent(self, user_msg: str, app: "App") -> None:
        """Stream agent response in a background thread."""
        if not _HAS_AGENT or self._agent is None:
            with self._lock:
                self.data["history"].append({
                    "role": "assistant",
                    "content": "⚠ Agent tidak tersedia. Pastikan modul agent.py dan dependencies terinstall.",
                })
                self.data["state"] = "IDLE"
            app._wake.set()
            return

        _kanban_reset(user_msg)
        t_start = time.time()
        with self._lock:
            self.data["exec_start"] = t_start
        ai_chunks: list[str] = []
        try:
            for event_type, content in _agent_mod.stream_agent_response(
                self._agent, self._agent_config, user_msg
            ):
                _kanban_update(event_type, content)
                ts = dt.datetime.now().strftime("%H:%M:%S")
                with self._lock:
                    if event_type in ("routing", "tool_call", "tool_result"):
                        icon = {"routing": "→", "tool_call": "⚙", "tool_result": "✓"}.get(event_type, "·")
                        self.data["history"].append({
                            "role": "agent_event",
                            "content": f"[{icon} {content}]",
                        })
                        self.data["scroll"] = 999999
                        _agent_activity_log.append({
                            "event_type": event_type,
                            "content": content,
                            "time": ts,
                        })
                    elif event_type == "ai":
                        ai_chunks.append(content)
                    elif event_type == "error":
                        self.data["history"].append({
                            "role": "assistant",
                            "content": f"⚠ Agent error: {content}",
                        })
                        self.data["scroll"] = 999999
                    elif event_type == "approval_required":
                        self.data["pending_approval"] = content
                        self.data["state"] = "APPROVAL"
                        self.data["scroll"] = 999999
                        _agent_activity_log.append({
                            "event_type": "approval_required",
                            "content": content,
                            "time": ts,
                        })
                app._wake.set()
                if event_type == "approval_required":
                    return

            elapsed = time.time() - t_start
            final = "\n".join(ai_chunks).strip()
            with self._lock:
                if final:
                    self.data["history"].append({"role": "assistant", "content": final})
                self.data["history"].append({
                    "role": "agent_event",
                    "content": f"[⏱ selesai dalam {elapsed:.1f}s]",
                })
                self.data["state"] = "IDLE"
                self.data["exec_start"] = None
                self.data["scroll"] = 999999
        except Exception as exc:
            elapsed = time.time() - t_start
            with self._lock:
                self.data["history"].append({
                    "role": "assistant",
                    "content": f"⚠ Agent error: {exc}",
                })
                self.data["history"].append({
                    "role": "agent_event",
                    "content": f"[⏱ gagal setelah {elapsed:.1f}s]",
                })
                self.data["state"] = "IDLE"
                self.data["exec_start"] = None
        app._wake.set()

    def _submit_approval(self, decision: str, app: "App") -> None:
        """Submit approval decision and resume the paused graph."""
        with self._lock:
            self.data["pending_approval"] = None
            self.data["state"] = "WAITING"
            self.data["history"].append({
                "role": "agent_event",
                "content": f"[✓ Operator: {decision.upper()}]",
            })
            self.data["scroll"] = 999999
        app._wake.set()
        threading.Thread(
            target=self._resume_after_approval,
            args=(decision, app),
            daemon=True,
        ).start()

    def _resume_after_approval(self, decision: str, app: "App") -> None:
        try:
            _agent_mod.submit_approval(self._agent, self._agent_config, decision)
            with self._lock:
                self.data["state"] = "IDLE"
        except Exception as exc:
            with self._lock:
                self.data["history"].append({
                    "role": "assistant",
                    "content": f"⚠ Resume setelah approval gagal: {exc}",
                })
                self.data["state"] = "IDLE"
        app._wake.set()

    def handle_key(self, key: int, app: "App") -> bool:
        ch = chr(key) if 0 < key < 256 else ""

        with self._lock:
            input_mode = self.data.get("input_mode", True)

        if input_mode:
            if key == 27:
                with self._lock:
                    self.data["input_mode"] = False
                return True

            if key in (10, 13, curses.KEY_ENTER):
                with self._lock:
                    buf = self.data.get("input_buf", "").strip()
                    waiting = self.data.get("state") == "WAITING"
                if buf and not waiting:
                    self._send_message(app)
                return True

            if key in (curses.KEY_BACKSPACE, 127, 8):
                with self._lock:
                    self.data["input_buf"] = self.data.get("input_buf", "")[:-1]
                return True

            if key == 21:
                with self._lock:
                    self.data["input_buf"] = ""
                return True

            if key in (curses.KEY_UP, 259):
                with self._lock:
                    self.data["scroll"] = max(0, int(self.data.get("scroll", 0)) - 1)
                return True

            if key in (curses.KEY_DOWN, 258):
                with self._lock:
                    total = self.data.get("_rendered_total", len(self.data.get("history", [])) * 8)
                    vis = self.data.get("_visible_rows", 20)
                    self.data["scroll"] = min(
                        max(0, total - vis),
                        int(self.data.get("scroll", 0)) + 1,
                    )
                return True

            if 32 <= key <= 126:
                with self._lock:
                    self.data["input_buf"] = self.data.get("input_buf", "") + chr(key)
                return True

            return False

        # Approval response (Y/N) when waiting for operator decision
        with self._lock:
            state = self.data.get("state", "IDLE")
        if state == "APPROVAL":
            if ch in ("y", "Y"):
                self._submit_approval("approved", app)
                return True
            if ch in ("n", "N"):
                self._submit_approval("rejected", app)
                return True

        if ch in ("i", "I") or key in (10, 13):
            with self._lock:
                self.data["input_mode"] = True
            return True

        if ch in ("c", "C"):
            if app.modal_confirm(["Hapus semua riwayat chat?"]):
                with self._lock:
                    self.data["history"] = []
                    self.data["state"] = "IDLE"
                    self.data["scroll"] = 0
                    self.data["input_buf"] = ""
                if _HAS_AGENT and _agent_mod is not None:
                    try:
                        new_tid = f"{id(self)}-{int(time.time())}"
                        self._agent, self._agent_config = \
                            _agent_mod.create_agent(thread_id=new_tid)
                    except Exception:
                        pass
            return True

        if ch in ("j", "J"):
            with self._lock:
                total = self.data.get("_rendered_total", len(self.data.get("history", [])) * 8)
                vis = self.data.get("_visible_rows", 20)
                self.data["scroll"] = min(
                    max(0, total - vis),
                    int(self.data.get("scroll", 0)) + 1,
                )
            return True

        if ch in ("k", "K"):
            with self._lock:
                self.data["scroll"] = max(0, int(self.data.get("scroll", 0)) - 1)
            return True

        return False

    def draw(self, win: Any, rows: int, cols: int) -> None:
        with self._lock:
            history = list(self.data.get("history", []))
            state = self.data.get("state", "IDLE")
            scroll = int(self.data.get("scroll", 0))
            input_buf = self.data.get("input_buf", "")
            input_mode = self.data.get("input_mode", True)

        agent_label = "NetOps Agent" if (_HAS_AGENT and self._agent is not None) else "Agent tidak tersedia"
        safe_addstr(
            win, 0, 1,
            f"AI Chat  [{agent_label}]",
            cp(C_TITLE) | curses.A_BOLD,
        )
        safe_addstr(win, 1, 1, "─" * max(1, cols - 2), cp(C_DIM))

        input_sep_row = rows - 4
        input_row = rows - 3
        status_row = rows - 2
        hint_row = rows - 1
        content_rows = input_sep_row - 2

        if not history:
            safe_addstr(win, 3, 2, "Belum ada percakapan.", cp(C_DIM))
            mode_hint = (
                "Mode: INSERT" if input_mode else "Mode: NORMAL - tekan [I] untuk mulai ketik"
            )
            safe_addstr(win, 4, 2, mode_hint, cp(C_DIM))
        else:
            rendered: list[tuple[str, int]] = []
            for msg in history:
                role = msg.get("role", "")
                content = msg.get("content", "")
                if role == "user":
                    prefix = "Anda: "
                    attr = cp(C_OK) | curses.A_BOLD
                elif role == "agent_event":
                    prefix = "  ↳ "
                    attr = cp(C_DIM)
                else:
                    prefix = "AI  : "
                    attr = cp(C_WARN)

                # Strip markdown and preserve newlines
                clean = strip_markdown(content)
                paragraphs = clean.split("\n")
                first_line = True
                for para_idx, para in enumerate(paragraphs):
                    if not para.strip():
                        # Blank line between paragraphs
                        rendered.append(("", 0))
                        continue
                    # Word-wrap this paragraph
                    indent = prefix if first_line else " " * len(prefix)
                    words = para.split()
                    line = indent
                    line_first = first_line
                    for word in words:
                        if len(line) + len(word) + 1 > cols - 3:
                            rendered.append((line.rstrip(), attr if line_first else cp(C_TITLE)))
                            line = " " * len(prefix) + word + " "
                            line_first = False
                            first_line = False
                        else:
                            line += word + " "
                    if line.strip():
                        rendered.append((line.rstrip(), attr if line_first else cp(C_TITLE)))
                        first_line = False
                rendered.append(("", 0))

            total = len(rendered)
            visible = max(1, content_rows)
            max_scroll = max(0, total - visible)
            clamped = max(0, min(scroll, max_scroll))
            with self._lock:
                # Store for accurate scroll clamping in handle_key
                self.data["_rendered_total"] = total
                self.data["_visible_rows"] = visible
                # Normalize scroll position after snap-to-end (999999 → real max)
                if int(self.data.get("scroll", 0)) == scroll and clamped != scroll:
                    self.data["scroll"] = clamped
            start = clamped
            view = rendered[start : start + visible]
            for idx, (line, attr) in enumerate(view):
                row_pos = 2 + idx
                if row_pos >= input_sep_row:
                    break
                if line:
                    safe_addstr(win, row_pos, 2, line[: cols - 3], attr)

        safe_addstr(win, input_sep_row, 1, "─" * max(1, cols - 2), cp(C_DIM))

        if state == "APPROVAL":
            with self._lock:
                approval_data = self.data.get("pending_approval", "")
            safe_addstr(win, input_sep_row - 2, 1, "─" * max(1, cols - 2), cp(C_ERR))
            safe_addstr(win, input_sep_row - 1, 2,
                        "⚠ APPROVAL REQUIRED — agent meminta izin sebelum melanjutkan",
                        cp(C_ERR) | curses.A_BOLD)
            safe_addstr(win, input_row, 2,
                        f"Aksi: {str(approval_data)[:cols-10]}",
                        cp(C_WARN))
            safe_addstr(win, status_row, 2,
                        "[Y] Setuju   [N] Tolak",
                        cp(C_OK) | curses.A_BOLD)
            safe_addstr(win, hint_row, 1,
                        "Operator harus menyetujui aksi config agent sebelum dieksekusi.",
                        cp(C_DIM))
            return
        elif state == "WAITING":
            spin = SPINNER[int(time.time() * 8) % len(SPINNER)]
            with self._lock:
                exec_start = self.data.get("exec_start")
            live_elapsed = f"  {time.time() - exec_start:.0f}s" if exec_start else ""
            safe_addstr(
                win,
                input_row,
                2,
                f"{spin} Agent sedang bekerja...{live_elapsed}",
                cp(C_WARN) | curses.A_BOLD,
            )
        else:
            prompt = "> "
            max_input_width = cols - len(prompt) - 4
            display_buf = input_buf
            if len(input_buf) > max_input_width:
                display_buf = input_buf[-max_input_width:]
            cursor = "▋" if input_mode else ""
            input_line = f"{prompt}{display_buf}{cursor}"

            if input_mode:
                safe_addstr(
                    win,
                    input_row,
                    2,
                    input_line[: cols - 3],
                    cp(C_OK) | curses.A_BOLD,
                )
            else:
                safe_addstr(
                    win,
                    input_row,
                    2,
                    f"{prompt}{display_buf}"[: cols - 3],
                    cp(C_DIM),
                )

        mode_label = "INSERT" if input_mode else "NORMAL"
        mode_attr = cp(C_OK) if input_mode else cp(C_WARN)
        safe_addstr(win, status_row, 2, f"Mode: {mode_label}", mode_attr | curses.A_BOLD)

        if input_mode:
            safe_addstr(
                win, hint_row, 1,
                "[Enter] Kirim  [Esc] Nav  [^U] Hapus baris  [↑↓] Scroll",
                cp(C_MENU),
            )
        else:
            safe_addstr(
                win, hint_row, 1,
                "[I] Insert  [C] Hapus riwayat  [J/K] Scroll  [1-8] Menu  [8] Kanban",
                cp(C_MENU),
            )


class App:
    """Main TUI application."""

    def __init__(self) -> None:
        LAPORAN_DIR.mkdir(parents=True, exist_ok=True)
        self.screens: list[Screen] = [
            DashboardScreen(),
            SkillsScreen(),
            ReachabilityScreen(),
            LaporanScreen(),
            LogScreen(),
            AIScreen(),
            AgentActivityScreen(),
            KanbanScreen(),
            TokenMetricsScreen(),
        ]
        self.current = 0
        self._wake = threading.Event()
        self._stop = threading.Event()
        self.stdscr: Any = None
        self._header_win = None
        self._menu_win = None
        self._content_win = None
        self._footer_win = None
        self._rows = 0
        self._cols = 0

    def run(self) -> None:
        curses.wrapper(self._run)

    def _run(self, stdscr: Any) -> None:
        global _HAS_COLORS

        self.stdscr = stdscr
        curses.curs_set(0)
        stdscr.timeout(100)
        stdscr.keypad(True)
        stdscr.notimeout(False)
        curses.set_escdelay(25)

        if curses.has_colors():
            try:
                curses.start_color()
                curses.use_default_colors()
                curses.init_pair(C_HEADER, curses.COLOR_WHITE, curses.COLOR_BLUE)
                curses.init_pair(C_MENU, curses.COLOR_CYAN, -1)
                curses.init_pair(C_MENU_SEL, curses.COLOR_BLACK, curses.COLOR_CYAN)
                curses.init_pair(C_OK, curses.COLOR_GREEN, -1)
                curses.init_pair(C_ERR, curses.COLOR_RED, -1)
                curses.init_pair(C_WARN, curses.COLOR_YELLOW, -1)
                curses.init_pair(C_TITLE, curses.COLOR_WHITE, -1)
                curses.init_pair(C_DIM, curses.COLOR_CYAN, -1)
                _HAS_COLORS = True
            except curses.error:
                _HAS_COLORS = False

        self._init_windows()

        self.screens[self.current].refresh()
        self._wake.set()

        t = threading.Thread(target=self._refresh_worker, daemon=True)
        t.start()

        running = True
        while running:
            key = stdscr.getch()
            if key == curses.KEY_RESIZE:
                curses.resizeterm(*stdscr.getmaxyx())
                self._init_windows()
                self._wake.set()
            elif key != -1:
                running = self.handle_key(key)

            if self._wake.is_set():
                self.draw()
                self._wake.clear()
            else:
                self._update_clock()

        self._stop.set()

    def _init_windows(self) -> None:
        """Create/recreate all windows based on current terminal size."""
        rows, cols = self.stdscr.getmaxyx()
        self._rows = rows
        self._cols = cols

        self._header_win = None
        self._menu_win = None
        self._content_win = None
        self._footer_win = None

    def _refresh_worker(self) -> None:
        while not self._stop.is_set():
            try:
                self.screens[self.current].refresh()
                self._wake.set()
            except Exception:
                pass
            self._stop.wait(timeout=REFRESH_INTERVAL)

    def handle_key(self, key: int) -> bool:
        """Handle global key events. Return False to quit."""
        ch = chr(key) if 0 < key < 256 else ""

        if key == 17:
            return False

        if self.current == 5:
            ai_screen = self.screens[5]
            if ai_screen.data.get("input_mode", True) or ai_screen.data.get("state") == "APPROVAL":
                consumed = ai_screen.handle_key(key, self)
                if consumed:
                    self._wake.set()
                return True

        if ch in ("q", "Q"):
            return False

        if ch and ch in "123456789":
            idx = int(ch) - 1
            if idx != self.current:
                self.current = idx
                if idx == 5:
                    self.screens[5].data["input_mode"] = True
                self.screens[self.current].refresh()
                self._wake.set()
            return True

        is_up = key in (curses.KEY_UP, 259) or ch in ("k", "K")
        is_down = key in (curses.KEY_DOWN, 258) or ch in ("j", "J")

        if is_up:
            if self.current > 0:
                self.current -= 1
                self.screens[self.current].refresh()
                self._wake.set()
            return True

        if is_down:
            if self.current < len(self.screens) - 1:
                self.current += 1
                if self.current == 5:
                    self.screens[5].data["input_mode"] = True
                self.screens[self.current].refresh()
                self._wake.set()
            return True

        if key in (curses.KEY_ENTER, 10, 13):
            self._wake.set()
            return True

        consumed = self.screens[self.current].handle_key(key, self)
        if consumed:
            self._wake.set()
        return True

    def draw(self) -> None:
        rows, cols = self.stdscr.getmaxyx()
        self.stdscr.erase()

        if rows < MIN_ROWS or cols < MIN_COLS:
            msg = (
                f"Terminal terlalu kecil (min {MIN_COLS}x{MIN_ROWS}, "
                f"sekarang {cols}x{rows})"
            )
            safe_addstr(
                self.stdscr,
                rows // 2,
                max(0, cols // 2 - len(msg) // 2),
                msg[:cols],
                cp(C_ERR) | curses.A_BOLD,
            )
            self.stdscr.refresh()
            return

        self._draw_header(rows, cols)
        self._draw_menu(rows, cols)
        self._draw_separator(rows, cols)
        self._draw_content(rows, cols)
        self._draw_footer(rows, cols)
        self.stdscr.refresh()

    def _draw_header(self, rows: int, cols: int) -> None:
        """Draw full-width header with title and clock."""
        attr = cp(C_HEADER) | curses.A_BOLD
        safe_addstr(self.stdscr, 0, 0, " " * max(0, cols), attr)
        safe_addstr(self.stdscr, 0, 1, TITLE[: max(1, cols - 22)], attr)
        clock = dt.datetime.now().strftime("%a %d %b  %H:%M:%S")
        safe_addstr(self.stdscr, 0, max(0, cols - len(clock) - 2), clock, attr)

    def _update_clock(self) -> None:
        """Update header clock only without full redraw."""
        rows, cols = self.stdscr.getmaxyx()
        if rows < 1:
            return
        clock = dt.datetime.now().strftime("%a %d %b  %H:%M:%S")
        safe_addstr(
            self.stdscr,
            0,
            max(0, cols - len(clock) - 2),
            clock,
            cp(C_HEADER) | curses.A_BOLD,
        )
        self.stdscr.refresh()

    def _draw_menu(self, rows: int, cols: int) -> None:
        """Draw left menu panel."""
        for i, (key, label) in enumerate(MENU):
            row = 2 + i * 2
            if row >= rows - 1:
                break
            if i == self.current:
                attr = cp(C_MENU_SEL) | curses.A_BOLD
                mark = "▶ "
            else:
                attr = cp(C_MENU)
                mark = "  "
            text = f"{mark}[{key}] {label}"
            text = text.ljust(MENU_WIDTH - 1)[: MENU_WIDTH - 1]
            safe_addstr(self.stdscr, row, 1, text, attr)

        safe_addstr(self.stdscr, rows - 2, 1, "[Q] Keluar"[: MENU_WIDTH - 1], cp(C_DIM))

    def _draw_separator(self, rows: int, cols: int) -> None:
        """Draw vertical separator between menu and content."""
        for r in range(1, rows - 1):
            safe_addstr(self.stdscr, r, MENU_WIDTH, "│", cp(C_DIM))

    def _draw_content(self, rows: int, cols: int) -> None:
        """Draw active screen content in a sub-window."""
        content_rows = rows - 2
        content_cols = cols - MENU_WIDTH - 1
        if content_rows < 1 or content_cols < 1:
            return

        try:
            win = self.stdscr.derwin(content_rows, content_cols, 1, MENU_WIDTH + 1)
            win.erase()
            self.screens[self.current].draw(win, content_rows, content_cols)
            win.refresh()
        except curses.error:
            pass

    def _draw_footer(self, rows: int, cols: int) -> None:
        """Draw footer with key hints."""
        hints = " [1-8] Menu  [↑↓] Nav  [Q] Keluar  [R] Refresh "
        safe_addstr(
            self.stdscr,
            rows - 1,
            0,
            hints.ljust(cols)[:cols],
            cp(C_HEADER),
        )

    def modal_confirm(self, lines: list[str]) -> bool:
        """Show centered yes/no modal and return True on Y."""
        rows, cols = self.stdscr.getmaxyx()
        if not lines:
            lines = ["Konfirmasi?"]
        h = len(lines) + 4
        w = max(len(l) for l in lines) + 6
        w = min(w, max(20, cols - 4))
        y = max(0, rows // 2 - h // 2)
        x = max(0, cols // 2 - w // 2)

        try:
            win = curses.newwin(h, w, y, x)
            win.erase()
            win.border()
            for i, line in enumerate(lines):
                safe_addstr(win, 1 + i, 2, line[: w - 4])
            safe_addstr(win, h - 2, 2, "[Y] Ya  [N] Tidak", cp(C_MENU))
            win.refresh()
            while True:
                k = self.stdscr.getch()
                if k in (ord("y"), ord("Y")):
                    return True
                if k in (ord("n"), ord("N"), 27):
                    return False
        except curses.error:
            return False

    def modal_input(self, prompt: str) -> str:
        """Show centered input modal and return user text."""
        rows, cols = self.stdscr.getmaxyx()
        w = max(len(prompt) + 20, 40)
        w = min(w, max(20, cols - 4))
        h = 5
        y = max(0, rows // 2 - h // 2)
        x = max(0, cols // 2 - w // 2)

        try:
            win = curses.newwin(h, w, y, x)
            win.erase()
            win.border()
            safe_addstr(win, 1, 2, prompt[: w - 4])
            safe_addstr(win, 2, 2, "-> ")
            win.refresh()
            curses.echo()
            curses.curs_set(1)
            raw = win.getstr(2, 5, w - 8)
            result = raw.decode("utf-8", errors="replace").strip()
            curses.noecho()
            curses.curs_set(0)
            return result
        except curses.error:
            curses.noecho()
            curses.curs_set(0)
            return ""

    def modal_message(self, lines: list[str], duration: float = 2.0) -> None:
        """Show centered timed message modal."""
        rows, cols = self.stdscr.getmaxyx()
        if not lines:
            lines = ["OK"]
        h = len(lines) + 4
        w = max(len(l) for l in lines) + 6
        w = min(w, max(20, cols - 4))
        y = max(0, rows // 2 - h // 2)
        x = max(0, cols // 2 - w // 2)
        try:
            win = curses.newwin(h, w, y, x)
            win.erase()
            win.border()
            for i, line in enumerate(lines):
                safe_addstr(win, 1 + i, 2, line[: w - 4])
            safe_addstr(win, h - 2, 2, "Tutup otomatis...", cp(C_DIM))
            win.refresh()
            time.sleep(duration)
        except curses.error:
            pass


def _run_headless(args: list[str]) -> None:
    """
    Headless mode — tanpa curses, cocok untuk dijalankan dari non-interactive shell.

    Satu pesan:   python tui.py --headless "status jaringan"
    Interaktif:   python tui.py --headless          (baca dari stdin, Ctrl+D untuk keluar)
    Debug mode:   python tui.py --headless --debug "pesan"
    """
    import json as _json
    import logging
    import sys

    debug = "--debug" in args
    if debug:
        args = [a for a in args if a != "--debug"]
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(name)s %(levelname)s: %(message)s",
            stream=sys.stdout,
        )
        logging.getLogger("agents.nodes").setLevel(logging.DEBUG)
    else:
        logging.basicConfig(level=logging.WARNING, stream=sys.stderr)

    if not _HAS_AGENT or _agent_mod is None:
        print("ERROR: agent module tidak tersedia. Pastikan dependencies terinstall.", flush=True)
        return

    graph, config = _agent_mod.create_agent(thread_id="headless")

    def _send(msg: str) -> None:
        print(f"\n>>> {msg}", flush=True)
        for event_type, content in _agent_mod.stream_agent_response(graph, config, msg):
            if event_type == "ai":
                print(f"\nAI: {content}\n", flush=True)
            elif event_type in ("routing", "tool_call", "tool_result"):
                icon = {"routing": "→", "tool_call": "⚙", "tool_result": "✓"}.get(event_type, "·")
                preview = content[:120] + "…" if len(content) > 120 else content
                print(f"  [{icon}] {preview}", flush=True)
            elif event_type == "error":
                print(f"\nERROR: {content}\n", flush=True)
            elif event_type == "approval_required":
                try:
                    data = _json.loads(content)
                    action = data.get("action", content)
                except Exception:
                    action = content
                print(f"\nAPPROVAL_REQUIRED: {action}", flush=True)
                decision = input("Ketik 'approved' atau 'rejected': ").strip()
                _agent_mod.submit_approval(graph, config, decision or "rejected")

    if args:
        _send(" ".join(args))
    else:
        print("NetOps AI — Headless Mode  (Ctrl+D atau 'exit' untuk keluar)", flush=True)
        while True:
            try:
                msg = input("\n> ").strip()
            except EOFError:
                break
            if msg.lower() in ("exit", "quit", "keluar"):
                break
            if msg:
                _send(msg)


if __name__ == "__main__":
    import locale
    import logging
    import sys

    if "--headless" in sys.argv:
        args = [a for a in sys.argv[1:] if a != "--headless"]
        _run_headless(args)
        sys.exit(0)

    # Redirect stderr ke log file — mencegah traceback paramiko/library lain
    # merusak tampilan curses di terminal.
    _stderr_log = open(WORKDIR / "netops_stderr.log", "a", buffering=1)
    sys.stderr = _stderr_log

    # Suppress paramiko transport thread exception noise
    logging.getLogger("paramiko").setLevel(logging.CRITICAL)
    logging.getLogger("paramiko.transport").setLevel(logging.CRITICAL)

    locale.setlocale(locale.LC_ALL, "")
    try:
        App().run()
    except KeyboardInterrupt:
        pass
    finally:
        _stderr_log.close()
