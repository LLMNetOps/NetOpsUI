"""Tool: baca log router MikroTik."""

from __future__ import annotations

import re

from langchain_core.tools import tool

from tools.base import validate_router, get_router_entries, ssh_creds, ssh_run_command


@tool
def get_router_log(router_name: str, topic: str = "", lines: int = 30) -> str:
    """
    Baca log sistem dari router MikroTik via SSH.
    Berguna untuk melihat pesan error, DHCP events, dan aktivitas sistem.
    Args:
        router_name: Nama router. Gunakan list_routers() untuk daftar valid.
        topic: Filter topic log (opsional). Contoh: 'dhcp', 'system',
               'firewall', 'error', 'warning', 'ospf'. Kosongkan untuk semua.
        lines: Jumlah baris log (default 30, maksimal 100).
    """
    router_name = validate_router(router_name)
    entry = get_router_entries(router_name)[0]
    creds = ssh_creds()

    n = max(1, min(int(lines), 100))
    base_cmd = "/log/print" if entry["ros_version"] == 7 else "log print"

    if topic.strip():
        safe_topic = re.sub(r'[^a-zA-Z0-9\-]', '', topic.strip())
        cmd = f'{base_cmd} where topics~"{safe_topic}"' if safe_topic else base_cmd
    else:
        cmd = base_cmd

    ok, out, err = ssh_run_command(
        host=entry["host"],
        username=creds["username"],
        password=creds["password"],
        command=cmd,
        port=creds["port"],
        timeout=creds["timeout"],
    )
    if not ok:
        return f"Gagal ambil log dari {router_name} ({entry['host']}): {err}"
    if not out.strip():
        topic_info = f" (topic: {topic})" if topic.strip() else ""
        return f"Tidak ada log ditemukan di {router_name}{topic_info}."

    log_lines = out.strip().splitlines()
    total = len(log_lines)
    view = log_lines[-n:]
    header = (
        f"Log {router_name} ({entry['host']})"
        + (f" — topic: {topic}" if topic.strip() else "")
        + f"\nMenunjukkan {len(view)} dari {total} baris:\n"
    )
    return header + "\n".join(view)
