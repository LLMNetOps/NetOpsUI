"""Tools: ping dan traceroute dari router ke target."""

from __future__ import annotations

import re

from langchain_core.tools import tool

from tools.base import validate_router, get_router_entries, ssh_creds, ssh_run_command


@tool
def run_diagnostic(
    router_name: str,
    tool_name: str,
    target: str,
    count: int = 4,
) -> str:
    """
    Jalankan perintah diagnostik jaringan dari router MikroTik (ping, traceroute).
    Args:
        router_name: Nama router. Gunakan list_routers() untuk daftar valid.
        tool_name:   Nama tool diagnostik: 'traceroute', 'ping', 'flood-ping'.
        target:      IP address atau hostname tujuan.
        count:       Jumlah paket ping atau hop traceroute (default 4, maks 30).
    """
    router_name = validate_router(router_name)
    if re.search(r'[|;&$`\\"\'\s]', target):
        return "Error: karakter tidak valid dalam target address."
    if not target:
        return "Error: target address kosong."

    allowed_tools = {"traceroute", "ping", "flood-ping"}
    tool_name = tool_name.strip().lower()
    if tool_name not in allowed_tools:
        return (
            f"Tool '{tool_name}' tidak diizinkan. "
            f"Pilihan: {', '.join(sorted(allowed_tools))}"
        )

    entry = get_router_entries(router_name)[0]
    creds = ssh_creds()
    ros = entry["ros_version"]
    count = max(1, min(int(count), 30))

    if tool_name == "traceroute":
        cmd = (
            f"/tool/traceroute address={target} count={count}"
            if ros == 7 else
            f"tool traceroute {target} count={count}"
        )
    elif tool_name == "ping":
        cmd = (
            f"/ping address={target} count={count}"
            if ros == 7 else
            f"ping {target} count={count}"
        )
    else:  # flood-ping
        cmd = (
            f"/ping address={target} count={count} interval=0"
            if ros == 7 else
            f"ping {target} count={count} interval=0"
        )

    ok, out, err = ssh_run_command(
        host=entry["host"],
        username=creds["username"],
        password=creds["password"],
        command=cmd,
        port=creds["port"],
        timeout=60,  # diagnostik butuh timeout lebih panjang
    )
    if not ok:
        return (
            f"Gagal menjalankan {tool_name} di {router_name} ({entry['host']}): {err}\n"
            f"Perintah: {cmd}"
        )
    if not out.strip():
        return f"Tidak ada output dari {tool_name} ke {target} di {router_name}."

    header = (
        f"Hasil {tool_name} dari {router_name} ({entry['host']}) ke {target}\n"
        f"Perintah: {cmd}\n{'─' * 60}\n"
    )
    output = out.strip()
    if len(output) > 3000:
        output = output[:3000] + f"\n...[terpotong, total {len(out)} karakter]..."
    return header + output
