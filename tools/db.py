"""Consolidated SQLite database for app-owned structured data.

Tables:
  routers      — router inventory (replaces config.yaml routers: section);
                 also carries an optional per-node SSH username/password override
  ssh_config   — global default SSH credentials (replaces config.yaml ssh: section)
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
                ssh_username  TEXT NOT NULL DEFAULT '',
                ssh_password  TEXT NOT NULL DEFAULT '',
                created_at    TEXT NOT NULL,
                updated_at    TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS ssh_config (
                id          INTEGER PRIMARY KEY CHECK (id = 1),
                username    TEXT NOT NULL DEFAULT '',
                password    TEXT NOT NULL DEFAULT '',
                port        INTEGER NOT NULL DEFAULT 22,
                timeout     INTEGER NOT NULL DEFAULT 15,
                updated_at  TEXT NOT NULL
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

        router_cols = {row[1] for row in c.execute("PRAGMA table_info(routers)")}
        if "ssh_username" not in router_cols:
            c.execute("ALTER TABLE routers ADD COLUMN ssh_username TEXT NOT NULL DEFAULT ''")
        if "ssh_password" not in router_cols:
            c.execute("ALTER TABLE routers ADD COLUMN ssh_password TEXT NOT NULL DEFAULT ''")


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


def _migrate_ssh_from_yaml_if_empty() -> None:
    """One-time non-destructive import of config.yaml's ssh: block into ssh_config.
    Only runs when ssh_config has no row yet. Never modifies config.yaml.

    Also backfills per-router ssh_username/ssh_password from ssh.networks overrides
    (matched by each router's `network` column), for rows that don't already have
    an override set — preserves the old per-network override behavior as a one-time
    per-node seed, after which per-node credentials are managed independently.
    """
    with _conn() as c:
        if c.execute("SELECT COUNT(*) FROM ssh_config").fetchone()[0] > 0:
            return

    ssh_cfg: dict[str, Any] = {}
    if _CONFIG_FILE.exists():
        try:
            import yaml
            with open(_CONFIG_FILE, encoding="utf-8") as f:
                cfg = yaml.safe_load(f) or {}
            ssh_cfg = cfg.get("ssh", {}) or {}
        except Exception as exc:
            logger.warning("[db] Could not read config.yaml for SSH migration: %s", exc)

    now = _now()
    with _conn() as c:
        c.execute(
            "INSERT OR IGNORE INTO ssh_config (id, username, password, port, timeout, updated_at) "
            "VALUES (1,?,?,?,?,?)",
            (
                ssh_cfg.get("username", ""), ssh_cfg.get("password", ""),
                int(ssh_cfg.get("port", 22)), int(ssh_cfg.get("timeout", 15)),
                now,
            ),
        )

        networks = ssh_cfg.get("networks", {}) or {}
        if networks:
            rows = c.execute("SELECT name, network, ssh_username FROM routers").fetchall()
            for row in rows:
                if row["ssh_username"]:
                    continue
                override = networks.get(row["network"])
                if override and override.get("username") and override.get("password"):
                    c.execute(
                        "UPDATE routers SET ssh_username=?, ssh_password=?, updated_at=? WHERE name=?",
                        (override["username"], override["password"], now, row["name"]),
                    )
    logger.info("[db] Migrated SSH config from config.yaml → netops.db")


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
            "SELECT name, host, ros_version, role, network, dhcp_servers, "
            "ssh_username, ssh_password "
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
            "SELECT name, host, ros_version, role, network, dhcp_servers, "
            "ssh_username, ssh_password "
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
    ssh_username: str = "",
    ssh_password: str = "",
) -> None:
    now = _now()
    with _conn() as c:
        c.execute(
            "INSERT INTO routers "
            "(name, host, ros_version, role, network, dhcp_servers, "
            "ssh_username, ssh_password, created_at, updated_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?)",
            (name, host, ros_version, role, network,
             json.dumps(dhcp_servers or []), ssh_username, ssh_password, now, now),
        )


def db_update_router_field(name: str, field: str, value: Any) -> int:
    """Update a single field on a router row. Returns rows affected."""
    allowed = {"host", "ros_version", "role", "network", "dhcp_servers", "ssh_username", "ssh_password"}
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


# ── SSH config (global default) CRUD ────────────────────────────────────────

def db_get_ssh_config() -> dict[str, Any]:
    with _conn() as c:
        row = c.execute(
            "SELECT username, password, port, timeout, updated_at FROM ssh_config WHERE id=1"
        ).fetchone()
    return dict(row) if row else {"username": "", "password": "", "port": 22, "timeout": 15, "updated_at": ""}


def db_set_ssh_config(
    username: str | None = None,
    password: str | None = None,
    port: int | None = None,
    timeout: int | None = None,
) -> dict[str, Any]:
    """Update username/password/port/timeout (only fields passed are changed). Returns the new row."""
    now = _now()
    with _conn() as c:
        if username is not None:
            c.execute("UPDATE ssh_config SET username=?, updated_at=? WHERE id=1", (username, now))
        if password is not None:
            c.execute("UPDATE ssh_config SET password=?, updated_at=? WHERE id=1", (password, now))
        if port is not None:
            c.execute("UPDATE ssh_config SET port=?, updated_at=? WHERE id=1", (port, now))
        if timeout is not None:
            c.execute("UPDATE ssh_config SET timeout=?, updated_at=? WHERE id=1", (timeout, now))
    return db_get_ssh_config()


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
    """Mark profile as active and sync its values to llm_config (the global fallback).

    Multiple profiles may be active at once — activating one does not deactivate
    others, since different agents can each be wired to a different active profile.
    """
    with _conn() as c:
        row = c.execute(
            "SELECT base_url, model, api_key FROM llm_profiles WHERE id=?", (profile_id,)
        ).fetchone()
        if not row:
            return None
        now = _now()
        c.execute("UPDATE llm_profiles SET is_active=1, updated_at=? WHERE id=?", (now, profile_id))
        c.execute(
            "UPDATE llm_config SET base_url=?, model=?, api_key=?, updated_at=? WHERE id=1",
            (row["base_url"], row["model"], row["api_key"], now),
        )
    return db_get_llm_config()


def db_deactivate_llm_profile(profile_id: int) -> dict[str, Any] | None:
    """Unmark profile as active. Does not touch llm_config (the last-activated fallback stays)."""
    with _conn() as c:
        now = _now()
        cur = c.execute("UPDATE llm_profiles SET is_active=0, updated_at=? WHERE id=?", (now, profile_id))
        if not cur.rowcount:
            return None
        row = c.execute(
            "SELECT id, name, base_url, model, api_key, is_active, updated_at "
            "FROM llm_profiles WHERE id=?", (profile_id,)
        ).fetchone()
    return dict(row)


# ── Module init ───────────────────────────────────────────────────────────────

_init_db()
_migrate_routers_from_yaml_if_empty()
_migrate_ssh_from_yaml_if_empty()
_seed_llm_config_from_env_if_empty()
