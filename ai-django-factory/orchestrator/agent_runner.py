"""
agent_runner.py
---------------
Runs agents via the local `claude` CLI (Claude Code) instead of the
Anthropic API, so no API credits are needed — uses your Claude Pro account.
"""

from __future__ import annotations

import subprocess

from logs.logger import get_logger

logger = get_logger("agent_runner")


class AgentRunner:
    """
    Runs a single agent turn by calling `claude -p` as a subprocess.

    Parameters
    ----------
    max_tokens:
        Ignored (CLI controls this), kept for interface compatibility.
    timeout:
        Seconds to wait for the CLI to respond (default: 300).
    """

    def __init__(self, client=None, max_tokens: int = 8192, timeout: int = 300) -> None:
        # `client` accepted but unused — kept so Orchestrator needs no change
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

        The system and user prompts are combined and piped via stdin to avoid
        OS argument-length limits on long prompts.

        Parameters
        ----------
        model:
            Ignored — the CLI uses whichever model Claude Code defaults to.
        system:
            System prompt text.
        user:
            User message text.
        temperature:
            Ignored — the CLI does not expose this parameter.

        Returns
        -------
        str
            The complete assistant response as a single string.
        """
        full_prompt = f"<system>\n{system}\n</system>\n\n{user}"

        logger.debug("Calling claude CLI (model/temperature ignored in CLI mode) …")

        try:
            result = subprocess.run(
                ["claude", "-p"],
                input=full_prompt,
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )

            if result.returncode != 0:
                stderr = result.stderr.strip()
                logger.error("claude CLI error (exit %d): %s", result.returncode, stderr)
                raise RuntimeError(f"claude CLI exited with code {result.returncode}: {stderr}")

            response = result.stdout.strip()
            logger.debug("claude CLI responded with %d chars", len(response))
            return response

        except FileNotFoundError:
            logger.error("'claude' command not found — is Claude Code installed and on PATH?")
            raise
        except subprocess.TimeoutExpired:
            logger.error("claude CLI timed out after %ds", self.timeout)
            raise
