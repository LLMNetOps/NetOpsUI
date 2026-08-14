"""AgentLoader: load dan validasi agent definitions dari data/netops.db.

agents/definitions/*.md tetap ada di repo sebagai seed satu-kali (lihat
tools.db._migrate_agents_from_md_if_empty) — setelah baris pertama masuk ke
tabel agent_definitions, file-file itu tidak pernah dibaca lagi saat runtime.
Edit via UI (PUT /api/agents/{name}) menulis ke DB, bukan ke file repo.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


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
    path: Optional[Path] = None
    # LLM tuning params (per-agent, dari DB)
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
    # Set False untuk nonaktifkan agent tanpa hapus row
    enabled: bool = True


class AgentLoader:
    """Registry of agent definitions loaded from data/netops.db."""

    def __init__(self) -> None:
        self._agents: dict[str, AgentDefinition] = {}
        self._load_all()

    # ── Loading ────────────────────────────────────────────────────────────

    def _load_all(self) -> None:
        from tools.db import db_list_agents  # noqa: PLC0415

        loaded: dict[str, AgentDefinition] = {}
        for row in db_list_agents():
            loaded[row["name"]] = AgentDefinition(
                name=row["name"],
                alias=row["alias"] or row["name"],
                description=row["description"],
                model=row["model"],
                tools=row["tools"],
                skills=row["skills"],
                handoff_to=row["handoff_to"],
                approval_required_tools=row["approval_required_tools"],
                body=row["body"],
                num_ctx=row["num_ctx"],
                num_predict=row["num_predict"],
                context_window=row["context_window"],
                timeout=row["timeout"],
                chat_prompt=row["chat_prompt"],
                ollama_host=row["ollama_host"],
                reasoning=row["reasoning"],
                max_iters=row["max_iters"],
                enabled=row["enabled"],
            )
        self._agents = loaded
        logger.info("AgentLoader: loaded %d agent definitions from DB", len(loaded))

    def reload(self) -> None:
        """Re-read all definitions from the DB."""
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
        """Return the body (system prompt) from the definition."""
        defn = self._agents.get(agent_name)
        return defn.body if defn else ""

    def __len__(self) -> int:
        return len(self._agents)

    def __repr__(self) -> str:
        return f"AgentLoader(agents={len(self)})"
