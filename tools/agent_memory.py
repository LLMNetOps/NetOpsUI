"""Cross-session agent memory — persists router knowledge across TUI restarts.

Stored in data/memory.db (SQLite). Agents can read/write facts that survive
between sessions: discovered IPs, recent SSH failures, router notes.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path

from langchain_core.tools import tool

_DB_PATH = Path(__file__).parent.parent / "data" / "memory.db"
_WIB = timezone(timedelta(hours=7))


def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(str(_DB_PATH), check_same_thread=False)
    c.row_factory = sqlite3.Row
    return c


def _init_db() -> None:
    with _conn() as c:
        c.executescript("""
            CREATE TABLE IF NOT EXISTS router_facts (
                router_name  TEXT NOT NULL,
                fact_type    TEXT NOT NULL,
                value        TEXT NOT NULL,
                source       TEXT DEFAULT '',
                updated_at   TEXT NOT NULL,
                PRIMARY KEY (router_name, fact_type)
            );
            CREATE TABLE IF NOT EXISTS session_notes (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                note         TEXT NOT NULL,
                tags         TEXT DEFAULT '',
                created_at   TEXT NOT NULL
            );
        """)


_init_db()


def _now() -> str:
    return datetime.now(_WIB).isoformat(timespec="seconds")


@tool
def remember_router_fact(router_name: str, fact_type: str, value: str, source: str = "") -> str:
    """
    Simpan fakta tentang router ke memory lintas sesi.
    Fakta lama dengan tipe yang sama akan ditimpa.
    Args:
        router_name: Nama router (contoh: GATE-IDREN-ITB).
        fact_type:   Jenis fakta — 'discovered_ip', 'ssh_status', 'ros_version',
                     'last_seen', 'note', 'bgp_peer_source'.
        value:       Nilai fakta (contoh: '103.78.233.5', 'OK', '7').
        source:      Asal informasi (contoh: 'NetBox primary_ip', 'BGP session GATE-IDREN-UB').
    """
    router_name = router_name.strip().upper()
    with _conn() as c:
        c.execute("""
            INSERT INTO router_facts (router_name, fact_type, value, source, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT (router_name, fact_type) DO UPDATE SET
                value=excluded.value, source=excluded.source, updated_at=excluded.updated_at
        """, (router_name, fact_type, value, source, _now()))
    return f"Memory disimpan: {router_name} [{fact_type}] = {value}"


@tool
def recall_router_facts(router_name: str) -> str:
    """
    Ambil semua fakta tersimpan tentang sebuah router dari memory lintas sesi.
    Berguna sebelum discovery — cek apakah IP sudah pernah ditemukan sebelumnya.
    Args:
        router_name: Nama router (contoh: GATE-IDREN-ITB).
    """
    router_name = router_name.strip().upper()
    with _conn() as c:
        rows = c.execute(
            "SELECT fact_type, value, source, updated_at FROM router_facts WHERE router_name=? ORDER BY fact_type",
            (router_name,)
        ).fetchall()
    if not rows:
        return f"Tidak ada memory tersimpan untuk {router_name}."
    lines = [f"Memory untuk {router_name}:"]
    for r in rows:
        src = f"  (sumber: {r['source']})" if r['source'] else ""
        lines.append(f"  [{r['fact_type']}] {r['value']}{src}  — {r['updated_at']}")
    return "\n".join(lines)


@tool
def recall_all_router_facts() -> str:
    """
    Tampilkan semua fakta router yang tersimpan di memory lintas sesi.
    Berguna untuk morning check atau audit — lihat apa yang sudah diketahui sistem.
    """
    with _conn() as c:
        rows = c.execute(
            "SELECT router_name, fact_type, value, source, updated_at FROM router_facts ORDER BY router_name, fact_type"
        ).fetchall()
    if not rows:
        return "Memory lintas sesi kosong — belum ada fakta router yang disimpan."
    lines = ["Memory router (semua):", "─" * 60]
    cur = ""
    for r in rows:
        if r["router_name"] != cur:
            cur = r["router_name"]
            lines.append(f"\n{cur}:")
        src = f" ← {r['source']}" if r['source'] else ""
        lines.append(f"  {r['fact_type']:<20} {r['value']}{src}")
    return "\n".join(lines)


@tool
def forget_router_facts(router_name: str, fact_type: str = "") -> str:
    """
    Hapus fakta router dari memory. Jika fact_type dikosongkan, hapus semua fakta router tersebut.
    Args:
        router_name: Nama router.
        fact_type:   Jenis fakta spesifik (opsional). Kosongkan untuk hapus semua.
    """
    router_name = router_name.strip().upper()
    with _conn() as c:
        if fact_type:
            c.execute("DELETE FROM router_facts WHERE router_name=? AND fact_type=?", (router_name, fact_type))
            return f"Memory dihapus: {router_name} [{fact_type}]"
        else:
            cur = c.execute("DELETE FROM router_facts WHERE router_name=?", (router_name,))
            return f"Memory dihapus: {router_name} ({cur.rowcount} fakta)"
