"""
orchestrator.py
---------------
Main pipeline orchestrator. Loads agents, selects context, runs each agent in
order, collects artifacts, and updates memory after every step.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Optional

import anthropic

from orchestrator.agent_loader import AgentLoader
from orchestrator.agent_runner import AgentRunner
from orchestrator.artifact_manager import ArtifactManager
from orchestrator.context_selector import ContextSelector
from orchestrator.file_generator import FileGenerator
from orchestrator.memory_manager import MemoryManager
from orchestrator.token_optimizer import TokenOptimizer
from logs.logger import get_logger

ROOT = Path(__file__).resolve().parent.parent
logger = get_logger("orchestrator")

# Default pipeline order
DEFAULT_PIPELINE: list[str] = [
    "product_manager",
    "business_analyst",
    "cto",
    "system_architect",
    "django_architect",
    "database_engineer",
    "api_engineer",
    "backend_engineer",
    "frontend_engineer",
    "ui_ux_designer",
    "security_engineer",
    "devops_engineer",
    "testing_engineer",
    "performance_engineer",
    "refactoring_engineer",
    "documentation_engineer",
]


class Orchestrator:
    """
    Coordinates the full agent pipeline for a Django project.

    Usage::

        orch = Orchestrator(project_name="my_saas", output_dir="generated/my_saas")
        orch.run("A SaaS task management app with teams, projects and Kanban board")
    """

    def __init__(
        self,
        project_name: str,
        output_dir: Optional[str] = None,
        pipeline: Optional[list[str]] = None,
    ) -> None:
        self.project_name = project_name
        self.output_dir = Path(output_dir or ROOT / "generated" / project_name)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.pipeline = pipeline or DEFAULT_PIPELINE

        self.client = anthropic.Anthropic()
        self.loader = AgentLoader(ROOT / "agents")
        self.memory = MemoryManager(ROOT / "memory")
        self.artifacts = ArtifactManager(ROOT / "artifacts" / project_name)
        self.selector = ContextSelector()
        self.generator = FileGenerator(self.output_dir)
        self.optimizer = TokenOptimizer()
        self.runner = AgentRunner(self.client)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self, project_description: str) -> None:
        """Execute the full pipeline for a given product description."""
        logger.info("=" * 60)
        logger.info(f"PROJECT : {self.project_name}")
        logger.info(f"OUTPUT  : {self.output_dir}")
        logger.info("=" * 60)

        # Seed memory with project description
        self.memory.update("decisions", f"## Project: {self.project_name}\n\n{project_description}\n")

        total = len(self.pipeline)
        for idx, agent_name in enumerate(self.pipeline, start=1):
            logger.info(f"\n[{idx}/{total}] Running agent: {agent_name.upper()}")
            self._run_agent(agent_name, project_description)

        logger.info("\n✅  Pipeline complete. Files written to: %s", self.output_dir)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _run_agent(self, agent_name: str, project_description: str) -> None:
        """Load agent, build prompt, call API, store artifact, generate files."""
        # 1. Load agent definition
        agent = self.loader.load(agent_name)
        if agent is None:
            logger.warning("Agent '%s' not found — skipping.", agent_name)
            return

        # 2. Select relevant memory + artifacts
        memory_context = self.selector.get_memory_context(agent_name, self.memory)
        artifact_context = self.selector.get_artifact_context(agent_name, self.artifacts)

        # 3. Build system + user prompt
        system_prompt = self._build_system_prompt(agent, project_description)
        user_prompt = self._build_user_prompt(agent, memory_context, artifact_context, project_description)

        # 4. Optimize tokens
        user_prompt = self.optimizer.fit(system_prompt, user_prompt)

        # 5. Call the model
        logger.info("  model=%s  temperature=%.1f", agent["model"], agent["temperature"])
        t0 = time.time()
        response_text = self.runner.run(
            model=agent["model"],
            system=system_prompt,
            user=user_prompt,
            temperature=agent["temperature"],
        )
        elapsed = time.time() - t0
        logger.info("  completed in %.1fs  chars=%d", elapsed, len(response_text))

        # 6. Save artifact
        self.artifacts.save(agent_name, response_text)

        # 7. Generate files from response
        files_written = self.generator.generate(response_text)
        if files_written:
            logger.info("  files written: %s", ", ".join(files_written))

        # 8. Update memory
        self.memory.update_from_agent(agent_name, response_text)

    def _build_system_prompt(self, agent: dict, project_description: str) -> str:
        return (
            f"You are a {agent['role']} working on a software project.\n\n"
            f"PROJECT DESCRIPTION:\n{project_description}\n\n"
            f"{agent.get('system_prompt', '')}\n\n"
            "IMPORTANT: When generating files, use EXACTLY this format:\n\n"
            "FILE: path/to/file.ext\n"
            "```language\n"
            "code here\n"
            "```\n\n"
            "Generate multiple files as needed. Be thorough and production-quality."
        )

    def _build_user_prompt(
        self,
        agent: dict,
        memory_context: str,
        artifact_context: str,
        project_description: str,
    ) -> str:
        parts = [f"# Task for {agent['name']}\n"]

        if memory_context:
            parts.append(f"## Project Memory\n{memory_context}\n")

        if artifact_context:
            parts.append(f"## Previous Agent Outputs\n{artifact_context}\n")

        default_task = "Perform your role as {} for this project.".format(agent["role"])
        parts.append(
            "## Your Task\n"
            + agent.get("task_prompt", default_task)
            + "\n\nExpected outputs: "
            + ", ".join(agent.get("outputs", []))
        )

        return "\n".join(parts)
