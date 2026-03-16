"""
artifact_manager.py
-------------------
Stores and retrieves the raw text output of each agent run.

Artifacts are stored as plain ``.txt`` files in the project's artifacts
directory.  The naming convention is ``{agent_name}.txt``.

The artifact manager also maintains a lightweight index so agents can
quickly check which prior outputs are available.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from logs.logger import get_logger

logger = get_logger("artifact_manager")


class ArtifactManager:
    """
    Saves and loads agent output artifacts.

    Parameters
    ----------
    artifacts_dir:
        Directory for this project's artifacts.
    """

    def __init__(self, artifacts_dir: Path) -> None:
        self.artifacts_dir = Path(artifacts_dir)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        self._index_path = self.artifacts_dir / "_index.json"
        self._index: dict[str, dict] = self._load_index()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def save(self, agent_name: str, content: str) -> Path:
        """Persist an agent's response text."""
        path = self.artifacts_dir / f"{agent_name}.txt"
        path.write_text(content, encoding="utf-8")

        self._index[agent_name] = {
            "path": str(path),
            "size": len(content),
            "saved_at": datetime.now().isoformat(),
        }
        self._write_index()
        logger.debug("Artifact saved: %s (%d chars)", agent_name, len(content))
        return path

    def load(self, agent_name: str) -> Optional[str]:
        """Return the stored artifact for an agent, or ``None`` if not found."""
        path = self.artifacts_dir / f"{agent_name}.txt"
        if path.exists():
            return path.read_text(encoding="utf-8")
        return None

    def exists(self, agent_name: str) -> bool:
        """True if an artifact has been saved for this agent."""
        return (self.artifacts_dir / f"{agent_name}.txt").exists()

    def list_saved(self) -> list[str]:
        """Return names of agents whose artifacts are available."""
        return list(self._index.keys())

    def load_many(self, agent_names: list[str], max_chars_each: int = 3000) -> dict[str, str]:
        """
        Load multiple artifacts at once, each truncated to ``max_chars_each``.
        Skips agents whose artifacts are not yet available.
        """
        result: dict[str, str] = {}
        for name in agent_names:
            content = self.load(name)
            if content:
                result[name] = content[:max_chars_each]
        return result

    def summary(self) -> str:
        """Return a human-readable summary of saved artifacts."""
        if not self._index:
            return "No artifacts saved yet."
        lines = ["Saved artifacts:"]
        for name, meta in self._index.items():
            lines.append(f"  - {name}: {meta['size']} chars @ {meta['saved_at']}")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_index(self) -> dict[str, dict]:
        if self._index_path.exists():
            try:
                return json.loads(self._index_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                return {}
        return {}

    def _write_index(self) -> None:
        self._index_path.write_text(
            json.dumps(self._index, indent=2), encoding="utf-8"
        )
