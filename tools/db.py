"""Consolidated SQLite database for app-owned structured data.

Tables:
  routers      — router inventory (replaces config.yaml routers: section)
  threads      — chat session metadata (persistent across server restarts)
  llm_config   — global Ollama base_url/model, editable from Settings → Environment
  llm_profiles — saved LLM connection profiles; activating one syncs to llm_config

DB file: data/netops.db
Does NOT touch: data/checkpoints.db (LangGraph-owned) or data/memory.db (agent_memory.py).
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_WORKDIR = Path(__file__).parent.parent
_DB_PATH = _WORKDIR / "data" / "netops.db"
_CONFIG_FILE = _WORKDIR / "config.yaml"   # read-only reference for one-time migration
_WIB = timezone(timedelta(hours=7))


def _conn() -> sqlite3.Connection:
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(str(_DB_PATH), check_same_thread=False)
    c.row_factory = sqlite3.Row
    return c


def _now() -> str:
    return datetime.now(_WIB).isoformat(timespec="seconds")


def _init_db() -> None:
    with _conn() as c:
        c.executescript("""
            CREATE TABLE IF NOT EXISTS routers (
                name          TEXT PRIMARY KEY,
                host          TEXT NOT NULL DEFAULT '',
                ros_version   INTEGER NOT NULL DEFAULT 7,
                role          TEXT NOT NULL DEFAULT 'backbone',
                network       TEXT NOT NULL DEFAULT 'kampus',
                dhcp_servers  TEXT NOT NULL DEFAULT '[]',
                created_at    TEXT NOT NULL,
                updated_at    TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS threads (
                thread_id     TEXT PRIMARY KEY,
                title         TEXT NOT NULL DEFAULT 'New Chat',
                last_message  TEXT NOT NULL DEFAULT '',
                created_at    TEXT NOT NULL,
                updated_at    TEXT NOT NULL,
                archived      INTEGER NOT NULL DEFAULT 0
            );

            CREATE INDEX IF NOT EXISTS idx_threads_updated
                ON threads(archived, updated_at DESC);

            CREATE TABLE IF NOT EXISTS llm_config (
                id          INTEGER PRIMARY KEY CHECK (id = 1),
                base_url    TEXT NOT NULL DEFAULT '',
                model       TEXT NOT NULL DEFAULT '',
                api_key     TEXT NOT NULL DEFAULT '',
                updated_at  TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS llm_profiles (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT NOT NULL UNIQUE,
                base_url    TEXT NOT NULL DEFAULT '',
                model       TEXT NOT NULL DEFAULT '',
                api_key     TEXT NOT NULL DEFAULT '',
                is_active   INTEGER NOT NULL DEFAULT 0,
                created_at  TEXT NOT NULL,
                updated_at  TEXT NOT NULL
            );
        """)
        cols = {row[1] for row in c.execute("PRAGMA table_info(llm_config)")}
        if "api_key" not in cols:
            c.execute("ALTER TABLE llm_config ADD COLUMN api_key TEXT NOT NULL DEFAULT ''")


def _migrate_routers_from_yaml_if_empty() -> None:
    """One-time non-destructive import from config.yaml routers: block.
    Only runs when the routers table is empty. Never modifies config.yaml.
    """
    with _conn() as c:
        if c.execute("SELECT COUNT(*) FROM routers").fetchone()[0] > 0:
            return

    if not _CONFIG_FILE.exists():
        return

    try:
        import yaml
        with open(_CONFIG_FILE, encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
    except Exception as exc:
        logger.warning("[db] Could not read config.yaml for migration: %s", exc)
        return

    yaml_routers = cfg.get("routers", [])
    if not yaml_routers:
        return

    # Collapse multiple same-name entries (one per dhcp_server) into one row
    by_name: dict[str, dict[str, Any]] = {}
    for r in yaml_routers:
        n = r.get("name", "")
        if not n:
            continue
        if n not in by_name:
            by_name[n] = {
                "name": n,
                "host": r.get("host", ""),
                "ros_version": int(r.get("ros_version", 7)),
                "role": str(r.get("role", "backbone")),
                "network": str(r.get("network", "kampus")),
                "dhcp_servers": [],
            }
        srv = r.get("dhcp_servers") or []
        if isinstance(srv, list):
            by_name[n]["dhcp_servers"].extend(srv)

    now = _now()
    with _conn() as c:
        for row in by_name.values():
            c.execute(
                "INSERT OR IGNORE INTO routers "
                "(name, host, ros_version, role, network, dhcp_servers, created_at, updated_at) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (
                    row["name"], row["host"], row["ros_version"],
                    row["role"], row["network"],
                    json.dumps(row["dhcp_servers"]),
                    now, now,
                ),
            )
    logger.info("[db] Migrated %d routers from config.yaml → netops.db", len(by_name))


def _seed_llm_config_from_env_if_empty() -> None:
    """One-time seed of llm_config from OLLAMA_BASE_URL/OLLAMA_MODEL env vars.
    Only runs when the row doesn't exist yet. Never touches .env.
    """
    now = _now()
    with _conn() as c:
        c.execute(
            "INSERT OR IGNORE INTO llm_config (id, base_url, model, api_key, updated_at) "
            "VALUES (1, ?, ?, ?, ?)",
            (
                os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
                os.getenv("OLLAMA_MODEL", "qwen3.6:27b"),
                os.getenv("OLLAMA_API_KEY", ""),
                now,
            ),
        )


# ── Router CRUD ───────────────────────────────────────────────────────────────

def db_list_routers() -> list[dict[str, Any]]:
    """Return all routers as dicts with dhcp_servers as Python list."""
    with _conn() as c:
        rows = c.execute(
            "SELECT name, host, ros_version, role, network, dhcp_servers "
            "FROM routers ORDER BY name"
        ).fetchall()
    result = []
    for row in rows:
        r = dict(row)
        r["dhcp_servers"] = json.loads(r["dhcp_servers"] or "[]")
        result.append(r)
    return result


def db_get_router(name: str) -> dict[str, Any] | None:
    with _conn() as c:
        row = c.execute(
            "SELECT name, host, ros_version, role, network, dhcp_servers "
            "FROM routers WHERE name=?", (name,)
        ).fetchone()
    if not row:
        return None
    r = dict(row)
    r["dhcp_servers"] = json.loads(r["dhcp_servers"] or "[]")
    return r


def db_add_router(
    name: str,
    host: str,
    ros_version: int = 7,
    role: str = "backbone",
    network: str = "kampus",
    dhcp_servers: list[str] | None = None,
) -> None:
    now = _now()
    with _conn() as c:
        c.execute(
            "INSERT INTO routers "
            "(name, host, ros_version, role, network, dhcp_servers, created_at, updated_at) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (name, host, ros_version, role, network,
             json.dumps(dhcp_servers or []), now, now),
        )


def db_update_router_field(name: str, field: str, value: Any) -> int:
    """Update a single field on a router row. Returns rows affected."""
    allowed = {"host", "ros_version", "role", "network", "dhcp_servers"}
    if field not in allowed:
        raise ValueError(f"Field '{field}' tidak diizinkan di tabel routers.")
    if field == "dhcp_servers" and isinstance(value, list):
        value = json.dumps(value)
    with _conn() as c:
        cur = c.execute(
            f"UPDATE routers SET {field}=?, updated_at=? WHERE name=?",
            (value, _now(), name),
        )
        return cur.rowcount


def db_delete_router(name: str) -> int:
    """Delete a router by name. Returns rows deleted."""
    with _conn() as c:
        cur = c.execute("DELETE FROM routers WHERE name=?", (name,))
        return cur.rowcount


# ── Thread CRUD ───────────────────────────────────────────────────────────────

def db_create_thread(thread_id: str, title: str = "New Chat") -> None:
    now = _now()
    with _conn() as c:
        c.execute(
            "INSERT OR IGNORE INTO threads "
            "(thread_id, title, created_at, updated_at) VALUES (?,?,?,?)",
            (thread_id, title, now, now),
        )


def db_list_threads(limit: int = 50, include_archived: bool = False) -> list[dict[str, Any]]:
    archived_filter = "" if include_archived else "WHERE archived=0"
    with _conn() as c:
        rows = c.execute(
            f"SELECT thread_id, title, last_message, created_at, updated_at "
            f"FROM threads {archived_filter} ORDER BY updated_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


def db_touch_thread(thread_id: str, last_message: str | None = None) -> None:
    """Update updated_at and optionally last_message preview."""
    if last_message is not None:
        with _conn() as c:
            c.execute(
                "UPDATE threads SET updated_at=?, last_message=? WHERE thread_id=?",
                (_now(), last_message[:120], thread_id),
            )
    else:
        with _conn() as c:
            c.execute(
                "UPDATE threads SET updated_at=? WHERE thread_id=?",
                (_now(), thread_id),
            )


def db_archive_thread(thread_id: str) -> None:
    with _conn() as c:
        c.execute(
            "UPDATE threads SET archived=1, updated_at=? WHERE thread_id=?",
            (_now(), thread_id),
        )


def db_delete_thread(thread_id: str) -> None:
    """Permanently remove thread metadata. Does not touch checkpoints.db —
    see agent.delete_thread() for purging the LangGraph conversation state."""
    with _conn() as c:
        c.execute("DELETE FROM threads WHERE thread_id=?", (thread_id,))


def db_rename_thread(thread_id: str, title: str) -> None:
    """Rename only — deliberately does not touch updated_at, since a manual
    rename shouldn't bump the thread's recency ranking in the sidebar list."""
    with _conn() as c:
        c.execute("UPDATE threads SET title=? WHERE thread_id=?", (title, thread_id))


# ── LLM config (Ollama base_url/model) CRUD ─────────────────────────────────────

def db_get_llm_config() -> dict[str, Any]:
    with _conn() as c:
        row = c.execute(
            "SELECT base_url, model, api_key, updated_at FROM llm_config WHERE id=1"
        ).fetchone()
    return dict(row) if row else {"base_url": "", "model": "", "api_key": "", "updated_at": ""}


def db_set_llm_config(
    base_url: str | None = None,
    model: str | None = None,
    api_key: str | None = None,
) -> dict[str, Any]:
    """Update base_url/model/api_key (only fields passed are changed). Returns the new row."""
    now = _now()
    with _conn() as c:
        if base_url is not None:
            c.execute("UPDATE llm_config SET base_url=?, updated_at=? WHERE id=1", (base_url, now))
        if model is not None:
            c.execute("UPDATE llm_config SET model=?, updated_at=? WHERE id=1", (model, now))
        if api_key is not None:
            c.execute("UPDATE llm_config SET api_key=?, updated_at=? WHERE id=1", (api_key, now))
    return db_get_llm_config()


# ── LLM profiles CRUD ────────────────────────────────────────────────────────

def db_list_llm_profiles() -> list[dict[str, Any]]:
    with _conn() as c:
        rows = c.execute(
            "SELECT id, name, base_url, model, api_key, is_active, updated_at "
            "FROM llm_profiles ORDER BY name"
        ).fetchall()
    return [dict(r) for r in rows]


def db_add_llm_profile(
    name: str,
    base_url: str,
    model: str,
    api_key: str = "",
) -> dict[str, Any]:
    now = _now()
    with _conn() as c:
        c.execute(
            "INSERT INTO llm_profiles (name, base_url, model, api_key, is_active, created_at, updated_at) "
            "VALUES (?,?,?,?,0,?,?)",
            (name, base_url, model, api_key, now, now),
        )
        row = c.execute(
            "SELECT id, name, base_url, model, api_key, is_active, updated_at "
            "FROM llm_profiles WHERE name=?", (name,)
        ).fetchone()
    return dict(row)


def db_update_llm_profile(
    profile_id: int,
    name: str | None = None,
    base_url: str | None = None,
    model: str | None = None,
    api_key: str | None = None,
) -> dict[str, Any] | None:
    now = _now()
    with _conn() as c:
        if name is not None:
            c.execute("UPDATE llm_profiles SET name=?, updated_at=? WHERE id=?", (name, now, profile_id))
        if base_url is not None:
            c.execute("UPDATE llm_profiles SET base_url=?, updated_at=? WHERE id=?", (base_url, now, profile_id))
        if model is not None:
            c.execute("UPDATE llm_profiles SET model=?, updated_at=? WHERE id=?", (model, now, profile_id))
        if api_key is not None:
            c.execute("UPDATE llm_profiles SET api_key=?, updated_at=? WHERE id=?", (api_key, now, profile_id))
        row = c.execute(
            "SELECT id, name, base_url, model, api_key, is_active, updated_at "
            "FROM llm_profiles WHERE id=?", (profile_id,)
        ).fetchone()
    return dict(row) if row else None


def db_delete_llm_profile(profile_id: int) -> int:
    with _conn() as c:
        cur = c.execute("DELETE FROM llm_profiles WHERE id=?", (profile_id,))
        return cur.rowcount


def db_activate_llm_profile(profile_id: int) -> dict[str, Any] | None:
    """Mark profile as active, sync its values to llm_config, and clear other active flags."""
    with _conn() as c:
        row = c.execute(
            "SELECT base_url, model, api_key FROM llm_profiles WHERE id=?", (profile_id,)
        ).fetchone()
        if not row:
            return None
        now = _now()
        c.execute("UPDATE llm_profiles SET is_active=0, updated_at=? WHERE is_active=1", (now,))
        c.execute("UPDATE llm_profiles SET is_active=1, updated_at=? WHERE id=?", (now, profile_id))
        c.execute(
            "UPDATE llm_config SET base_url=?, model=?, api_key=?, updated_at=? WHERE id=1",
            (row["base_url"], row["model"], row["api_key"], now),
        )
    return db_get_llm_config()


# ── Module init ───────────────────────────────────────────────────────────────

_init_db()
_migrate_routers_from_yaml_if_empty()
_seed_llm_config_from_env_if_empty()
