"""Shared infrastructure: config loading, SSH helpers, router validation.

Semua tools di tools/*.py mengimport dari sini. Jangan tambahkan
logic bisnis di file ini — hanya shared utilities.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

import yaml

# ── Path constants ────────────────────────────────────────────────────────────

WORKDIR = Path(__file__).parent.parent        # project root
CONFIG_FILE = WORKDIR / "config.yaml"
OUTPUT_DIR = WORKDIR / "output"
LAPORAN_DIR = WORKDIR / "laporan"
BACKUPS_DIR = WORKDIR / "backups"

# ── Environment ───────────────────────────────────────────────────────────────

def _load_dotenv() -> None:
    """Load .env ke os.environ jika ada (tanpa dependency python-dotenv)."""
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
            if key and key not in os.environ:
                os.environ[key] = val


_load_dotenv()

OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "gemma4:e4b")

# ── SSH (dari legacy/mikrotik_agent.py) ───────────────────────────────────────

_HAS_SSH = False
_LEGACY_DIR = str(Path(__file__).parent.parent / "legacy")

try:
    if _LEGACY_DIR not in sys.path:
        sys.path.insert(0, _LEGACY_DIR)
    from mikrotik_agent import (          # type: ignore[import]
        ssh_run_command as _ssh_run_command,
        ssh_get_dhcp_leases as _ssh_get_dhcp_leases,
        parse_mikrotik_dhcp_output,
    )
    _HAS_SSH = True
except ImportError:
    _HAS_SSH = False

    def _ssh_run_command(*a: Any, **kw: Any) -> tuple[bool, str, str]:  # type: ignore[misc]
        return (False, "", "legacy/mikrotik_agent.py tidak ditemukan")

    def _ssh_get_dhcp_leases(*a: Any, **kw: Any) -> tuple[bool, str, str]:  # type: ignore[misc]
        return (False, "", "legacy/mikrotik_agent.py tidak ditemukan")

    def parse_mikrotik_dhcp_output(*a: Any, **kw: Any) -> list:  # type: ignore[misc]
        return []


def _safe_call(fn, *a: Any, **kw: Any) -> tuple[bool, str, str]:
    """Panggil fungsi SSH dan tangkap semua exception menjadi (False, '', err)."""
    try:
        return fn(*a, **kw)
    except EOFError:
        return False, "", "SSH error: EOFError — koneksi terputus saat transfer data."
    except Exception as exc:
        return False, "", f"SSH error: {type(exc).__name__}: {exc}"


def ssh_run_command(*a: Any, **kw: Any) -> tuple[bool, str, str]:
    """ssh_run_command dengan exception safety (EOFError, SSHException, dll)."""
    host = kw.get("host") or (a[0] if a else "")
    if not str(host).strip():
        return False, "", "host kosong — jalankan resolve_router_host('<nama_router>') untuk auto-discover IP"
    return _safe_call(_ssh_run_command, *a, **kw)


def ssh_get_dhcp_leases(*a: Any, **kw: Any) -> tuple[bool, str, str]:
    """ssh_get_dhcp_leases dengan exception safety."""
    host = kw.get("host") or (a[0] if a else "")
    if not str(host).strip():
        return False, "", "host kosong — jalankan resolve_router_host('<nama_router>') untuk auto-discover IP"
    return _safe_call(_ssh_get_dhcp_leases, *a, **kw)


# ── Config ────────────────────────────────────────────────────────────────────

_SSH_CONFIG: dict[str, Any] = {}
_SSH_NETWORK_CREDS: dict[str, dict[str, str]] = {}   # network → {username, password}
_ROUTERS: list[dict[str, Any]] = []
VALID_ROUTER_NAMES: frozenset[str] = frozenset()
_NAME_TO_ENTRIES: dict[str, list[dict[str, Any]]] = {}


def load_config() -> None:
    """Muat SSH/NetBox dari config.yaml + router registry dari data/netops.db."""
    global _SSH_CONFIG, _SSH_NETWORK_CREDS, _ROUTERS, VALID_ROUTER_NAMES, _NAME_TO_ENTRIES
    # ── SSH + NetBox dari config.yaml ─────────────────────────────────────────
    try:
        with open(CONFIG_FILE, encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
        ssh_cfg = cfg.get("ssh", {})
        _SSH_CONFIG = {
            "username": ssh_cfg.get("username", ""),
            "password": ssh_cfg.get("password", ""),
            "timeout": int(ssh_cfg.get("timeout", 15)),
            "port": int(ssh_cfg.get("port", 22)),
        }
        _SSH_NETWORK_CREDS = {
            net: {"username": v["username"], "password": v["password"]}
            for net, v in ssh_cfg.get("networks", {}).items()
            if "username" in v and "password" in v
        }
    except FileNotFoundError:
        print(f"[base] config.yaml tidak ditemukan: {CONFIG_FILE}", file=sys.stderr)
    except Exception as exc:
        print(f"[base] config.yaml load error: {exc}", file=sys.stderr)

    # ── Router registry dari data/netops.db ───────────────────────────────────
    try:
        from tools.db import db_list_routers  # noqa: PLC0415
        db_rows = db_list_routers()
    except Exception as exc:
        print(f"[base] Router DB load error: {exc}", file=sys.stderr)
        db_rows = []

    dhcp_flat: list[dict[str, Any]] = []
    name_to_entries: dict[str, list[dict[str, Any]]] = {}
    for row in db_rows:
        base_entry = {
            "name": row["name"],
            "host": row["host"],
            "ros_version": int(row["ros_version"]),
            "role": str(row["role"]),
            "network": str(row["network"]),
        }
        servers = row.get("dhcp_servers") or []
        if servers:
            for srv in servers:
                entry = {**base_entry, "dhcp_server": srv}
                dhcp_flat.append(entry)
                name_to_entries.setdefault(row["name"], []).append(entry)
        else:
            entry = {**base_entry, "dhcp_server": None}
            name_to_entries.setdefault(row["name"], []).append(entry)

    _ROUTERS = dhcp_flat
    _NAME_TO_ENTRIES = name_to_entries
    VALID_ROUTER_NAMES = frozenset(_NAME_TO_ENTRIES.keys())


def reload_config() -> None:
    """Reload config tanpa restart — berguna saat config.yaml diubah."""
    load_config()


load_config()


# ── Router helpers ────────────────────────────────────────────────────────────

def validate_router(name: str) -> str:
    """Validasi nama router (case-insensitive) dan return nama kanonik."""
    upper = name.strip().upper()
    for valid_name in VALID_ROUTER_NAMES:
        if valid_name.upper() == upper:
            return valid_name
    valid = ", ".join(sorted(VALID_ROUTER_NAMES))
    raise ValueError(f"Router '{name}' tidak dikenal. Pilihan valid: {valid}")


def ssh_creds() -> dict[str, Any]:
    """Return global SSH credentials dari config (fallback/default)."""
    return {
        "username": _SSH_CONFIG.get("username", ""),
        "password": _SSH_CONFIG.get("password", ""),
        "port": _SSH_CONFIG.get("port", 22),
        "timeout": _SSH_CONFIG.get("timeout", 15),
    }


def ssh_creds_for(entry: dict[str, Any]) -> dict[str, Any]:
    """Return SSH credentials untuk satu router entry.
    Override username+password dari ssh.networks jika network cocok,
    port+timeout selalu dari global ssh config.
    """
    base = ssh_creds()
    network = entry.get("network", "kampus")
    override = _SSH_NETWORK_CREDS.get(network, {})
    if override:
        base["username"] = override["username"]
        base["password"] = override["password"]
    return base


def get_router_entries(router_name: str) -> list[dict[str, Any]]:
    """Return semua DHCP server entries untuk satu router."""
    return _NAME_TO_ENTRIES.get(router_name, [])


def get_all_routers() -> list[dict[str, Any]]:
    """Return flat list router entries dengan DHCP server (satu entry per DHCP server).
    Gunakan untuk operasi DHCP. Router tanpa dhcp_servers tidak termasuk."""
    return list(_ROUTERS)


def get_unique_router_entries() -> list[dict[str, Any]]:
    """Return satu entry per router (termasuk router tanpa DHCP server).
    Gunakan untuk operasi non-DHCP (traffic, config, reachability bulk)."""
    return sorted(
        (entries[0] for entries in _NAME_TO_ENTRIES.values()),
        key=lambda e: e["name"],
    )


def get_router_names() -> list[str]:
    """Return sorted list nama router yang valid."""
    return sorted(VALID_ROUTER_NAMES)


def update_router_host(router_name: str, host: str) -> None:
    """Update host in-memory untuk semua entries router tertentu. Tidak ubah config.yaml."""
    for entry in _NAME_TO_ENTRIES.get(router_name, []):
        entry["host"] = host
    for entry in _ROUTERS:
        if entry["name"] == router_name:
            entry["host"] = host


def ssh_error_hint(err: str) -> str:
    """Terjemahkan pesan error SSH menjadi diagnosis yang actionable."""
    if "Error reading SSH protocol banner" in err:
        return (
            f"{err} — Port 22 terbuka (TCP) tetapi SSH handshake gagal. "
            "Kemungkinan SSH ACL router membatasi akses dari sumber IP ini. "
            "Gunakan check_ssh_access untuk diagnosis lebih detail."
        )
    if "timed out" in err.lower() or "Connection timed out" in err:
        return f"{err} — Firewall kemungkinan memblokir port 22 (DROP)."
    if "Connection refused" in err.lower():
        return f"{err} — SSH service tidak berjalan atau port 22 di-block (REJECT)."
    if "Network is unreachable" in err or "No route to host" in err:
        return f"{err} — Tidak ada rute ke host, masalah routing atau link down."
    if "Authentication failed" in err:
        return f"{err} — Kredensial SSH salah (username/password)."
    return err


def get_progress_writer(source: str):
    """Return a callable emit(content, event_type='tool_result') that pushes a
    live progress line to the UI via LangGraph's custom stream writer, or a
    no-op outside a streaming context.

    For multi-router tools that fan out over ThreadPoolExecutor (audit_*,
    get_*_all): a single tool call can take minutes with zero visibility to
    the operator otherwise. Call this once in the calling thread (e.g. right
    before/inside the as_completed() loop, which runs on the caller's thread)
    so each per-router result can be surfaced as it lands.
    """
    try:
        from langgraph.config import get_stream_writer
        writer = get_stream_writer()
    except Exception:
        return lambda *_a, **_kw: None

    def emit(content: str, event_type: str = "tool_result") -> None:
        writer({"source": source, "event_type": event_type, "content": content})

    return emit
