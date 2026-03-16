"""
context_selector.py
-------------------
Decides which memory files and previous artifacts are injected into each
agent's prompt. This is the token-optimization layer — agents only receive
context that is relevant to their role.

Context map (agent → memory keys)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
* Product Manager    → decisions
* Business Analyst   → decisions
* CTO                → decisions, architecture
* System Architect   → decisions, architecture
* Django Architect   → architecture
* Database Engineer  → architecture, database
* API Engineer       → architecture, database, api
* Backend Engineer   → architecture, database, api
* Frontend Engineer  → api, ui
* UI/UX Designer     → ui
* Security Engineer  → architecture, api
* DevOps Engineer    → architecture
* Testing Engineer   → architecture, api
* Performance Engineer → architecture, database
* Refactoring Engineer → architecture
* Documentation Engineer → architecture, api, ui

Artifact dependencies (agent → list of prior agent artifacts to include)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Each agent receives the output of the immediately preceding agent(s) it
depends on, rather than the full history.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .memory_manager import MemoryManager
    from .artifact_manager import ArtifactManager

# Memory files each agent should receive
AGENT_MEMORY_NEEDS: dict[str, list[str]] = {
    "product_manager":       ["decisions"],
    "business_analyst":      ["decisions"],
    "cto":                   ["decisions", "architecture"],
    "system_architect":      ["decisions", "architecture"],
    "django_architect":      ["architecture"],
    "database_engineer":     ["architecture", "database"],
    "api_engineer":          ["architecture", "database", "api"],
    "backend_engineer":      ["architecture", "database", "api"],
    "frontend_engineer":     ["api", "ui"],
    "ui_ux_designer":        ["ui"],
    "security_engineer":     ["architecture", "api"],
    "devops_engineer":       ["architecture"],
    "testing_engineer":      ["architecture", "api"],
    "performance_engineer":  ["architecture", "database"],
    "refactoring_engineer":  ["architecture"],
    "documentation_engineer":["architecture", "api", "ui"],
    "code_review_engineer":  ["architecture", "api"],
    "migration_engineer":    ["database"],
    "accessibility_engineer":["ui"],
}

# Prior agent outputs each agent depends on (in order of priority)
AGENT_ARTIFACT_NEEDS: dict[str, list[str]] = {
    "product_manager":       [],
    "business_analyst":      ["product_manager"],
    "cto":                   ["business_analyst", "product_manager"],
    "system_architect":      ["cto", "business_analyst"],
    "django_architect":      ["system_architect", "cto"],
    "database_engineer":     ["django_architect", "system_architect"],
    "api_engineer":          ["database_engineer", "django_architect"],
    "backend_engineer":      ["api_engineer", "database_engineer"],
    "frontend_engineer":     ["api_engineer", "ui_ux_designer"],
    "ui_ux_designer":        ["frontend_engineer", "product_manager"],
    "security_engineer":     ["backend_engineer", "api_engineer"],
    "devops_engineer":       ["django_architect", "backend_engineer"],
    "testing_engineer":      ["backend_engineer", "frontend_engineer"],
    "performance_engineer":  ["backend_engineer", "database_engineer"],
    "refactoring_engineer":  ["backend_engineer", "testing_engineer"],
    "documentation_engineer":["refactoring_engineer", "api_engineer"],
    "code_review_engineer":  ["backend_engineer", "frontend_engineer"],
    "migration_engineer":    ["database_engineer"],
    "accessibility_engineer":["frontend_engineer", "ui_ux_designer"],
}

# Maximum characters per memory section
MAX_MEMORY_CHARS = 1500
# Maximum characters per artifact
MAX_ARTIFACT_CHARS = 3000


class ContextSelector:
    """
    Builds the context string to inject into each agent's prompt.
    """

    def get_memory_context(self, agent_name: str, memory: "MemoryManager") -> str:
        """Return relevant memory sections for this agent."""
        keys = AGENT_MEMORY_NEEDS.get(agent_name, ["decisions"])
        sections: list[str] = []

        for key in keys:
            content = memory.summarize(key, max_chars=MAX_MEMORY_CHARS)
            if content.strip():
                sections.append(f"### {key.title()} Memory\n\n{content.strip()}")

        return "\n\n".join(sections)

    def get_artifact_context(self, agent_name: str, artifacts: "ArtifactManager") -> str:
        """Return relevant prior artifacts for this agent."""
        needed = AGENT_ARTIFACT_NEEDS.get(agent_name, [])
        sections: list[str] = []

        for prior_agent in needed:
            content = artifacts.load(prior_agent)
            if content:
                truncated = content[:MAX_ARTIFACT_CHARS]
                if len(content) > MAX_ARTIFACT_CHARS:
                    truncated += "\n[...truncated for context...]"
                sections.append(
                    f"### Output from: {prior_agent.replace('_', ' ').title()}\n\n{truncated}"
                )

        return "\n\n".join(sections)
