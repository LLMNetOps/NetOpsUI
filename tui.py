#!/usr/bin/env python3
"""Single-file curses TUI for DHCP lease monitoring."""

from __future__ import annotations

import curses
import datetime as dt
import os
import re
import shutil
import subprocess
import threading
import time
from pathlib import Path
from typing import Any


WORKDIR = Path(__file__).parent
OUTPUT_DIR = WORKDIR / "output"
LAPORAN_DIR = WORKDIR / "laporan"
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
    ("2", "Jadwal"),
    ("3", "Collect"),
    ("4", "Laporan"),
    ("5", "Log"),
    ("6", "AI Chat"),
    ("7", "Aktivitas Agent"),
]

# ── Agent module ─────────────────────────────────────────────────────────────
_HAS_AGENT = False
_agent_mod = None
try:
    import agent as _agent_mod
    _HAS_AGENT = True
except Exception:
    pass

# Shared activity log: written by AIScreen, read by AgentActivityScreen
_agent_activity_log: list[dict] = []

_HAS_COLORS = False
ATQ_RE = re.compile(r"^(\d+)\t(\w{3} \w{3}\s+\d+ \d{2}:\d{2}:\d{2} \d{4})")


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


def parse_atq() -> list[dict[str, Any]]:
    """Parse atq output into dictionaries: id, dt, label."""
    output = run_cmd(["atq"], cwd=WORKDIR, timeout=5)
    jobs: list[dict[str, Any]] = []
    for raw in output.splitlines():
        line = raw.strip("\n")
        m = ATQ_RE.match(line)
        if not m:
            continue
        job_id = m.group(1)
        dt_str = m.group(2)
        try:
            parsed_dt = dt.datetime.strptime(dt_str, "%a %b %d %H:%M:%S %Y")
        except ValueError:
            continue
        jobs.append({"id": job_id, "dt": parsed_dt, "label": dt_str})
    return jobs


def format_countdown(target: dt.datetime) -> str:
    """Format countdown from now to target datetime."""
    if not target:
        return "-"
    now = dt.datetime.now()
    delta = target - now
    sec = int(delta.total_seconds())
    if sec < 0:
        return "overdue"
    hours = sec // 3600
    minutes = (sec % 3600) // 60
    return f"{hours}h {minutes}m"


def today_str() -> str:
    """Return today's date in YYYYMMDD format."""
    return dt.datetime.now().strftime("%Y%m%d")


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
    """Overview status and key counters."""

    def refresh(self) -> None:
        atd_status = run_cmd(["systemctl", "is-active", "atd"]).strip() or "unknown"
        at_available = shutil.which("at") is not None
        jobs = sorted(parse_atq(), key=lambda x: x["dt"])

        now = dt.datetime.now()
        next_job = None
        for item in jobs:
            if item["dt"] > now:
                next_job = item
                break

        txt_today = len(list(OUTPUT_DIR.glob(f"*{today_str()}*.txt")))
        md_all = len(list(LAPORAN_DIR.glob("*.md")))

        recent = sorted(
            OUTPUT_DIR.glob("*.txt"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )[:5]

        with self._lock:
            self.data["atd_status"] = atd_status
            self.data["at_available"] = at_available
            self.data["jobs"] = jobs
            self.data["next_job"] = next_job
            self.data["txt_today"] = txt_today
            self.data["md_all"] = md_all
            self.data["recent_txt"] = [p.name for p in recent]

    def draw(self, win: Any, rows: int, cols: int) -> None:
        with self._lock:
            data = dict(self.data)

        safe_addstr(win, 0, 1, "Dashboard", cp(C_TITLE) | curses.A_BOLD)
        safe_addstr(win, 1, 1, "-" * max(1, cols - 2), cp(C_DIM))

        safe_addstr(win, 3, 2, "Status Sistem", cp(C_TITLE) | curses.A_BOLD)
        safe_addstr(win, 4, 2, "-------------", cp(C_DIM))

        atd_active = data.get("atd_status") == "active"
        if atd_active:
            safe_addstr(win, 5, 2, "atd service  : ", 0)
            safe_addstr(win, 5, 17, "● active", cp(C_OK) | curses.A_BOLD)
        else:
            safe_addstr(win, 5, 2, "atd service  : ", 0)
            safe_addstr(win, 5, 17, "✗ tidak aktif", cp(C_ERR) | curses.A_BOLD)

        at_available = bool(data.get("at_available"))
        if at_available:
            safe_addstr(win, 6, 2, "at command   : ", 0)
            safe_addstr(win, 6, 17, "✓ tersedia", cp(C_OK) | curses.A_BOLD)
        else:
            safe_addstr(win, 6, 2, "at command   : ", 0)
            safe_addstr(win, 6, 17, "✗ tidak ditemukan", cp(C_ERR) | curses.A_BOLD)

        safe_addstr(win, 8, 2, "Jadwal Berikutnya", cp(C_TITLE) | curses.A_BOLD)
        safe_addstr(win, 9, 2, "-----------------", cp(C_DIM))

        next_job = data.get("next_job")
        if next_job:
            label = next_job["dt"].strftime("%a %b %d %H:%M:%S")
            safe_addstr(win, 10, 2, f"Job #{next_job['id']}  ->  {label}"[: cols - 3])
            safe_addstr(win, 11, 2, "Countdown  : ")
            safe_addstr(
                win,
                11,
                15,
                format_countdown(next_job["dt"]),
                cp(C_WARN) | curses.A_BOLD,
            )
        else:
            safe_addstr(win, 10, 2, "Tidak ada jadwal")
            safe_addstr(win, 11, 2, "Countdown  : -", cp(C_DIM))

        safe_addstr(win, 13, 2, "File Hari Ini", cp(C_TITLE) | curses.A_BOLD)
        safe_addstr(win, 14, 2, "--------------", cp(C_DIM))
        safe_addstr(win, 15, 2, f".txt output  :  {int(data.get('txt_today', 0))} file")
        safe_addstr(win, 16, 2, f".md laporan  :  {int(data.get('md_all', 0))} file")

        safe_addstr(win, 18, 2, "Terbaru:", cp(C_TITLE))
        recent = data.get("recent_txt", [])
        for idx, name in enumerate(recent[:5]):
            maxw = max(4, cols - 7)
            show = name if len(name) <= maxw else (name[: maxw - 3] + "...")
            safe_addstr(win, 19 + idx, 4, show)


class JadwalScreen(Screen):
    """Schedule listing and actions for at jobs."""

    def refresh(self) -> None:
        jobs = sorted(parse_atq(), key=lambda x: x["dt"])
        at_available = shutil.which("at") is not None
        with self._lock:
            self.data["jobs"] = jobs
            self.data["at_available"] = at_available

    def handle_key(self, key: int, app: "App") -> bool:
        ch = chr(key) if 0 < key < 256 else ""

        if ch in ("s", "S"):
            if app.modal_confirm(["Jalankan ./schedule_utbk.sh?"]):
                out = run_cmd(["bash", "schedule_utbk.sh"], cwd=WORKDIR, timeout=30)
                lines = ["Setup selesai."]
                if out.strip():
                    lines.extend(out.strip().splitlines()[-3:])
                app.modal_message(lines[:6], duration=3.0)
                self.refresh()
            return True

        if ch in ("c", "C"):
            if app.modal_confirm(["Cancel SEMUA at jobs?"]):
                out = run_cmd(
                    ["bash", "schedule_utbk.sh", "--cancel"],
                    cwd=WORKDIR,
                    timeout=30,
                )
                lines = ["Cancel selesai."]
                if out.strip():
                    lines.extend(out.strip().splitlines()[-3:])
                app.modal_message(lines[:6], duration=3.0)
                self.refresh()
            return True

        if ch in ("x", "X"):
            job_id = app.modal_input("Nomor job (contoh: 7): ")
            if job_id.isdigit():
                out = run_cmd(["atrm", job_id], cwd=WORKDIR, timeout=10)
                lines = [f"Job #{job_id} dibatalkan."]
                if out.strip():
                    lines.extend(out.strip().splitlines()[-2:])
                app.modal_message(lines[:5], duration=2.5)
                self.refresh()
            else:
                app.modal_message(["Input tidak valid."], duration=1.5)
            return True

        return False

    def draw(self, win: Any, rows: int, cols: int) -> None:
        with self._lock:
            jobs = list(self.data.get("jobs", []))
            at_available = bool(self.data.get("at_available", False))

        safe_addstr(
            win,
            0,
            1,
            f"Jadwal at Jobs  ({len(jobs)} terjadwal)",
            cp(C_TITLE) | curses.A_BOLD,
        )
        safe_addstr(win, 1, 1, "-" * max(1, cols - 2), cp(C_DIM))

        row = 3
        if not at_available:
            safe_addstr(win, row, 2, "Perintah 'at' tidak tersedia di sistem.", cp(C_ERR))
            row += 1

        if not jobs:
            safe_addstr(win, row, 2, "Tidak ada jadwal terdaftar.", cp(C_DIM))
        else:
            for item in jobs:
                if row >= rows - 4:
                    break
                when = item["dt"].strftime("%a %b %d %H:%M:%S %Y")
                cd = format_countdown(item["dt"])
                line = f"#{item['id']:<3} {when:<24} ({cd})"
                safe_addstr(win, row, 2, line[: cols - 3])
                row += 1

        cmd_row = max(2, rows - 3)
        safe_addstr(win, cmd_row, 1, "-" * max(1, cols - 2), cp(C_DIM))
        safe_addstr(
            win,
            cmd_row + 1,
            2,
            "[S] Setup   [C] Cancel semua   [X] Cancel #",
            cp(C_MENU),
        )


class CollectScreen(Screen):
    """Run mikrotik_agent.py and stream output."""

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
            proc = self.data.get("proc")
            start = self.data.get("start")
            state = self.data.get("state", "IDLE")
            if state == "RUNNING" and proc is not None:
                if proc.poll() is None and start is not None:
                    self.data["elapsed"] = time.time() - float(start)

    def _start_collect(self, app: "App") -> None:
        with self._lock:
            proc = self.data.get("proc")
            if proc is not None and proc.poll() is None:
                self.data["lines"].append("Collect sedang berjalan...")
                self.data["lines"] = self.data["lines"][-20:]
                return

            self.data["state"] = "RUNNING"
            self.data["lines"] = []
            self.data["start"] = time.time()
            self.data["elapsed"] = 0.0
            self.data["exit_code"] = None

        try:
            proc = subprocess.Popen(
                ["python3", "mikrotik_agent.py"],
                cwd=str(WORKDIR),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
        except Exception as exc:
            with self._lock:
                self.data["state"] = "FAILED"
                self.data["lines"] = [f"Gagal start proses: {exc}"]
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
                            self.data["lines"] = lines[-20:]
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
                    lines.append(f"Reader error: {exc}")
                    self.data["lines"] = lines[-20:]
                    self.data["exit_code"] = -1
            finally:
                app._wake.set()

        threading.Thread(target=reader, daemon=True).start()

    def handle_key(self, key: int, app: "App") -> bool:
        ch = chr(key) if 0 < key < 256 else ""
        if ch in ("r", "R"):
            with self._lock:
                state = self.data.get("state", "IDLE")
            if state == "RUNNING":
                with self._lock:
                    lines = list(self.data.get("lines", []))
                    lines.append("Collect sudah berjalan.")
                    self.data["lines"] = lines[-20:]
                return True
            self._start_collect(app)
            return True
        return False

    def draw(self, win: Any, rows: int, cols: int) -> None:
        with self._lock:
            state = self.data.get("state", "IDLE")
            lines = list(self.data.get("lines", []))
            elapsed = float(self.data.get("elapsed", 0.0))
            exit_code = self.data.get("exit_code")

        safe_addstr(win, 0, 1, "Collect Data dari Router", cp(C_TITLE) | curses.A_BOLD)
        safe_addstr(win, 1, 1, "-" * max(1, cols - 2), cp(C_DIM))

        if state == "IDLE":
            safe_addstr(win, 3, 2, "Jalankan mikrotik_agent.py untuk mengambil")
            safe_addstr(win, 4, 2, "data DHCP lease dari semua router.")
            safe_addstr(win, 6, 2, "Output disimpan ke: output/")
            safe_addstr(win, 7, 2, "Log: schedule.log")
            safe_addstr(win, 9, 2, "[R] Mulai collect", cp(C_MENU) | curses.A_BOLD)
            return

        if state == "RUNNING":
            spin = SPINNER[int(time.time() * 8) % len(SPINNER)]
            safe_addstr(
                win,
                3,
                2,
                f"{spin} Running... {int(elapsed)}s",
                cp(C_WARN) | curses.A_BOLD,
            )
            view = lines[-15:]
            for idx, line in enumerate(view):
                safe_addstr(win, 5 + idx, 2, line[: cols - 3])
            return

        if state == "DONE":
            safe_addstr(
                win,
                3,
                2,
                "✓ Selesai (exit 0)",
                cp(C_OK) | curses.A_BOLD,
            )
            safe_addstr(win, 4, 2, f"Elapsed: {int(elapsed)}s", cp(C_DIM))
            view = lines[-15:]
            for idx, line in enumerate(view):
                safe_addstr(win, 6 + idx, 2, line[: cols - 3])
            safe_addstr(win, rows - 2, 2, "[R] Jalankan lagi", cp(C_MENU) | curses.A_BOLD)
            return

        safe_addstr(
            win,
            3,
            2,
            f"✗ Gagal (exit {exit_code})",
            cp(C_ERR) | curses.A_BOLD,
        )
        safe_addstr(win, 4, 2, f"Elapsed: {int(elapsed)}s", cp(C_DIM))
        view = lines[-15:]
        for idx, line in enumerate(view):
            safe_addstr(win, 6 + idx, 2, line[: cols - 3])
        safe_addstr(win, rows - 2, 2, "[R] Coba lagi", cp(C_MENU) | curses.A_BOLD)


class LaporanScreen(Screen):
    """Report list and report generation."""

    def __init__(self) -> None:
        super().__init__()
        with self._lock:
            self.data["files"] = []
            self.data["gen_state"] = "IDLE"
            self.data["gen_lines"] = []
            self.data["gen_proc"] = None
            self.data["gen_start"] = None
            self.data["gen_elapsed"] = 0.0
            self.data["gen_exit_code"] = None

    def refresh(self) -> None:
        files = sorted(
            LAPORAN_DIR.glob("*.md"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )

        with self._lock:
            self.data["files"] = files
            proc = self.data.get("gen_proc")
            state = self.data.get("gen_state")
            start = self.data.get("gen_start")
            if state == "RUNNING" and proc is not None and proc.poll() is None and start:
                self.data["gen_elapsed"] = time.time() - float(start)

    def _start_generate(self, app: "App", force: bool) -> None:
        with self._lock:
            proc = self.data.get("gen_proc")
            if proc is not None and proc.poll() is None:
                lines = list(self.data.get("gen_lines", []))
                lines.append("Generate masih berjalan...")
                self.data["gen_lines"] = lines[-20:]
                return

            self.data["gen_state"] = "RUNNING"
            self.data["gen_lines"] = []
            self.data["gen_start"] = time.time()
            self.data["gen_elapsed"] = 0.0
            self.data["gen_exit_code"] = None

        cmd = ["python3", "generate_reports.py"]
        if force:
            cmd.append("--force")

        try:
            proc = subprocess.Popen(
                cmd,
                cwd=str(WORKDIR),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
        except Exception as exc:
            with self._lock:
                self.data["gen_state"] = "FAILED"
                self.data["gen_lines"] = [f"Gagal start generate: {exc}"]
                self.data["gen_exit_code"] = -1
            app._wake.set()
            return

        with self._lock:
            self.data["gen_proc"] = proc

        def reader() -> None:
            try:
                if proc.stdout is not None:
                    for line in proc.stdout:
                        with self._lock:
                            out = list(self.data.get("gen_lines", []))
                            out.append(line.rstrip())
                            self.data["gen_lines"] = out[-20:]
                            start = self.data.get("gen_start")
                            if start is not None:
                                self.data["gen_elapsed"] = time.time() - float(start)
                        app._wake.set()

                proc.wait()
                with self._lock:
                    start = self.data.get("gen_start")
                    if start is not None:
                        self.data["gen_elapsed"] = time.time() - float(start)
                    self.data["gen_exit_code"] = proc.returncode
                    self.data["gen_state"] = (
                        "DONE" if proc.returncode == 0 else "FAILED"
                    )
            except Exception as exc:
                with self._lock:
                    self.data["gen_state"] = "FAILED"
                    out = list(self.data.get("gen_lines", []))
                    out.append(f"Reader error: {exc}")
                    self.data["gen_lines"] = out[-20:]
                    self.data["gen_exit_code"] = -1
            finally:
                app._wake.set()

        threading.Thread(target=reader, daemon=True).start()

    def handle_key(self, key: int, app: "App") -> bool:
        ch = chr(key) if 0 < key < 256 else ""
        if ch in ("g", "G"):
            with self._lock:
                state = self.data.get("gen_state", "IDLE")
            if state != "RUNNING":
                self._start_generate(app, force=True)
            return True

        if ch in ("f", "F"):
            with self._lock:
                state = self.data.get("gen_state", "IDLE")
            if state != "RUNNING":
                self._start_generate(app, force=False)
            return True

        return False

    def draw(self, win: Any, rows: int, cols: int) -> None:
        with self._lock:
            files = list(self.data.get("files", []))
            gen_state = self.data.get("gen_state", "IDLE")
            gen_lines = list(self.data.get("gen_lines", []))
            gen_elapsed = float(self.data.get("gen_elapsed", 0.0))
            gen_exit_code = self.data.get("gen_exit_code")

        safe_addstr(win, 0, 1, f"Laporan .md ({len(files)} files)", cp(C_TITLE) | curses.A_BOLD)
        safe_addstr(win, 1, 1, "-" * max(1, cols - 2), cp(C_DIM))

        row = 2
        max_list_rows = max(0, rows - 8)
        for p in files[:max_list_rows]:
            ts = dt.datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
            name_width = max(8, cols - 24)
            name = p.name
            if len(name) > name_width:
                name = name[: name_width - 3] + "..."
            safe_addstr(win, row, 2, f"{name:<{name_width}}  {ts}"[: cols - 3])
            row += 1

        cmd_row = max(2, rows - 5)
        safe_addstr(win, cmd_row, 1, "-" * max(1, cols - 2), cp(C_DIM))
        safe_addstr(
            win,
            cmd_row + 1,
            2,
            "[G] Generate --force   [F] Generate fresh",
            cp(C_MENU),
        )

        status_row = cmd_row + 2
        if gen_state == "RUNNING":
            spin = SPINNER[int(time.time() * 8) % len(SPINNER)]
            safe_addstr(
                win,
                status_row,
                2,
                f"{spin} Generating... {int(gen_elapsed)}s",
                cp(C_WARN) | curses.A_BOLD,
            )
            if gen_lines:
                safe_addstr(win, min(rows - 1, status_row + 1), 2, gen_lines[-1][: cols - 3], cp(C_DIM))
        elif gen_state == "DONE":
            safe_addstr(win, status_row, 2, "✓ Selesai", cp(C_OK) | curses.A_BOLD)
        elif gen_state == "FAILED":
            safe_addstr(
                win,
                status_row,
                2,
                f"✗ Gagal (exit {gen_exit_code})",
                cp(C_ERR) | curses.A_BOLD,
            )
            if gen_lines:
                safe_addstr(win, min(rows - 1, status_row + 1), 2, gen_lines[-1][: cols - 3], cp(C_DIM))


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
            f"Schedule Log  ({len(lines)} lines, scroll ↑↓)",
            cp(C_TITLE) | curses.A_BOLD,
        )
        safe_addstr(win, 1, 1, "-" * max(1, cols - 2), cp(C_DIM))

        visible_rows = max(0, rows - 4)
        if not lines:
            safe_addstr(win, 3, 2, "schedule.log belum ada - jobs belum dieksekusi", cp(C_DIM))
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

        ai_chunks: list[str] = []
        try:
            for event_type, content in _agent_mod.stream_agent_response(
                self._agent, self._agent_config, user_msg
            ):
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

            final = "\n".join(ai_chunks).strip()
            with self._lock:
                if final:
                    self.data["history"].append({"role": "assistant", "content": final})
                self.data["state"] = "IDLE"
                self.data["scroll"] = 999999
        except Exception as exc:
            with self._lock:
                self.data["history"].append({
                    "role": "assistant",
                    "content": f"⚠ Agent error: {exc}",
                })
                self.data["state"] = "IDLE"
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
            safe_addstr(
                win,
                input_row,
                2,
                f"{spin} Agent sedang bekerja...",
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
                "[I] Insert  [C] Hapus riwayat  [J/K] Scroll  [1-7] Menu  [7] Aktivitas",
                cp(C_MENU),
            )


class App:
    """Main TUI application."""

    def __init__(self) -> None:
        LAPORAN_DIR.mkdir(parents=True, exist_ok=True)
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        self.screens: list[Screen] = [
            DashboardScreen(),
            JadwalScreen(),
            CollectScreen(),
            LaporanScreen(),
            LogScreen(),
            AIScreen(),
            AgentActivityScreen(),
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

        if ch and ch in "1234567":
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
        hints = " [1-6] Menu  [↑↓] Nav  [Q] Keluar  [R] Refresh "
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


if __name__ == "__main__":
    import locale

    locale.setlocale(locale.LC_ALL, "")
    try:
        App().run()
    except KeyboardInterrupt:
        pass
