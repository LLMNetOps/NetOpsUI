"""Tool: system resource router — CPU, RAM, uptime."""

from __future__ import annotations

from langchain_core.tools import tool

from tools.base import validate_router, get_router_entries, ssh_creds, ssh_creds_for, ssh_run_command, ssh_error_hint


@tool
def get_system_info(router_name: str) -> str:
    """
    Ambil informasi sistem router: CPU, memori, uptime, versi RouterOS.
    Args:
        router_name: Nama router. Gunakan list_routers() untuk daftar valid.
    """
    router_name = validate_router(router_name)
    entry = get_router_entries(router_name)[0]
    creds = ssh_creds_for(entry)
    cmd = "/system/resource/print" if entry["ros_version"] == 7 else "system resource print"
    ok, out, err = ssh_run_command(
        host=entry["host"],
        username=creds["username"],
        password=creds["password"],
        command=cmd,
        port=creds["port"],
        timeout=creds["timeout"],
    )
    if not ok:
        return f"Gagal terhubung ke {router_name} ({entry['host']}): {ssh_error_hint(err)}"
    return f"System info {router_name} ({entry['host']}):\n{out.strip()}"
