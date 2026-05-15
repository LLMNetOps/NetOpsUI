"""Tools: jalankan perintah read-only di router (generic command runner)."""

from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from langchain_core.tools import tool

from tools.base import (
    validate_router, get_router_entries, get_unique_router_entries,
    ssh_creds, ssh_creds_for, ssh_run_command,
)

_BLOCKED_KEYWORDS = [
    "remove", "delete", " set ", "=set", "/set",
    " add ", "=add", "/add",
    "move", "enable", "disable",
    "reset", "reboot", "shutdown", "format",
    "export sensitive", "password",
]


def _is_safe_command(command: str) -> tuple[bool, str]:
    """Return (True, "") jika aman, atau (False, keyword) jika berbahaya."""
    cmd_lower = command.lower()
    for blocked in _BLOCKED_KEYWORDS:
        if blocked in cmd_lower:
            return False, blocked.strip()
    return True, ""


@tool
def run_command(router_name: str, command: str) -> str:
    """
    Jalankan perintah MikroTik read-only di satu router.
    Gunakan untuk verifikasi atau cek spesifik yang tidak tercakup tool lain.
    Contoh: '/user/print', '/ip/address/print where interface=ether1'
    Args:
        router_name: Nama router. Gunakan list_routers() untuk daftar valid.
        command: Perintah MikroTik read-only yang akan dieksekusi.
    """
    router_name = validate_router(router_name)
    safe, blocked_kw = _is_safe_command(command)
    if not safe:
        return (
            f"Error: perintah ditolak — mengandung kata terlarang '{blocked_kw}'. "
            f"Hanya perintah read-only yang diizinkan."
        )

    entry = get_router_entries(router_name)[0]
    creds = ssh_creds_for(entry)
    ok, out, err = ssh_run_command(
        host=entry["host"],
        username=creds["username"],
        password=creds["password"],
        command=command.strip(),
        port=creds["port"],
        timeout=creds["timeout"],
    )
    if not ok:
        return f"Gagal menjalankan perintah di {router_name} ({entry['host']}): {err}"
    if not out.strip():
        return f"Perintah '{command}' tidak menghasilkan output di {router_name}."

    output = out.strip()
    header = f"Output dari {router_name} ({entry['host']}) — `{command}`\n{'─'*60}\n"
    if len(output) > 8000:
        output = output[:8000] + f"\n...[terpotong, total {len(out)} karakter]..."
    return header + output


@tool
def run_command_all(command: str) -> str:
    """
    Jalankan perintah MikroTik read-only yang SAMA di SEMUA router secara paralel.
    Jauh lebih efisien dari memanggil run_command() satu per satu.
    Contoh: '/user/print where name=netadmin', '/ip/dns/print', '/system/identity/print'
    Args:
        command: Perintah MikroTik read-only. Tool ini otomatis menyesuaikan
                 sintaks untuk ROS v6 (strip leading slash).
    """
    safe, blocked_kw = _is_safe_command(command)
    if not safe:
        return (
            f"Error: perintah ditolak — mengandung kata terlarang '{blocked_kw}'. "
            f"Hanya perintah read-only yang diizinkan."
        )

    seen_names: set[str] = set()
    unique_entries: list[dict[str, Any]] = []
    for entry in get_unique_router_entries():
        if entry["name"] not in seen_names:
            seen_names.add(entry["name"])
            unique_entries.append(entry)

    def _check_one(entry: dict[str, Any]) -> dict[str, Any]:
        creds = ssh_creds_for(entry)
        cmd = command.strip()
        if entry["ros_version"] == 6 and cmd.startswith("/"):
            cmd = cmd.lstrip("/").replace("/", " ")
        ok, out, err = ssh_run_command(
            host=entry["host"],
            username=creds["username"],
            password=creds["password"],
            command=cmd,
            port=creds["port"],
            timeout=creds["timeout"],
        )
        return {
            "name": entry["name"],
            "host": entry["host"],
            "ok": ok,
            "out": out.strip() if ok else "",
            "err": err if not ok else "",
        }

    results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(_check_one, e): e for e in unique_entries}
        for future in as_completed(futures, timeout=120):
            try:
                results.append(future.result())
            except Exception as exc:
                entry = futures[future]
                results.append({
                    "name": entry["name"], "host": entry["host"],
                    "ok": False, "out": "", "err": str(exc),
                })

    results.sort(key=lambda x: x["name"])
    ok_count    = sum(1 for r in results if r["ok"] and r["out"])
    empty_count = sum(1 for r in results if r["ok"] and not r["out"])
    fail_count  = sum(1 for r in results if not r["ok"])

    lines = [
        f"Hasil `{command}` di semua router ({len(results)} router):\n",
        f"Ringkasan: {ok_count} ada output, {empty_count} output kosong, {fail_count} gagal\n",
        "─" * 60,
    ]
    for r in results:
        lines.append(f"\n[{r['name']}] ({r['host']})")
        if not r["ok"]:
            lines.append(f"  ✗ GAGAL: {r['err'][:80]}")
        elif not r["out"]:
            lines.append("  (tidak ada output / tidak ditemukan)")
        else:
            preview = r["out"][:2000]
            if len(r["out"]) > 2000:
                preview += f"  ...[+{len(r['out'])-2000} karakter]"
            lines.append(preview)
    return "\n".join(lines)
