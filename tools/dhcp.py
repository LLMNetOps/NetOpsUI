"""Tools: DHCP lease queries dan device search."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from langchain_core.tools import tool

from tools.base import (
    validate_router, get_router_entries, get_all_routers,
    ssh_creds, ssh_get_dhcp_leases, parse_mikrotik_dhcp_output,
)


def _query_leases(entry: dict[str, Any]) -> dict[str, Any]:
    """SSH ke satu router entry dan return parsed stats. Internal helper."""
    creds = ssh_creds()
    ok, raw, err = ssh_get_dhcp_leases(
        host=entry["host"],
        username=creds["username"],
        password=creds["password"],
        dhcp_server=entry["dhcp_server"],
        port=creds["port"],
        timeout=creds["timeout"],
        ros_version=entry["ros_version"],
    )
    if not ok:
        return {**entry, "ok": False, "error": err, "leases": []}
    leases = parse_mikrotik_dhcp_output(raw)
    bound    = sum(1 for l in leases if l.is_active)
    waiting  = sum(1 for l in leases if l.is_inactive)
    disabled = sum(1 for l in leases if l.disabled)
    utbk     = sum(1 for l in leases if l.is_active and l.hostname == "utbk-os")
    return {
        **entry,
        "ok": True,
        "leases": leases,
        "bound": bound,
        "waiting": waiting,
        "disabled": disabled,
        "utbk": utbk,
        "total": len(leases),
    }


@tool
def get_dhcp_leases(router_name: str, dhcp_server: str) -> str:
    """
    Ambil data DHCP lease live dari satu DHCP server tertentu di router.
    Args:
        router_name: Nama router. Gunakan list_routers() untuk daftar valid.
        dhcp_server: Nama DHCP server (contoh: dhcp-lab-tik).
    """
    router_name = validate_router(router_name)
    entries = get_router_entries(router_name)
    valid_servers = [e["dhcp_server"] for e in entries]
    if dhcp_server not in valid_servers:
        return (
            f"DHCP server '{dhcp_server}' tidak ditemukan di {router_name}. "
            f"Server yang valid: {', '.join(valid_servers)}"
        )
    entry = next(e for e in entries if e["dhcp_server"] == dhcp_server)
    result = _query_leases(entry)
    if not result["ok"]:
        return f"Gagal ambil lease dari {router_name}/{dhcp_server}: {result['error']}"

    leases = result["leases"]
    lines = [
        f"DHCP Lease — {router_name} / {dhcp_server} ({entry['host']})",
        f"Total: {result['total']}  bound: {result['bound']}  "
        f"waiting: {result['waiting']}  disabled: {result['disabled']}  "
        f"utbk-os: {result['utbk']}",
        "",
    ]
    for l in leases[:200]:
        status = "bound" if l.is_active else ("waiting" if l.is_inactive else "disabled")
        lines.append(
            f"  {l.ip_address:<16} {l.mac_address}  {l.hostname or '-':<20} {status}"
        )
    if len(leases) > 200:
        lines.append(f"  ... ({len(leases) - 200} lease lagi tidak ditampilkan)")
    return "\n".join(lines)


@tool
def get_router_leases(router_name: str) -> str:
    """
    Ambil dan agregasi semua DHCP lease dari semua DHCP server di satu router.
    Berguna untuk router dengan banyak DHCP server (contoh: FILKOM, FK-8).
    Args:
        router_name: Nama router. Gunakan list_routers() untuk daftar valid.
    """
    router_name = validate_router(router_name)
    entries = get_router_entries(router_name)
    lines = [f"Semua DHCP server di {router_name}:"]
    total_bound = total_waiting = total_disabled = total_utbk = 0
    for entry in entries:
        result = _query_leases(entry)
        if not result["ok"]:
            lines.append(f"  {entry['dhcp_server']}: GAGAL — {result['error']}")
        else:
            lines.append(
                f"  {entry['dhcp_server']}: "
                f"bound={result['bound']} waiting={result['waiting']} "
                f"disabled={result['disabled']} utbk={result['utbk']}"
            )
            total_bound    += result["bound"]
            total_waiting  += result["waiting"]
            total_disabled += result["disabled"]
            total_utbk     += result["utbk"]
    lines.append("")
    lines.append(
        f"TOTAL: bound={total_bound} waiting={total_waiting} "
        f"disabled={total_disabled} utbk={total_utbk}"
    )
    return "\n".join(lines)


@tool
def search_device(query: str) -> str:
    """
    Cari perangkat berdasarkan IP address atau MAC address di semua router.
    Args:
        query: IP address (contoh: 10.39.0.101) atau MAC address
               (contoh: dc:a6:32:1b:2c:3d) atau sebagian MAC (contoh: dc:a6).
    """
    import re
    if re.search(r'[|;&$`\\"\']', query):
        return "Error: karakter tidak valid dalam query."
    query = query.strip()
    if not query:
        return "Error: query kosong."
    q = query.lower()

    matches: list[str] = []
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(_query_leases, entry): entry for entry in get_all_routers()}
        for future in as_completed(futures, timeout=120):
            try:
                result = future.result()
                if not result["ok"]:
                    continue
                for l in result["leases"]:
                    if q in l.ip_address.lower() or q in l.mac_address.lower().replace("-", ":"):
                        status = "bound" if l.is_active else ("waiting" if l.is_inactive else "disabled")
                        matches.append(
                            f"  {result['name']}/{result['dhcp_server']}  "
                            f"{l.ip_address:<16} {l.mac_address}  "
                            f"{l.hostname or '-':<20} {status}"
                        )
            except Exception:
                pass

    if not matches:
        return f"Perangkat '{query}' tidak ditemukan di router mana pun."
    return f"Hasil pencarian '{query}' ({len(matches)} ditemukan):\n" + "\n".join(matches)


@tool
def audit_dhcp() -> str:
    """
    Audit menyeluruh DHCP semua router: ambil data lease dari seluruh
    perangkat secara paralel. Menampilkan ringkasan status per router.
    Proses ini membutuhkan 30-90 detik.
    """
    results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(_query_leases, entry): entry for entry in get_all_routers()}
        for future in as_completed(futures, timeout=120):
            try:
                results.append(future.result())
            except Exception as e:
                entry = futures[future]
                results.append({**entry, "ok": False, "error": str(e)})

    lines = [
        f"{'Router':<14} {'Server':<22} {'Host':<16} {'Bound':>6} {'Wait':>6} {'Dis':>5} {'UTBK':>6} Status",
        "-" * 90,
    ]
    total_b = total_w = total_d = total_u = ok_count = fail_count = 0
    for r in sorted(results, key=lambda x: (x["name"], x["dhcp_server"])):
        if r["ok"]:
            lines.append(
                f"  {r['name']:<14} {r['dhcp_server']:<22} {r['host']:<16} "
                f"{r['bound']:>6} {r['waiting']:>6} {r['disabled']:>5} {r['utbk']:>6}  ✓"
            )
            total_b += r["bound"]
            total_w += r["waiting"]
            total_d += r["disabled"]
            total_u += r["utbk"]
            ok_count += 1
        else:
            lines.append(
                f"  {r['name']:<14} {r['dhcp_server']:<22} {r['host']:<16} "
                f"{'':>6} {'':>6} {'':>5} {'':>6}  ✗ {r.get('error','')[:30]}"
            )
            fail_count += 1
    lines.append("-" * 90)
    lines.append(
        f"  {'TOTAL':<14} {ok_count} OK / {fail_count} GAGAL"
        f"{'':>16} {total_b:>6} {total_w:>6} {total_d:>5} {total_u:>6}"
    )
    return "\n".join(lines)
