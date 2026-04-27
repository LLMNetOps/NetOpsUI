"""Tool: cek reachability router via ICMP ping lokal."""

from __future__ import annotations

import re
import subprocess
from typing import Any

from langchain_core.tools import tool

from tools.base import validate_router, get_router_entries


@tool
def check_reachability(router_name: str) -> str:
    """
    Cek apakah router dapat dijangkau via ping dari host lokal.
    Args:
        router_name: Nama router (contoh: DTI, FIB, FILKOM).
                     Gunakan list_routers() untuk daftar valid.
    """
    router_name = validate_router(router_name)
    hosts = list({e["host"] for e in get_router_entries(router_name)})
    results = []
    for host in hosts:
        try:
            res = subprocess.run(
                ["ping", "-c", "1", "-W", "3", host],
                capture_output=True,
                text=True,
                timeout=5,
            )
            reachable = res.returncode == 0
            rtt = "-"
            m = re.search(r"time=([\d.]+)", res.stdout)
            if m:
                rtt = f"{m.group(1)} ms"
            results.append(
                f"{host}: {'✓ reachable' if reachable else '✗ unreachable'} (RTT: {rtt})"
            )
        except Exception as e:
            results.append(f"{host}: error — {e}")
    return f"Reachability {router_name}:\n" + "\n".join(results)
