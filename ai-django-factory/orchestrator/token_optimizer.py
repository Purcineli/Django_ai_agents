"""
token_optimizer.py
------------------
Estimates token usage and trims prompts so they fit within the model's
context window.

Strategies used
~~~~~~~~~~~~~~~
1. **Context selection** – only relevant memory files are included
   (handled by ``context_selector.py``).
2. **Artifact truncation** – each artifact is capped at ``max_artifact_chars``
   (handled by ``artifact_manager.py``).
3. **Prompt fitting** – if the combined system + user prompt exceeds
   ``max_input_chars``, the user message is trimmed from the least-important
   sections (old memory entries).
4. **Memory summarisation** – long memory files are summarised automatically
   by ``MemoryManager.summarize()``.

Token estimation
~~~~~~~~~~~~~~~~
A simple heuristic: 1 token ≈ 4 characters (English prose).  This is
conservative enough to stay well inside limits.
"""

from __future__ import annotations

from logs.logger import get_logger

logger = get_logger("token_optimizer")

# ~4 chars per token (conservative)
CHARS_PER_TOKEN = 4

# Target input token budget (leaves headroom for the model's output)
# claude-opus-4-6 context: 200K tokens → ~800K chars
# claude-sonnet-4-6 context: 200K tokens → ~800K chars
# We use a conservative 100K token budget for input = 400K chars
MAX_INPUT_CHARS = 400_000

# Warning threshold
WARN_CHARS = 300_000


def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // CHARS_PER_TOKEN)


class TokenOptimizer:
    """
    Ensures combined prompts do not exceed the model's context window.
    """

    def fit(self, system_prompt: str, user_prompt: str) -> str:
        """
        If the total prompt length exceeds the budget, trim the user prompt
        while preserving the most-recent content.

        Returns the (possibly trimmed) user prompt.
        """
        total = len(system_prompt) + len(user_prompt)
        tokens_est = _estimate_tokens(system_prompt + user_prompt)

        if total > WARN_CHARS:
            logger.warning(
                "Large prompt: ~%d tokens (%d chars). Trimming …",
                tokens_est,
                total,
            )

        available_for_user = MAX_INPUT_CHARS - len(system_prompt)

        if len(user_prompt) <= available_for_user:
            logger.debug("Prompt OK: ~%d tokens.", tokens_est)
            return user_prompt

        # Trim: keep the tail (most recent content) of the user prompt
        trimmed = user_prompt[-available_for_user:]

        # Try to trim at a section boundary
        newline_pos = trimmed.find("\n")
        if newline_pos > 0:
            trimmed = "[...context trimmed for token budget...]\n" + trimmed[newline_pos:]

        logger.info(
            "User prompt trimmed: %d → %d chars",
            len(user_prompt),
            len(trimmed),
        )
        return trimmed

    @staticmethod
    def estimate(text: str) -> int:
        """Return estimated token count for a string."""
        return _estimate_tokens(text)

    @staticmethod
    def budget_report(system: str, user: str) -> str:
        """Return a human-readable budget report."""
        sys_tok = _estimate_tokens(system)
        usr_tok = _estimate_tokens(user)
        total = sys_tok + usr_tok
        pct = total / (MAX_INPUT_CHARS // CHARS_PER_TOKEN) * 100
        return (
            f"Token budget: system={sys_tok:,}  user={usr_tok:,}  "
            f"total={total:,}  ({pct:.1f}% of {MAX_INPUT_CHARS//CHARS_PER_TOKEN:,})"
        )
