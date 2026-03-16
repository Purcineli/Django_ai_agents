"""
agent_runner.py
---------------
Runs agents via the local `claude` CLI (Claude Code) instead of the
Anthropic API, so no API credits are needed — uses your Claude Pro account.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from logs.logger import get_logger

logger = get_logger("agent_runner")


def _find_claude() -> str:
    found = shutil.which("claude")
    if found:
        return found
    for candidate in [
        Path.home() / ".local" / "bin" / "claude.exe",
        Path.home() / ".local" / "bin" / "claude",
    ]:
        if candidate.exists():
            return str(candidate)
    return "claude"


CLAUDE_EXE = _find_claude()


class AgentRunner:
    """
    Runs a single agent turn by calling `claude -p` as a subprocess.

    Parameters
    ----------
    client:
        Unused — kept for interface compatibility with the old API runner.
    timeout:
        Seconds to wait for the CLI to respond (default: 300).
    """

    def __init__(self, client=None, max_tokens: int = 8192, timeout: int = 300) -> None:
        self.timeout = timeout

    def run(
        self,
        model: str,
        system: str,
        user: str,
        temperature: float = 0.7,
    ) -> str:
        """
        Call the `claude` CLI and return the full response text.

        Uses --system-prompt and --tools "" (no tools, no permission prompts).
        The user prompt is piped via stdin to avoid Windows arg-length limits.
        """
        logger.debug("Calling claude CLI …")

        cmd = [
            CLAUDE_EXE,
            "--print",
            "--output-format", "text",
            "--system-prompt", system,
            "--tools", "",                  # disable all tools — text-only response
            "--dangerously-skip-permissions",
        ]

        # Strip API key so the CLI uses the Pro account (OAuth) instead
        env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}

        try:
            result = subprocess.run(
                cmd,
                input=user,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                env=env,
            )

            if result.returncode != 0:
                output = (result.stdout + result.stderr).strip()
                logger.error("claude CLI error (exit %d): %s", result.returncode, output)
                raise RuntimeError(
                    f"claude CLI exited with code {result.returncode}: {output}"
                )

            response = result.stdout.strip()
            logger.debug("claude CLI responded with %d chars", len(response))
            return response

        except FileNotFoundError:
            logger.error(
                "'claude' not found at %s — is Claude Code installed?", CLAUDE_EXE
            )
            raise
        except subprocess.TimeoutExpired:
            logger.error("claude CLI timed out after %ds", self.timeout)
            raise
