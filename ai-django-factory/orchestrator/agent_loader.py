"""
agent_loader.py
---------------
Reads agent definition markdown files from the ``agents/`` directory.
Each file has a YAML-like frontmatter block followed by the agent's
system prompt and task description.

Expected markdown structure::

    ---
    name: Product Manager
    role: Senior Product Manager
    model: opus
    temperature: 0.8
    inputs:
      - project_description
    outputs:
      - product_requirements.md
      - user_stories.md
    ---

    ## System Prompt
    You are an experienced product manager ...

    ## Task
    Define the product requirements for the project.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

import yaml

from logs.logger import get_logger

logger = get_logger("agent_loader")

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_SECTION_RE = re.compile(r"^##\s+(.+?)$(.*?)(?=^##\s|\Z)", re.MULTILINE | re.DOTALL)


class AgentLoader:
    """
    Loads and caches agent definitions from markdown files.

    Parameters
    ----------
    agents_dir:
        Path to the directory containing ``*.md`` agent files.
    """

    def __init__(self, agents_dir: Path) -> None:
        self.agents_dir = Path(agents_dir)
        self._cache: dict[str, dict] = {}

    def load(self, agent_name: str) -> Optional[dict]:
        """
        Load an agent definition by name (snake_case filename without extension).

        Returns ``None`` if the file does not exist.
        """
        if agent_name in self._cache:
            return self._cache[agent_name]

        file_path = self.agents_dir / f"{agent_name}.md"
        if not file_path.exists():
            logger.warning("Agent file not found: %s", file_path)
            return None

        agent = self._parse(file_path)
        self._cache[agent_name] = agent
        return agent

    def list_agents(self) -> list[str]:
        """Return all available agent names (without extension)."""
        return [p.stem for p in self.agents_dir.glob("*.md")]

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _parse(self, path: Path) -> dict:
        """Parse a markdown agent file into a dict."""
        text = path.read_text(encoding="utf-8")

        # Extract YAML frontmatter
        meta: dict = {}
        fm_match = _FRONTMATTER_RE.match(text)
        if fm_match:
            meta = yaml.safe_load(fm_match.group(1)) or {}
            body = text[fm_match.end():]
        else:
            logger.warning("No frontmatter found in %s — using defaults.", path.name)
            body = text

        # Extract ## sections from the body
        sections: dict[str, str] = {}
        for m in _SECTION_RE.finditer(body):
            title = m.group(1).strip().lower().replace(" ", "_")
            sections[title] = m.group(2).strip()

        agent = {
            "name": meta.get("name", path.stem.replace("_", " ").title()),
            "role": meta.get("role", "Software Engineer"),
            "model": meta.get("model", "sonnet"),
            "temperature": float(meta.get("temperature", 0.7)),
            "inputs": meta.get("inputs", []),
            "outputs": meta.get("outputs", []),
            "system_prompt": sections.get("system_prompt", ""),
            "task_prompt": sections.get("task", ""),
            "_path": str(path),
        }

        logger.debug("Loaded agent: %s (model=%s)", agent["name"], agent["model"])
        return agent
