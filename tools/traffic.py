"""Tools: traffic statistics — TX/RX rates, top talkers, queue stats."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from langchain_core.tools import tool

from tools.base import (
    validate_router, get_router_entries, get_unique_router_entries,
    ssh_creds, ssh_run_command,
)


def _fetch(host: str, command: str, ros: int) -> tuple[bool, str, str]:
    creds = ssh_creds()
    cmd = command.strip()
    if ros == 6 and cmd.startswith("/"):
        cmd = cmd.lstrip("/").replace("/", " ")
    return ssh_run_command(
        host=host,
        username=creds["username"],
        password=creds["password"],
        command=cmd,
        port=creds["port"],
        timeout=creds["timeout"],
    )


@tool
def get_interface_traffic(router_name: str, interface: str = "") -> str:
    """
    Ambil statistik TX/RX rate realtime per interface dari router.
    Args:
        router_name: Nama router. Gunakan list_routers() untuk daftar valid.
        interface:   Nama interface spesifik (contoh: ether1, sfp1).
                     Kosongkan untuk semua interface.
    """
    router_name = validate_router(router_name)
    entry = get_router_entries(router_name)[0]

    if interface:
        cmd = f"/interface/monitor-traffic {interface} once"
    else:
        cmd = "/interface/print stats"

    ok, out, err = _fetch(entry["host"], cmd, entry["ros_version"])
    if not ok:
        return f"Gagal ambil traffic stats dari {router_name}: {err}"
    if not out.strip():
        return f"Tidak ada data traffic dari {router_name}."

    header = f"Traffic stats — {router_name} ({entry['host']})\n{'─'*60}\n"
    return header + out.strip()[:3000]


@tool
def get_traffic_summary(router_name: str) -> str:
    """
    Ringkasan statistik traffic semua interface di satu router:
    TX/RX bytes, packets, drops, dan errors.
    Args:
        router_name: Nama router. Gunakan list_routers() untuk daftar valid.
    """
    router_name = validate_router(router_name)
    entry = get_router_entries(router_name)[0]

    ok, out, err = _fetch(entry["host"], "/interface/print stats", entry["ros_version"])
    if not ok:
        return f"Gagal ambil traffic summary dari {router_name}: {err}"

    header = (
        f"Traffic Summary — {router_name} ({entry['host']})\n"
        f"{'─'*60}\n"
    )
    return header + (out.strip()[:3000] if out.strip() else "(tidak ada data)")


@tool
def get_top_talkers(router_name: str, limit: int = 10) -> str:
    """
    Ambil daftar IP dengan traffic tertinggi menggunakan firewall connection tracking.
    Berguna untuk mengidentifikasi siapa yang menggunakan bandwidth terbanyak.
    Args:
        router_name: Nama router. Gunakan list_routers() untuk daftar valid.
        limit:       Jumlah top entry yang ditampilkan (default 10, max 20).
    """
    router_name = validate_router(router_name)
    entry = get_router_entries(router_name)[0]
    limit = min(int(limit), 20)

    # Connection tracking sorted by bytes — works on both ROS v6 and v7
    cmd = f"/ip/firewall/connection/print count-only"
    ok, out, err = _fetch(entry["host"], cmd, entry["ros_version"])
    conn_count = out.strip() if ok else "?"

    cmd2 = f"/ip/firewall/connection/print"
    ok2, out2, err2 = _fetch(entry["host"], cmd2, entry["ros_version"])

    if not ok2 or not out2.strip():
        return (
            f"Connection tracking — {router_name} ({entry['host']})\n"
            f"Total connections: {conn_count}\n"
            f"Detail: {'tidak tersedia — ' + err2 if not ok2 else 'tidak ada data'}"
        )

    lines_raw = out2.strip().split("\n")
    # Show first `limit` lines
    preview = "\n".join(lines_raw[:limit * 3])  # each entry ~3 lines
    header = (
        f"Connection Tracking — {router_name} ({entry['host']})\n"
        f"Total connections: {conn_count}\n"
        f"{'─'*60}\n"
    )
    return header + preview[:2500]


@tool
def get_queue_stats(router_name: str) -> str:
    """
    Ambil statistik queue (simple queue dan queue tree): drop count dan bytes.
    Berguna untuk cek apakah ada queue yang sering drop — indikasi link overload.
    Args:
        router_name: Nama router. Gunakan list_routers() untuk daftar valid.
    """
    router_name = validate_router(router_name)
    entry = get_router_entries(router_name)[0]

    results = []

    # Simple queues
    ok, out, _ = _fetch(entry["host"], "/queue/simple/print stats", entry["ros_version"])
    if ok and out.strip():
        results.append("=== Simple Queues ===\n" + out.strip()[:1500])
    elif ok:
        results.append("=== Simple Queues: (tidak ada) ===")

    # Queue tree
    ok2, out2, _ = _fetch(entry["host"], "/queue/tree/print stats", entry["ros_version"])
    if ok2 and out2.strip():
        results.append("=== Queue Tree ===\n" + out2.strip()[:1500])
    elif ok2:
        results.append("=== Queue Tree: (tidak ada) ===")

    if not results:
        return f"Gagal ambil queue stats dari {router_name}."

    header = f"Queue Stats — {router_name} ({entry['host']})\n{'─'*60}\n"
    return header + "\n\n".join(results)


@tool
def get_traffic_all(metric: str = "stats") -> str:
    """
    Ambil statistik traffic dari SEMUA router secara paralel.
    Args:
        metric: Jenis metrik — 'stats' (default, TX/RX bytes/packets),
                'queues' (drop stats), atau 'connections' (connection count).
    """
    valid = {"stats", "queues", "connections"}
    if metric not in valid:
        return f"metric tidak valid. Pilih dari: {', '.join(valid)}"

    cmd_map = {
        "stats":       "/interface/print stats",
        "queues":      "/queue/simple/print stats",
        "connections": "/ip/firewall/connection/print count-only",
    }
    cmd = cmd_map[metric]

    def _check_one(entry: dict[str, Any]) -> dict[str, Any]:
        ok, out, err = _fetch(entry["host"], cmd, entry["ros_version"])
        return {
            "name": entry["name"], "host": entry["host"],
            "ok": ok,
            "out": out.strip() if ok else "",
            "err": err if not ok else "",
        }

    unique = get_unique_router_entries()

    results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(_check_one, e): e for e in unique}
        for future in as_completed(futures, timeout=120):
            try:
                results.append(future.result())
            except Exception as exc:
                entry = futures[future]
                results.append({"name": entry["name"], "host": entry["host"],
                                 "ok": False, "out": "", "err": str(exc)})

    results.sort(key=lambda x: x["name"])
    ok_count   = sum(1 for r in results if r["ok"] and r["out"])
    fail_count = sum(1 for r in results if not r["ok"])

    lines = [
        f"Traffic `{metric}` — semua router ({len(results)} router)\n",
        f"Ringkasan: {ok_count} ada data, {fail_count} gagal\n",
        "─" * 60,
    ]
    for r in results:
        lines.append(f"\n[{r['name']}] ({r['host']})")
        if not r["ok"]:
            lines.append(f"  ✗ GAGAL: {r['err'][:80]}")
        elif not r["out"]:
            lines.append("  (tidak ada data)")
        else:
            preview = r["out"][:200]
            if len(r["out"]) > 200:
                preview += f"  ...[+{len(r['out'])-200} karakter]"
            lines.append(preview)
    return "\n".join(lines)
