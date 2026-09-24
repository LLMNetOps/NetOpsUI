"""Filesystem access to the two agent backends' home directories.

Everything here is deliberately narrow: skills are read/written only as
<skills_dir>/<slug>/SKILL.md, config.yaml is only ever returned with secrets
masked, and .env is only ever returned as variable *names*.
"""
from __future__ import annotations

import hashlib
import os
import re
import shutil
import time
from pathlib import Path

import yaml

BACKENDS = ("netops", "hermes")

# Env var naming each backend's home directory (mounted into the container).
_HOME_ENV = {"netops": "NETOPS_AGENT_HOME", "hermes": "HERMES_HOME"}

SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
_SECRET_KEY_RE = re.compile(r"(key|token|secret|passw|credential|auth)", re.I)
_ENV_REF_RE = re.compile(r"^\$\{[^}]+\}$")


def home(backend: str) -> Path:
    if backend not in BACKENDS:
        raise ValueError(f"backend tidak dikenal: {backend}")
    return Path(os.environ.get(_HOME_ENV[backend], f"/data/{backend}"))


def skills_dir(backend: str) -> Path:
    return home(backend) / "skills"


# Hermes groups skills in category folders; ours go under this one so they are
# recognizable and never collide with Hermes' own.
HERMES_CATEGORY = "netopsui"


def skill_path(backend: str, slug: str) -> Path:
    if not SLUG_RE.match(slug):
        raise ValueError("slug harus huruf kecil/angka/strip, maksimal 64 karakter")
    root = skills_dir(backend)
    p = root / HERMES_CATEGORY / slug / "SKILL.md" if backend == "hermes" else root / slug / "SKILL.md"
    if root.resolve() not in p.resolve().parents:
        raise ValueError("path di luar folder skills")
    return p


def sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


# ── SKILL.md rendering / parsing ─────────────────────────────────────────────

def render_skill(backend: str, skill: dict) -> str:
    tags = list(skill.get("tags") or [])
    if backend == "netops":
        # `metadata.palapa` is the namespace of the underlying palapa-agent's
        # SKILL.md schema (it uses it for auto_extracted); keep it as its parser expects.
        meta = {"name": skill["slug"], "description": skill["description"], "tags": tags,
                "metadata": {"palapa": {"managed_by": "netopsui"}}}
    else:
        meta = {"name": skill["slug"], "description": skill["description"], "version": "1.0.0",
                "metadata": {"hermes": {"tags": tags}, "netopsui": {"managed": True}}}
    front = yaml.safe_dump(meta, sort_keys=False, allow_unicode=True).strip()
    return f"---\n{front}\n---\n\n{skill['body'].strip()}\n"


def parse_skill(text: str) -> dict:
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", text, re.S)
    meta, body = ({}, text) if not m else (yaml.safe_load(m.group(1)) or {}, m.group(2))
    tags = meta.get("tags") or (meta.get("metadata") or {}).get("hermes", {}).get("tags") or []
    return {
        "name": str(meta.get("name") or ""),
        "description": str(meta.get("description") or ""),
        "tags": [str(t) for t in tags] if isinstance(tags, list) else [],
        "body": body.strip(),
    }


def read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None


def write_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def remove_skill(backend: str, slug: str) -> bool:
    p = skill_path(backend, slug)
    if not p.exists():
        return False
    p.unlink()
    try:
        p.parent.rmdir()  # only succeeds when the folder is now empty
    except OSError:
        pass
    return True


def disk_skills(backend: str) -> list[dict]:
    root = skills_dir(backend)
    out = []
    if not root.is_dir():
        return out
    for f in sorted(root.rglob("SKILL.md")):
        text = read_text(f)
        if text is None:
            continue
        info = parse_skill(text)
        rel = f.relative_to(root)
        out.append({
            "path": str(rel),
            "slug": f.parent.name,
            "category": str(rel.parent.parent) if len(rel.parts) > 2 else "",
            "name": info["name"] or f.parent.name,
            "description": info["description"],
            "tags": info["tags"],
            "hash": sha(text),
        })
    return out


def read_disk_skill(backend: str, rel_path: str) -> dict:
    root = skills_dir(backend).resolve()
    f = (root / rel_path).resolve()
    if root not in f.parents or f.name != "SKILL.md":
        raise ValueError("path tidak valid")
    text = read_text(f)
    if text is None:
        raise FileNotFoundError(rel_path)
    return {**parse_skill(text), "slug": f.parent.name, "path": rel_path}


# ── config.yaml / .env / SOUL.md (read-only views) ───────────────────────────

def _mask(node):
    if isinstance(node, dict):
        out = {}
        for k, v in node.items():
            if isinstance(v, str) and _SECRET_KEY_RE.search(str(k)) and not str(k).endswith("_env") \
                    and v and not _ENV_REF_RE.match(v):
                out[k] = "***"
            else:
                out[k] = _mask(v)
        return out
    if isinstance(node, list):
        return [_mask(v) for v in node]
    return node


def read_config(backend: str) -> dict:
    """config.yaml re-serialized with secret-looking values masked. Values that
    are `${ENV_VAR}` references stay visible — they are pointers, not secrets."""
    text = read_text(home(backend) / "config.yaml")
    if text is None:
        return {"exists": False, "yaml": ""}
    data = yaml.safe_load(text)
    masked = yaml.safe_dump(_mask(data), sort_keys=False, allow_unicode=True, width=100)
    return {"exists": True, "yaml": masked}


def read_env_names(backend: str) -> dict:
    """Variable names only. Values never leave this process."""
    text = read_text(home(backend) / ".env")
    if text is None:
        return {"exists": False, "vars": []}
    out = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, _, value = line.removeprefix("export ").partition("=")
        out.append({"name": name.strip(), "set": bool(value.strip().strip("'\""))})
    return {"exists": True, "vars": sorted(out, key=lambda v: v["name"])}


def read_soul(backend: str) -> dict:
    text = read_text(home(backend) / "SOUL.md")
    return {"exists": text is not None, "content": text or ""}


def write_soul(backend: str, content: str, backup_dir: Path) -> None:
    """Written in place (not via rename) because SOUL.md may be a single-file
    bind mount, which cannot be replaced atomically."""
    p = home(backend) / "SOUL.md"
    old = read_text(p)
    if old is not None:
        backup_dir.mkdir(parents=True, exist_ok=True)
        (backup_dir / f"SOUL.{backend}.{time.strftime('%Y%m%d-%H%M%S')}.md").write_text(old, encoding="utf-8")
    p.write_text(content, encoding="utf-8")
