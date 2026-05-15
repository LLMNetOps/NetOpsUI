"""SkillLibrary: load, index, dan hot-reload skill Markdown files."""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml

logger = logging.getLogger(__name__)

SKILLS_DIR = Path(__file__).parent


@dataclass
class Skill:
    name: str
    domain: str
    triggers: list[str]
    tools: list[str]
    approval_required: bool
    enabled: bool
    body: str
    path: Path

    def summary(self) -> dict:
        return {
            "name": self.name,
            "domain": self.domain,
            "triggers": self.triggers,
            "tools": self.tools,
            "approval_required": self.approval_required,
            "enabled": self.enabled,
        }


def _parse_skill_file(path: Path) -> Optional[Skill]:
    """Parse a single skill Markdown file. Returns None on error."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as e:
        logger.warning("Cannot read skill %s: %s", path, e)
        return None

    if not text.startswith("---"):
        logger.warning("Skill %s missing frontmatter, skipping", path.name)
        return None

    end = text.find("---", 3)
    if end == -1:
        logger.warning("Skill %s has unclosed frontmatter, skipping", path.name)
        return None

    frontmatter_raw = text[3:end].strip()
    body = text[end + 3:].strip()

    try:
        fm = yaml.safe_load(frontmatter_raw) or {}
    except yaml.YAMLError as e:
        logger.warning("Skill %s YAML parse error: %s", path.name, e)
        return None

    name = fm.get("name", path.stem)
    if not isinstance(name, str) or not name:
        name = path.stem

    return Skill(
        name=name,
        domain=str(fm.get("domain", path.parent.name)),
        triggers=[str(t) for t in (fm.get("triggers") or [])],
        tools=[str(t) for t in (fm.get("tools") or [])],
        approval_required=bool(fm.get("approval_required", False)),
        enabled=bool(fm.get("enabled", True)),
        body=body,
        path=path,
    )


class SkillLibrary:
    """Thread-safe skill registry with optional hot-reload."""

    def __init__(self, skills_dir: Path = SKILLS_DIR) -> None:
        self._dir = skills_dir
        self._skills: dict[str, Skill] = {}
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._watcher: Optional[threading.Thread] = None
        self._load_all()

    # ── Loading ────────────────────────────────────────────────────────────

    def _load_all(self) -> None:
        loaded: dict[str, Skill] = {}
        for md_file in self._dir.rglob("*.md"):
            if "templates" in md_file.parts:
                continue
            skill = _parse_skill_file(md_file)
            if skill:
                if skill.name in loaded:
                    logger.warning(
                        "Duplicate skill name '%s' in %s (already from %s) — skipping",
                        skill.name, md_file.name, loaded[skill.name].path.name,
                    )
                else:
                    loaded[skill.name] = skill
        with self._lock:
            self._skills = loaded
        logger.info("SkillLibrary: loaded %d skills from %s", len(loaded), self._dir)

    def _reload_file(self, path: str | Path) -> None:
        path = Path(path)
        if not path.suffix == ".md":
            return
        if not path.exists():
            # file deleted — remove matching skill
            with self._lock:
                to_remove = [n for n, s in self._skills.items() if s.path == path]
                for name in to_remove:
                    del self._skills[name]
                    logger.info("SkillLibrary: removed skill '%s'", name)
            return
        skill = _parse_skill_file(path)
        if skill:
            with self._lock:
                self._skills[skill.name] = skill
            logger.info("SkillLibrary: reloaded skill '%s'", skill.name)

    # ── Hot Reload ─────────────────────────────────────────────────────────

    def start_watcher(self) -> None:
        """Start background thread that watches skills_dir for changes."""
        if self._watcher and self._watcher.is_alive():
            return
        self._stop.clear()
        self._watcher = threading.Thread(
            target=self._watch_loop, daemon=True, name="skill-watcher"
        )
        self._watcher.start()
        logger.info("SkillLibrary: file watcher started on %s", self._dir)

    def stop_watcher(self) -> None:
        self._stop.set()
        if self._watcher and self._watcher.is_alive():
            self._watcher.join(timeout=3)

    def _watch_loop(self) -> None:
        try:
            from watchfiles import watch
        except ImportError:
            logger.warning("watchfiles not installed — hot reload disabled")
            return

        for changes in watch(self._dir, stop_event=self._stop):
            for _change_type, path in changes:
                self._reload_file(path)

    # ── Query ──────────────────────────────────────────────────────────────

    def find_relevant(self, query: str, domain: Optional[str] = None) -> list[Skill]:
        """Return enabled skills whose triggers appear in query (case-insensitive)."""
        q = query.lower()
        with self._lock:
            skills = list(self._skills.values())
        result = []
        for skill in skills:
            if not skill.enabled:
                continue
            if domain and skill.domain != domain:
                continue
            if any(trigger.lower() in q for trigger in skill.triggers):
                result.append(skill)
        return result

    def get_by_name(self, name: str) -> Optional[Skill]:
        with self._lock:
            return self._skills.get(name)

    def list_enabled(self) -> list[Skill]:
        with self._lock:
            return [s for s in self._skills.values() if s.enabled]

    def inject_context(self, skills: list[Skill]) -> str:
        """Combine skill bodies into a single system-context block."""
        if not skills:
            return ""
        parts = []
        for skill in skills:
            parts.append(f"## Skill: {skill.name} (domain: {skill.domain})\n\n{skill.body}")
        return "\n\n---\n\n".join(parts)

    def __len__(self) -> int:
        with self._lock:
            return len(self._skills)

    def __repr__(self) -> str:
        return f"SkillLibrary(skills={len(self)}, dir={self._dir})"
