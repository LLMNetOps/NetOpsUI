"""AgentLoader: load dan validasi agent definitions dari file Markdown."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml

logger = logging.getLogger(__name__)

DEFINITIONS_DIR = Path(__file__).parent / "definitions"


@dataclass
class AgentDefinition:
    name: str
    alias: str
    description: str
    model: str
    tools: list[str]
    skills: list[str]
    handoff_to: list[str]
    approval_required_tools: list[str]
    body: str
    path: Path
    # LLM tuning params (per-agent, from frontmatter)
    num_ctx: int = 8192
    num_predict: int = 2048
    context_window: int = 10
    timeout: int = 300
    # Optional chat fallback prompt (supervisor only)
    chat_prompt: str = ""
    # Optional per-agent Ollama host (overrides OLLAMA_BASE_URL env var)
    ollama_host: str = ""
    # Enable think/reasoning mode (qwen3.5 and compatible models only)
    reasoning: bool = False
    # Max ReAct iterations (tool calls) before forced summary
    max_iters: int = 20
    # Set False di frontmatter untuk nonaktifkan agent tanpa hapus file
    enabled: bool = True


def _parse_definition_file(path: Path) -> Optional[AgentDefinition]:
    """Parse a single agent definition Markdown file. Returns None on error."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as e:
        logger.warning("Cannot read agent definition %s: %s", path, e)
        return None

    if not text.startswith("---"):
        logger.warning("Agent definition %s missing frontmatter, skipping", path.name)
        return None

    end = text.find("---", 3)
    if end == -1:
        logger.warning("Agent definition %s has unclosed frontmatter, skipping", path.name)
        return None

    frontmatter_raw = text[3:end].strip()
    body = text[end + 3:].strip()

    try:
        fm = yaml.safe_load(frontmatter_raw) or {}
    except yaml.YAMLError as e:
        logger.warning("Agent definition %s YAML parse error: %s", path.name, e)
        return None

    name = fm.get("name", path.stem)
    if not isinstance(name, str) or not name:
        name = path.stem

    return AgentDefinition(
        name=name,
        alias=str(fm.get("alias", name)),
        description=str(fm.get("description", "")),
        model=str(fm.get("model", "")),
        tools=[str(t) for t in (fm.get("tools") or [])],
        skills=[str(s) for s in (fm.get("skills") or [])],
        handoff_to=[str(a) for a in (fm.get("handoff_to") or [])],
        approval_required_tools=[str(t) for t in (fm.get("approval_required_tools") or [])],
        body=body,
        path=path,
        num_ctx=int(fm.get("num_ctx", 8192)),
        num_predict=int(fm.get("num_predict", 2048)),
        context_window=int(fm.get("context_window", 10)),
        timeout=int(fm.get("timeout", 300)),
        chat_prompt=str(fm.get("chat_prompt", "")),
        ollama_host=str(fm.get("ollama_host", "")),
        reasoning=bool(fm.get("reasoning", False)),
        max_iters=int(fm.get("max_iters", 20)),
        enabled=bool(fm.get("enabled", True)),
    )


class AgentLoader:
    """Registry of agent definitions loaded from Markdown files."""

    def __init__(self, definitions_dir: Path = DEFINITIONS_DIR) -> None:
        self._dir = definitions_dir
        self._agents: dict[str, AgentDefinition] = {}
        self._load_all()

    # ── Loading ────────────────────────────────────────────────────────────

    def _load_all(self) -> None:
        loaded: dict[str, AgentDefinition] = {}
        for md_file in sorted(self._dir.glob("*.md")):
            defn = _parse_definition_file(md_file)
            if defn:
                if defn.name in loaded:
                    logger.warning(
                        "Duplicate agent name '%s' in %s (already from %s) — skipping",
                        defn.name, md_file.name, loaded[defn.name].path.name,
                    )
                else:
                    loaded[defn.name] = defn
        self._agents = loaded
        logger.info("AgentLoader: loaded %d agent definitions from %s", len(loaded), self._dir)

    def reload(self) -> None:
        """Re-read all definition files from disk."""
        self._load_all()

    # ── Validation ─────────────────────────────────────────────────────────

    def validate(
        self,
        tool_map: dict[str, object],
        skill_library=None,
    ) -> list[str]:
        """
        Validate all loaded definitions. Returns list of warning strings.

        Checks:
        - agent.tools entries exist in tool_map
        - agent.skills entries exist in skill_library (if provided)
        - skill.tools ⊆ agent.tools for each skill assigned to the agent
        """
        warnings: list[str] = []

        for defn in self.all(include_disabled=True):
            agent_tool_set = set(defn.tools)

            # Check tool existence
            for tool_name in defn.tools:
                if tool_name not in tool_map:
                    warnings.append(
                        f"[{defn.name}] tool '{tool_name}' not found in TOOL_MAP"
                    )

            if skill_library is None:
                continue

            # Check skill existence and tool subset constraint
            for skill_name in defn.skills:
                skill = skill_library.get_by_name(skill_name)
                if skill is None:
                    warnings.append(
                        f"[{defn.name}] skill '{skill_name}' not found in SkillLibrary"
                    )
                    continue

                missing = set(skill.tools) - agent_tool_set
                if missing:
                    warnings.append(
                        f"[{defn.name}] skill '{skill_name}' requires tools not in agent: "
                        + ", ".join(sorted(missing))
                    )

        return warnings

    # ── Query ──────────────────────────────────────────────────────────────

    def get(self, name: str) -> Optional[AgentDefinition]:
        return self._agents.get(name)

    def all(self, include_disabled: bool = False) -> list[AgentDefinition]:
        agents = list(self._agents.values())
        if include_disabled:
            return agents
        return [a for a in agents if a.enabled]

    def tool_list(self, agent_name: str) -> list[str]:
        """Return the tool name list for an agent, or [] if not found."""
        defn = self._agents.get(agent_name)
        return defn.tools if defn else []

    def skill_list(self, agent_name: str) -> list[str]:
        """Return the skill name list for an agent, or [] if not found."""
        defn = self._agents.get(agent_name)
        return defn.skills if defn else []

    def system_prompt(self, agent_name: str) -> str:
        """Return the body (system prompt) from the definition file."""
        defn = self._agents.get(agent_name)
        return defn.body if defn else ""

    def __len__(self) -> int:
        return len(self._agents)

    def __repr__(self) -> str:
        return f"AgentLoader(agents={len(self)}, dir={self._dir})"
