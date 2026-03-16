"""
agent_runner.py
---------------
Thin wrapper around the Anthropic Messages API.
Supports streaming (default) to avoid timeouts on long outputs.
"""

from __future__ import annotations

import anthropic

from logs.logger import get_logger

logger = get_logger("agent_runner")

# Map short model aliases to real model IDs
MODEL_MAP: dict[str, str] = {
    "opus": "claude-opus-4-6",
    "sonnet": "claude-sonnet-4-6",
    "haiku": "claude-haiku-4-5",
    # allow full IDs to pass through
    "claude-opus-4-6": "claude-opus-4-6",
    "claude-sonnet-4-6": "claude-sonnet-4-6",
    "claude-haiku-4-5": "claude-haiku-4-5",
}


class AgentRunner:
    """
    Runs a single agent turn via the Anthropic streaming API.

    Parameters
    ----------
    client:
        Instantiated ``anthropic.Anthropic`` client.
    max_tokens:
        Maximum tokens in the response (default: 8192).
    """

    def __init__(self, client: anthropic.Anthropic, max_tokens: int = 8192) -> None:
        self.client = client
        self.max_tokens = max_tokens

    def run(
        self,
        model: str,
        system: str,
        user: str,
        temperature: float = 0.7,
    ) -> str:
        """
        Call the API with streaming and return the full response text.

        Parameters
        ----------
        model:
            Short alias ("opus", "sonnet", "haiku") or full model ID.
        system:
            System prompt text.
        user:
            User message text.
        temperature:
            Sampling temperature (0.0–1.0).

        Returns
        -------
        str
            The complete assistant response as a single string.
        """
        resolved_model = MODEL_MAP.get(model, model)

        logger.debug("Calling %s (streaming) …", resolved_model)

        chunks: list[str] = []
        try:
            with self.client.messages.stream(
                model=resolved_model,
                max_tokens=self.max_tokens,
                temperature=temperature,
                system=system,
                messages=[{"role": "user", "content": user}],
            ) as stream:
                for text_chunk in stream.text_stream:
                    chunks.append(text_chunk)
                    # Optional: real-time progress dots
                    print(".", end="", flush=True)

            print()  # newline after dots
            return "".join(chunks)

        except anthropic.RateLimitError as exc:
            logger.error("Rate limit hit: %s", exc)
            raise
        except anthropic.APIStatusError as exc:
            logger.error("API error %s: %s", exc.status_code, exc.message)
            raise
        except anthropic.APIConnectionError as exc:
            logger.error("Connection error: %s", exc)
            raise
