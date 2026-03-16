"""
file_generator.py
-----------------
Parses agent responses and writes files to disk.

Expected format in agent output::

    FILE: apps/users/models.py

    ```python
    from django.db import models

    class User(AbstractUser):
        pass
    ```

Multiple FILE blocks can appear in a single response.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from logs.logger import get_logger

logger = get_logger("file_generator")

# Matches:
#   FILE: some/path/file.ext
#   ```[optional language]
#   ...code...
#   ```
_FILE_BLOCK_RE = re.compile(
    r"FILE:\s*(?P<path>[^\n]+)\n+"        # FILE: path
    r"```[a-zA-Z0-9_\-]*\n"              # opening fence (optional language)
    r"(?P<code>.*?)"                       # code content (non-greedy)
    r"```",                                # closing fence
    re.DOTALL,
)

# Fallback: plain FILE: followed by indented or raw code block
_FILE_BLOCK_PLAIN_RE = re.compile(
    r"FILE:\s*(?P<path>[^\n]+)\n+"
    r"(?P<code>(?:[ \t]+[^\n]+\n?)+)",
    re.MULTILINE,
)

# Characters not allowed in file paths
_DANGEROUS_PATH_RE = re.compile(r"\.\./|~[/\\]|^[/\\]")


class FileGenerator:
    """
    Parses agent responses and writes the specified files.

    Parameters
    ----------
    output_dir:
        Root directory for all generated files.
    """

    def __init__(self, output_dir: Path) -> None:
        self.output_dir = Path(output_dir)

    def generate(self, response_text: str) -> list[str]:
        """
        Parse ``response_text``, create files, and return a list of written paths.

        Only writes files that have a ``FILE:`` directive.
        """
        blocks = self._extract_blocks(response_text)
        written: list[str] = []

        for file_path_str, code in blocks:
            safe_path = self._sanitize(file_path_str)
            if safe_path is None:
                logger.warning("Unsafe path skipped: %s", file_path_str)
                continue

            full_path = self.output_dir / safe_path
            full_path.parent.mkdir(parents=True, exist_ok=True)

            full_path.write_text(code, encoding="utf-8")
            written.append(str(safe_path))
            logger.debug("Wrote: %s (%d bytes)", safe_path, len(code))

        return written

    def _extract_blocks(self, text: str) -> list[tuple[str, str]]:
        """Extract (file_path, code) pairs from the response text."""
        blocks: list[tuple[str, str]] = []

        for match in _FILE_BLOCK_RE.finditer(text):
            path = match.group("path").strip()
            code = match.group("code")
            blocks.append((path, code))

        if not blocks:
            # Try the plain (non-fenced) fallback
            for match in _FILE_BLOCK_PLAIN_RE.finditer(text):
                path = match.group("path").strip()
                code = match.group("code")
                blocks.append((path, code))

        return blocks

    def _sanitize(self, raw_path: str) -> Optional[Path]:
        """
        Validate and clean a file path.
        Returns ``None`` if the path is considered unsafe.
        """
        # Strip quotes and leading slashes
        cleaned = raw_path.strip("\"' \t")
        cleaned = cleaned.lstrip("/\\")

        if _DANGEROUS_PATH_RE.search(cleaned):
            return None

        try:
            return Path(cleaned)
        except (ValueError, OSError):
            return None
