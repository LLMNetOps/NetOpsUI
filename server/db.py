"""SQLite store: source of truth for skills and agent profiles managed in NetOpsUI."""
from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

DATA_DIR = Path(os.environ.get("DATA_DIR", "/data/netopsui"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS skills (
  slug        TEXT PRIMARY KEY,
  description TEXT NOT NULL DEFAULT '',
  tags        TEXT NOT NULL DEFAULT '[]',
  body        TEXT NOT NULL DEFAULT '',
  created_at  TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS skill_publications (
  slug         TEXT NOT NULL REFERENCES skills(slug) ON DELETE CASCADE,
  backend      TEXT NOT NULL,
  path         TEXT NOT NULL,
  content_hash TEXT NOT NULL,
  published_at TEXT NOT NULL DEFAULT (datetime('now')),
  PRIMARY KEY (slug, backend)
);
CREATE TABLE IF NOT EXISTS profiles (
  slug        TEXT PRIMARY KEY,
  name        TEXT NOT NULL,
  description TEXT NOT NULL DEFAULT '',
  prompt      TEXT NOT NULL DEFAULT '',
  created_at  TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


def db_path() -> Path:
    return DATA_DIR / "netopsui.db"


@contextmanager
def conn():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(db_path(), timeout=10)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys = ON")
    try:
        yield c
        c.commit()
    finally:
        c.close()


def init() -> None:
    with conn() as c:
        c.executescript(SCHEMA)
        # The backend was called 'palapa' before the rename to NetOps Agent.
        c.execute("UPDATE OR IGNORE skill_publications SET backend='netops' WHERE backend='palapa'")


def skill_row(r: sqlite3.Row) -> dict:
    d = dict(r)
    d["tags"] = json.loads(d["tags"])
    return d
