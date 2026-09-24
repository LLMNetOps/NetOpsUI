"""NetOpsUI management service.

Owns what NetOps Agent and Hermes have no API for: the skill library, agent
profiles/prompts, and read-only views of each backend's config files. Chat
itself never goes through here — the browser reaches the backends via nginx.
"""
from __future__ import annotations

import json
import re
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

import backends as bk
import db


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init()
    yield


app = FastAPI(title="NetOpsUI Manager", docs_url=None, redoc_url=None, lifespan=lifespan)


def _bad(msg: str, code: int = 400):
    raise HTTPException(code, msg)


def _backend(b: str) -> str:
    if b not in bk.BACKENDS:
        _bad(f"backend tidak dikenal: {b}", 404)
    return b


def _slug(s: str) -> str:
    if not bk.SLUG_RE.match(s):
        _bad("slug harus huruf kecil/angka/strip, maksimal 64 karakter")
    return s


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "backends": {b: bk.home(b).is_dir() for b in bk.BACKENDS}}


# ── read-only views of backend files ─────────────────────────────────────────

@app.get("/api/backends/{backend}/config")
def get_config(backend: str) -> dict:
    return bk.read_config(_backend(backend))


@app.get("/api/backends/{backend}/env")
def get_env(backend: str) -> dict:
    return bk.read_env_names(_backend(backend))


@app.get("/api/backends/{backend}/soul")
def get_soul(backend: str) -> dict:
    return bk.read_soul(_backend(backend))


@app.get("/api/backends/{backend}/disk-skills")
def get_disk_skills(backend: str) -> dict:
    _backend(backend)
    with db.conn() as c:
        managed = {r["path"] for r in c.execute("SELECT path FROM skill_publications WHERE backend=?", (backend,))}
    skills = bk.disk_skills(backend)
    for s in skills:
        s["managed"] = s["path"] in managed
    return {"skills": skills}


# ── skills ───────────────────────────────────────────────────────────────────

class SkillIn(BaseModel):
    slug: str
    description: str = ""
    tags: list[str] = Field(default_factory=list)
    body: str = ""


def _status(backend: str, skill: dict, pub) -> str:
    if pub is None:
        return "draft"
    disk = bk.read_text(bk.skill_path(backend, skill["slug"]))
    if disk is None:
        return "missing"
    if bk.sha(disk) != pub["content_hash"]:
        return "disk_changed"
    return "in_sync" if bk.sha(bk.render_skill(backend, skill)) == pub["content_hash"] else "db_changed"


def _with_status(c, skill: dict) -> dict:
    pubs = {r["backend"]: r for r in c.execute("SELECT * FROM skill_publications WHERE slug=?", (skill["slug"],))}
    skill["publications"] = {b: {"status": _status(b, skill, pubs.get(b)),
                                 "published_at": pubs[b]["published_at"] if b in pubs else None}
                             for b in bk.BACKENDS}
    return skill


@app.get("/api/skills")
def list_skills() -> dict:
    with db.conn() as c:
        rows = [db.skill_row(r) for r in c.execute("SELECT * FROM skills ORDER BY slug")]
        return {"skills": [_with_status(c, s) for s in rows]}


@app.get("/api/skills/{slug}")
def get_skill(slug: str) -> dict:
    with db.conn() as c:
        r = c.execute("SELECT * FROM skills WHERE slug=?", (slug,)).fetchone()
        if not r:
            _bad("skill tidak ditemukan", 404)
        return _with_status(c, db.skill_row(r))


@app.post("/api/skills", status_code=201)
def create_skill(s: SkillIn) -> dict:
    _slug(s.slug)
    with db.conn() as c:
        if c.execute("SELECT 1 FROM skills WHERE slug=?", (s.slug,)).fetchone():
            _bad("slug sudah dipakai", 409)
        c.execute("INSERT INTO skills (slug, description, tags, body) VALUES (?,?,?,?)",
                  (s.slug, s.description, json.dumps(s.tags), s.body))
    return get_skill(s.slug)


@app.put("/api/skills/{slug}")
def update_skill(slug: str, s: SkillIn) -> dict:
    if s.slug != slug:
        _bad("slug tidak bisa diubah; buat skill baru")
    with db.conn() as c:
        cur = c.execute("UPDATE skills SET description=?, tags=?, body=?, updated_at=datetime('now') WHERE slug=?",
                        (s.description, json.dumps(s.tags), s.body, slug))
        if cur.rowcount == 0:
            _bad("skill tidak ditemukan", 404)
    return get_skill(slug)


@app.delete("/api/skills/{slug}")
def delete_skill(slug: str, unpublish: bool = False) -> dict:
    """Deletes the DB record. Files already published to a backend stay in
    place unless unpublish=true — an agent may be relying on them."""
    with db.conn() as c:
        pubs = list(c.execute("SELECT backend FROM skill_publications WHERE slug=?", (slug,)))
        if unpublish:
            for p in pubs:
                bk.remove_skill(p["backend"], slug)
        if c.execute("DELETE FROM skills WHERE slug=?", (slug,)).rowcount == 0:
            _bad("skill tidak ditemukan", 404)
    return {"deleted": slug, "unpublished": [p["backend"] for p in pubs] if unpublish else []}


class PublishIn(BaseModel):
    backend: str
    force: bool = False  # overwrite even if the file on disk was changed outside NetOpsUI


@app.post("/api/skills/{slug}/publish")
def publish_skill(slug: str, req: PublishIn) -> dict:
    backend = _backend(req.backend)
    with db.conn() as c:
        r = c.execute("SELECT * FROM skills WHERE slug=?", (slug,)).fetchone()
        if not r:
            _bad("skill tidak ditemukan", 404)
        skill = db.skill_row(r)
        if not skill["description"].strip() or not skill["body"].strip():
            _bad("deskripsi dan isi skill wajib diisi sebelum dipublish")
        pub = c.execute("SELECT * FROM skill_publications WHERE slug=? AND backend=?", (slug, backend)).fetchone()
        path = bk.skill_path(backend, slug)
        existing = bk.read_text(path)
        if existing is not None and not req.force and (pub is None or bk.sha(existing) != pub["content_hash"]):
            _bad("File skill dengan nama ini sudah ada di backend dan bukan hasil publish terakhir dari NetOpsUI "
                 "(diubah di luar atau milik backend). Kirim force=true untuk menimpa.", 409)
        text = bk.render_skill(backend, skill)
        bk.write_atomic(path, text)
        rel = str(path.relative_to(bk.skills_dir(backend)))
        c.execute("""INSERT INTO skill_publications (slug, backend, path, content_hash) VALUES (?,?,?,?)
                     ON CONFLICT(slug, backend) DO UPDATE SET path=excluded.path,
                     content_hash=excluded.content_hash, published_at=datetime('now')""",
                  (slug, backend, rel, bk.sha(text)))
    return get_skill(slug)


@app.post("/api/skills/{slug}/unpublish")
def unpublish_skill(slug: str, req: PublishIn) -> dict:
    backend = _backend(req.backend)
    with db.conn() as c:
        if not c.execute("SELECT 1 FROM skill_publications WHERE slug=? AND backend=?", (slug, backend)).fetchone():
            _bad("skill ini belum dipublish ke backend tersebut", 404)
        bk.remove_skill(backend, slug)
        c.execute("DELETE FROM skill_publications WHERE slug=? AND backend=?", (slug, backend))
    return get_skill(slug)


class ImportIn(BaseModel):
    backend: str
    path: str  # relative path from disk-skills


@app.post("/api/skills/import", status_code=201)
def import_skill(req: ImportIn) -> dict:
    """Copy a skill found on a backend's disk into the DB. Not marked as
    published: the backend keeps its own file until you publish over it."""
    backend = _backend(req.backend)
    try:
        d = bk.read_disk_skill(backend, req.path)
    except FileNotFoundError:
        _bad("file skill tidak ditemukan", 404)
    except ValueError as e:
        _bad(str(e))
    slug = re.sub(r"[^a-z0-9-]+", "-", d["slug"].lower()).strip("-")[:64]
    if not bk.SLUG_RE.match(slug):
        _bad("nama skill tidak bisa dijadikan slug yang valid")
    with db.conn() as c:
        if c.execute("SELECT 1 FROM skills WHERE slug=?", (slug,)).fetchone():
            _bad(f"slug '{slug}' sudah ada di NetOpsUI", 409)
        c.execute("INSERT INTO skills (slug, description, tags, body) VALUES (?,?,?,?)",
                  (slug, d["description"], json.dumps(d["tags"]), d["body"]))
    return get_skill(slug)


# ── agent profiles (prompts) ─────────────────────────────────────────────────

class ProfileIn(BaseModel):
    slug: str
    name: str
    description: str = ""
    prompt: str = ""


@app.get("/api/profiles")
def list_profiles() -> dict:
    with db.conn() as c:
        return {"profiles": [dict(r) for r in c.execute("SELECT * FROM profiles ORDER BY name")]}


@app.get("/api/profiles/{slug}")
def get_profile(slug: str) -> dict:
    with db.conn() as c:
        r = c.execute("SELECT * FROM profiles WHERE slug=?", (slug,)).fetchone()
    if not r:
        _bad("profil tidak ditemukan", 404)
    return dict(r)


@app.post("/api/profiles", status_code=201)
def create_profile(p: ProfileIn) -> dict:
    _slug(p.slug)
    if not p.name.strip():
        _bad("nama wajib diisi")
    with db.conn() as c:
        if c.execute("SELECT 1 FROM profiles WHERE slug=?", (p.slug,)).fetchone():
            _bad("slug sudah dipakai", 409)
        c.execute("INSERT INTO profiles (slug, name, description, prompt) VALUES (?,?,?,?)",
                  (p.slug, p.name.strip(), p.description, p.prompt))
    return get_profile(p.slug)


@app.put("/api/profiles/{slug}")
def update_profile(slug: str, p: ProfileIn) -> dict:
    if p.slug != slug:
        _bad("slug tidak bisa diubah; buat profil baru")
    with db.conn() as c:
        cur = c.execute("UPDATE profiles SET name=?, description=?, prompt=?, updated_at=datetime('now') WHERE slug=?",
                        (p.name.strip(), p.description, p.prompt, slug))
        if cur.rowcount == 0:
            _bad("profil tidak ditemukan", 404)
    return get_profile(slug)


@app.delete("/api/profiles/{slug}")
def delete_profile(slug: str) -> dict:
    with db.conn() as c:
        if c.execute("DELETE FROM profiles WHERE slug=?", (slug,)).rowcount == 0:
            _bad("profil tidak ditemukan", 404)
    return {"deleted": slug}


@app.post("/api/profiles/{slug}/apply-soul")
def apply_profile_to_soul(slug: str) -> dict:
    """Publish a profile's prompt as NetOps Agent's SOUL.md (its persona file). The
    previous SOUL.md is copied to DATA_DIR/backups first. Hermes profiles are
    applied per request as `instructions` by the browser instead."""
    prof = get_profile(slug)
    if not prof["prompt"].strip():
        _bad("prompt profil kosong")
    bk.write_soul("netops", prof["prompt"].strip() + "\n", db.DATA_DIR / "backups")
    return {"applied": slug, "backend": "netops", "path": "SOUL.md"}
