"""Tools: utility umum — list routers, waktu saat ini."""

from __future__ import annotations

from datetime import datetime, timezone, timedelta

from langchain_core.tools import tool

from tools.base import get_all_routers, get_router_entries, get_router_names


@tool
def list_routers() -> str:
    """
    Daftar semua router/switch yang tersedia beserta DHCP server-nya.
    Gunakan ini untuk mengetahui nama router yang valid sebelum
    memanggil tool lain. Tidak memerlukan argumen.
    """
    lines = ["Router yang tersedia:\n"]
    seen: dict[str, list[str]] = {}
    for e in get_all_routers():
        seen.setdefault(e["name"], []).append(e["dhcp_server"])
    for name in sorted(seen):
        entries = get_router_entries(name)
        host = entries[0]["host"]
        ros  = entries[0]["ros_version"]
        role = entries[0].get("role", "backbone")
        servers = ", ".join(seen[name])
        lines.append(
            f"  {name:<14} {host:<16} ROS v{ros}  role={role}  servers: {servers}"
        )
    return "\n".join(lines)


@tool
def get_current_time() -> str:
    """
    Dapatkan waktu dan tanggal saat ini (WIB, UTC+7).
    Gunakan saat ditanya jam berapa sekarang, tanggal berapa, hari apa,
    atau untuk menghitung selisih waktu dari jadwal tertentu.
    Tidak memerlukan argumen.
    """
    WIB = timezone(timedelta(hours=7))
    now = datetime.now(WIB)
    day_names = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
    month_names = [
        "Januari", "Februari", "Maret", "April", "Mei", "Juni",
        "Juli", "Agustus", "September", "Oktober", "November", "Desember",
    ]
    return (
        f"Waktu saat ini (WIB):\n"
        f"  Hari    : {day_names[now.weekday()]}\n"
        f"  Tanggal : {now.day:02d} {month_names[now.month - 1]} {now.year}\n"
        f"  Jam     : {now.strftime('%H:%M:%S')} WIB\n"
        f"  ISO     : {now.isoformat()}"
    )
