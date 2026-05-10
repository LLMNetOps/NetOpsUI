"""Tools: traffic statistics — TX/RX rates, top talkers, queue stats."""

from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from langchain_core.tools import tool

from tools.base import (
    validate_router, get_router_entries, get_unique_router_entries,
    ssh_creds, ssh_run_command,
)


def _human_bytes(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB", "PB"):
        if n < 1024:
            return f"{n:.1f} {unit}" if unit != "B" else f"{n} B"
        n /= 1024
    return f"{n:.1f} PB"


def _parse_iface_stats(raw: str) -> list[dict]:
    """Parse output /interface print stats ROS v7 → list of dicts."""
    entries = []
    comment = ""
    for line in raw.splitlines():
        if ";;;" in line:
            comment = line.split(";;;", 1)[1].strip()
            continue
        # Baris data: "  0 RS ether1   14 768 998 935"
        # Nama interface tidak punya spasi; bytes pakai spasi ribuan
        m = re.match(r'^\s*\d+\s+[A-Z]+\s+(\S+)\s+([\d ]+)\s*$', line)
        if not m:
            continue
        name = m.group(1)
        try:
            rx = int(m.group(2).replace(" ", ""))
        except ValueError:
            continue
        entries.append({"name": name, "rx": rx, "comment": comment})
        comment = ""
    return entries


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
    Ambil statistik RX bytes per interface dari router, diurutkan dari tertinggi.
    Interface dengan 0 bytes dikelompokkan terpisah di bagian bawah.
    Args:
        router_name: Nama router. Gunakan list_routers() untuk daftar valid.
        interface:   Nama interface spesifik (contoh: ether1, sfp1).
                     Kosongkan untuk semua interface aktif.
    """
    router_name = validate_router(router_name)
    entry = get_router_entries(router_name)[0]

    if interface:
        cmd = f"/interface/monitor-traffic {interface} once"
        ok, out, err = _fetch(entry["host"], cmd, entry["ros_version"])
        if not ok:
            return f"Gagal ambil traffic {interface} dari {router_name}: {err}"
        return f"Traffic {interface} — {router_name}\n{'─'*60}\n{out.strip()}"

    ok, out, err = _fetch(entry["host"], "/interface/print stats where running=yes",
                          entry["ros_version"])
    if not ok:
        return f"Gagal ambil traffic stats dari {router_name}: {err}"
    if not out.strip():
        return f"Tidak ada data traffic dari {router_name}."

    ifaces = _parse_iface_stats(out)
    if not ifaces:
        # Fallback: kembalikan raw output tanpa truncation
        return f"Traffic stats — {router_name} ({entry['host']})\n{'─'*60}\n{out.strip()}"

    active   = sorted([i for i in ifaces if i["rx"] > 0], key=lambda x: x["rx"], reverse=True)
    inactive = [i for i in ifaces if i["rx"] == 0]

    lines = [
        f"Traffic stats — {router_name} ({entry['host']})",
        f"Interface aktif: {len(active)}  |  Zero-traffic: {len(inactive)}",
        "─" * 60,
        f"{'Interface':<45} {'RX':>12}  Keterangan",
        "─" * 60,
    ]
    for i in active:
        keterangan = f"  {i['comment']}" if i["comment"] else ""
        lines.append(f"{i['name']:<45} {_human_bytes(i['rx']):>12}{keterangan}")

    if inactive:
        lines.append("")
        lines.append(f"Zero-traffic ({len(inactive)} interface):")
        lines.append("  " + ", ".join(i["name"] for i in inactive))

    return "\n".join(lines)


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
    return header + (out.strip() if out.strip() else "(tidak ada data)")


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
    preview = "\n".join(lines_raw[:limit * 3])  # each entry ~3 lines
    header = (
        f"Connection Tracking — {router_name} ({entry['host']})\n"
        f"Total connections: {conn_count}\n"
        f"{'─'*60}\n"
    )
    return header + preview


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
        results.append("=== Simple Queues ===\n" + out.strip())
    elif ok:
        results.append("=== Simple Queues: (tidak ada) ===")

    # Queue tree
    ok2, out2, _ = _fetch(entry["host"], "/queue/tree/print stats", entry["ros_version"])
    if ok2 and out2.strip():
        results.append("=== Queue Tree ===\n" + out2.strip())
    elif ok2:
        results.append("=== Queue Tree: (tidak ada) ===")

    if not results:
        return f"Gagal ambil queue stats dari {router_name}."

    header = f"Queue Stats — {router_name} ({entry['host']})\n{'─'*60}\n"
    return header + "\n\n".join(results)


@tool
def get_top_interfaces_all(limit: int = 10) -> str:
    """
    Ambil top N interface dengan RX bytes tertinggi dari SEMUA router secara paralel.
    Berguna untuk identifikasi interface paling sibuk secara global di seluruh kampus.
    Lebih akurat dari get_traffic_all untuk pencarian top-N karena data tidak dipotong.
    Args:
        limit: Jumlah interface teratas yang ditampilkan (default 10, max 30).
    """
    limit = min(int(limit), 30)

    def _check_one(entry: dict[str, Any]) -> dict[str, Any]:
        ok, out, err = _fetch(entry["host"], "/interface/print stats where running=yes",
                              entry["ros_version"])
        if not ok or not out.strip():
            return {"name": entry["name"], "host": entry["host"], "ifaces": [], "error": err}
        return {"name": entry["name"], "host": entry["host"],
                "ifaces": _parse_iface_stats(out), "error": ""}

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
                                 "ifaces": [], "error": str(exc)})

    all_ifaces = []
    for r in results:
        for iface in r["ifaces"]:
            all_ifaces.append({
                "router": r["name"],
                "iface": iface["name"],
                "rx": iface["rx"],
                "comment": iface["comment"],
            })

    if not all_ifaces:
        return "Tidak ada data interface dari router manapun."

    top = sorted(all_ifaces, key=lambda x: x["rx"], reverse=True)[:limit]
    ok_count   = sum(1 for r in results if not r["error"])
    fail_count = sum(1 for r in results if r["error"])

    lines = [
        f"Top {limit} Interface — seluruh kampus ({len(results)} router)",
        f"Berhasil: {ok_count} router  |  Gagal: {fail_count} router",
        "─" * 72,
        f"{'#':<4} {'Router':<22} {'Interface':<28} {'RX':>12}  Keterangan",
        "─" * 72,
    ]
    for i, iface in enumerate(top, 1):
        ket = f"  {iface['comment']}" if iface["comment"] else ""
        lines.append(
            f"{i:<4} {iface['router']:<22} {iface['iface']:<28} {_human_bytes(iface['rx']):>12}{ket}"
        )
    if fail_count:
        failed = [r["name"] for r in results if r["error"]]
        lines.append(f"\nRouter gagal ({fail_count}): {', '.join(failed)}")
    return "\n".join(lines)


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
            preview = r["out"][:1500]
            if len(r["out"]) > 1500:
                preview += f"  ...[+{len(r['out'])-1500} karakter]"
            lines.append(preview)
    return "\n".join(lines)
