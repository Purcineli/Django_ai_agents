"""
memory_manager.py
-----------------
Persistent project memory backed by markdown files.

Memory files
~~~~~~~~~~~~
* ``architecture.md``  – high-level architecture decisions
* ``database.md``      – schema, models, relationships
* ``api.md``           – API endpoints, serializers, permissions
* ``ui.md``            – frontend structure, components, styles
* ``decisions.md``     – key decisions and reasoning

The orchestrator loads these files before each agent run and updates them
after receiving the agent's response.
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from logs.logger import get_logger

logger = get_logger("memory_manager")

# Which agents update which memory files
AGENT_MEMORY_MAP: dict[str, list[str]] = {
    "product_manager":      ["decisions"],
    "business_analyst":     ["decisions"],
    "cto":                  ["architecture", "decisions"],
    "system_architect":     ["architecture"],
    "django_architect":     ["architecture"],
    "database_engineer":    ["database"],
    "api_engineer":         ["api"],
    "backend_engineer":     ["api", "architecture"],
    "frontend_engineer":    ["ui"],
    "ui_ux_designer":       ["ui"],
    "security_engineer":    ["architecture", "decisions"],
    "devops_engineer":      ["architecture"],
    "testing_engineer":     ["decisions"],
    "performance_engineer": ["decisions"],
    "refactoring_engineer": ["architecture"],
    "documentation_engineer": ["decisions"],
}

# Patterns to extract structured sections from agent output
_SECTION_PATTERNS: dict[str, list[str]] = {
    "architecture": [
        r"#+\s*Architecture.*?\n(.*?)(?=#+|\Z)",
        r"#+\s*System Design.*?\n(.*?)(?=#+|\Z)",
        r"#+\s*Tech Stack.*?\n(.*?)(?=#+|\Z)",
    ],
    "database": [
        r"#+\s*Database.*?\n(.*?)(?=#+|\Z)",
        r"#+\s*Models.*?\n(.*?)(?=#+|\Z)",
        r"#+\s*Schema.*?\n(.*?)(?=#+|\Z)",
    ],
    "api": [
        r"#+\s*API.*?\n(.*?)(?=#+|\Z)",
        r"#+\s*Endpoints.*?\n(.*?)(?=#+|\Z)",
        r"#+\s*REST.*?\n(.*?)(?=#+|\Z)",
    ],
    "ui": [
        r"#+\s*Frontend.*?\n(.*?)(?=#+|\Z)",
        r"#+\s*UI.*?\n(.*?)(?=#+|\Z)",
        r"#+\s*Components.*?\n(.*?)(?=#+|\Z)",
    ],
    "decisions": [
        r"#+\s*Decision.*?\n(.*?)(?=#+|\Z)",
        r"#+\s*Recommendation.*?\n(.*?)(?=#+|\Z)",
        r"#+\s*Summary.*?\n(.*?)(?=#+|\Z)",
    ],
}


class MemoryManager:
    """
    Manages persistent project memory stored as markdown files.

    Parameters
    ----------
    memory_dir:
        Directory where memory files are stored.
    """

    def __init__(self, memory_dir: Path) -> None:
        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self._ensure_files()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def read(self, key: str) -> str:
        """Read a memory file. Returns empty string if it does not exist."""
        path = self._path(key)
        if path.exists():
            return path.read_text(encoding="utf-8")
        return ""

    def update(self, key: str, content: str) -> None:
        """Append content to a memory file with a timestamp header."""
        path = self._path(key)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        entry = f"\n\n---\n_Updated: {timestamp}_\n\n{content.strip()}\n"
        with path.open("a", encoding="utf-8") as fh:
            fh.write(entry)
        logger.debug("Memory '%s' updated (%d chars).", key, len(content))

    def update_from_agent(self, agent_name: str, response_text: str) -> None:
        """
        Extract relevant sections from an agent's response and append to the
        appropriate memory files based on ``AGENT_MEMORY_MAP``.
        """
        keys = AGENT_MEMORY_MAP.get(agent_name, ["decisions"])
        for key in keys:
            extracted = self._extract(key, response_text)
            if extracted:
                self.update(key, f"### From agent: {agent_name}\n\n{extracted}")

    def read_all(self) -> dict[str, str]:
        """Return all memory files as a dict."""
        return {key: self.read(key) for key in ["architecture", "database", "api", "ui", "decisions"]}

    def summarize(self, key: str, max_chars: int = 2000) -> str:
        """Return a truncated version of a memory file."""
        content = self.read(key)
        if len(content) <= max_chars:
            return content
        # Keep the end (most recent) content
        return f"[...truncated...]\n\n{content[-max_chars:]}"

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _path(self, key: str) -> Path:
        return self.memory_dir / f"{key}.md"

    def _ensure_files(self) -> None:
        """Create empty memory files with headers if they don't exist."""
        headers = {
            "architecture": "# Architecture Memory\n\nArchitecture decisions and system design.\n",
            "database": "# Database Memory\n\nSchema, models, and relationships.\n",
            "api": "# API Memory\n\nEndpoints, serializers, and permissions.\n",
            "ui": "# UI Memory\n\nFrontend structure, components, and styles.\n",
            "decisions": "# Decisions Memory\n\nKey decisions and reasoning.\n",
        }
        for key, header in headers.items():
            path = self._path(key)
            if not path.exists():
                path.write_text(header, encoding="utf-8")

    def _extract(self, key: str, text: str) -> str:
        """Extract relevant content for a memory key from agent output."""
        patterns = _SECTION_PATTERNS.get(key, [])
        found_parts: list[str] = []
        for pattern in patterns:
            matches = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)
            for m in matches:
                cleaned = m.strip()
                if len(cleaned) > 50:  # skip trivially short matches
                    found_parts.append(cleaned[:1500])

        if found_parts:
            return "\n\n".join(found_parts[:2])  # max 2 sections per update

        # Fallback: take first 800 chars of the response
        return text[:800].strip()
