"""Tool: interface stats — error, drop, status per interface."""

from __future__ import annotations

from langchain_core.tools import tool

from tools.base import validate_router, get_router_entries, ssh_creds, ssh_run_command


@tool
def get_interface_stats(router_name: str) -> str:
    """
    Ambil statistik interface router: TX/RX error, drop, dan status.
    Berguna untuk mendeteksi masalah kabel, duplex mismatch, atau congestion.
    Args:
        router_name: Nama router. Gunakan list_routers() untuk daftar valid.
    """
    router_name = validate_router(router_name)
    entry = get_router_entries(router_name)[0]
    creds = ssh_creds()
    ros = entry["ros_version"]

    cmd = (
        "/interface/print stats"
        if ros == 7
        else "interface print stats"
    )
    ok, out, err = ssh_run_command(
        host=entry["host"],
        username=creds["username"],
        password=creds["password"],
        command=cmd,
        port=creds["port"],
        timeout=creds["timeout"],
    )
    if not ok:
        return f"Gagal ambil interface stats dari {router_name} ({entry['host']}): {err}"
    if not out.strip():
        return f"Tidak ada data interface di {router_name}."

    output = out.strip()
    header = f"Interface Stats — {router_name} ({entry['host']})\n{'─'*60}\n"
    if len(output) > 8000:
        output = output[:8000] + f"\n...[terpotong, total {len(out)} karakter]..."
    return header + output
