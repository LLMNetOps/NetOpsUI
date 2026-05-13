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
    return _safe_call(_ssh_run_command, *a, **kw)


def ssh_get_dhcp_leases(*a: Any, **kw: Any) -> tuple[bool, str, str]:
    """ssh_get_dhcp_leases dengan exception safety."""
    return _safe_call(_ssh_get_dhcp_leases, *a, **kw)


# ── Config ────────────────────────────────────────────────────────────────────

_SSH_CONFIG: dict[str, Any] = {}
_ROUTERS: list[dict[str, Any]] = []
VALID_ROUTER_NAMES: frozenset[str] = frozenset()
_NAME_TO_ENTRIES: dict[str, list[dict[str, Any]]] = {}


def load_config() -> None:
    """Muat config.yaml dan populate global router registry."""
    global _SSH_CONFIG, _ROUTERS, VALID_ROUTER_NAMES, _NAME_TO_ENTRIES
    try:
        with open(CONFIG_FILE, encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
        _SSH_CONFIG = {
            "username": cfg["ssh"]["username"],
            "password": cfg["ssh"]["password"],
            "timeout": int(cfg["ssh"].get("timeout", 15)),
            "port": int(cfg["ssh"].get("port", 22)),
        }
        dhcp_flat: list[dict[str, Any]] = []
        name_to_entries: dict[str, list[dict[str, Any]]] = {}
        for r in cfg.get("routers", []):
            base_entry = {
                "name": r["name"],
                "host": r["host"],
                "ros_version": int(r.get("ros_version", 7)),
                "role": str(r.get("role", "backbone")),
            }
            dhcp_servers = r.get("dhcp_servers", [])
            if dhcp_servers:
                for srv in dhcp_servers:
                    entry = {**base_entry, "dhcp_server": srv}
                    dhcp_flat.append(entry)
                    name_to_entries.setdefault(r["name"], []).append(entry)
            else:
                # Router tanpa DHCP server — tetap terdaftar untuk non-DHCP tools
                entry = {**base_entry, "dhcp_server": None}
                name_to_entries.setdefault(r["name"], []).append(entry)
        _ROUTERS = dhcp_flat          # hanya entries dengan dhcp_server nyata
        _NAME_TO_ENTRIES = name_to_entries
        VALID_ROUTER_NAMES = frozenset(_NAME_TO_ENTRIES.keys())
    except FileNotFoundError:
        print(f"[base] config.yaml tidak ditemukan: {CONFIG_FILE}", file=sys.stderr)
    except Exception as exc:
        print(f"[base] Config load error: {exc}", file=sys.stderr)


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
    """Return SSH credentials dari config."""
    return {
        "username": _SSH_CONFIG.get("username", ""),
        "password": _SSH_CONFIG.get("password", ""),
        "port": _SSH_CONFIG.get("port", 22),
        "timeout": _SSH_CONFIG.get("timeout", 15),
    }


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
