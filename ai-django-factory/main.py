#!/usr/bin/env python3
"""
main.py
-------
Entry point for the AI Django Factory.

Usage
-----
    python main.py "A SaaS task management app with teams, projects and Kanban board"

Options
-------
    --project  Project name (default: derived from description)
    --agents   Comma-separated list of agents to run (default: full pipeline)
    --output   Output directory (default: generated/<project_name>)
    --resume   Resume from a specific agent (skip earlier ones)
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# Make the package importable when running from the repo root
sys.path.insert(0, str(Path(__file__).resolve().parent))

from orchestrator.orchestrator import Orchestrator, DEFAULT_PIPELINE  # noqa: E402


def _slugify(text: str) -> str:
    """Convert a phrase to a filesystem-safe slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "_", text)
    return text[:40]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="AI Django Factory — Generate a Django project from a description",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "description",
        nargs="?",
        help="Product idea or project description",
    )
    parser.add_argument(
        "--project",
        default=None,
        help="Project name (auto-derived if not provided)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output directory for generated files",
    )
    parser.add_argument(
        "--agents",
        default=None,
        help="Comma-separated agent names to run (default: full pipeline)",
    )
    parser.add_argument(
        "--resume",
        default=None,
        help="Resume pipeline from this agent name (skip earlier agents)",
    )
    parser.add_argument(
        "--list-agents",
        action="store_true",
        help="List all available agents and exit",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.list_agents:
        print("Available agents (default pipeline order):")
        for i, name in enumerate(DEFAULT_PIPELINE, 1):
            print(f"  {i:2}. {name}")
        return

    # Get project description
    description = args.description
    if not description:
        print("Enter your project description (press Enter twice when done):")
        lines: list[str] = []
        while True:
            line = input()
            if line == "" and lines and lines[-1] == "":
                break
            lines.append(line)
        description = "\n".join(lines).strip()

    if not description:
        print("Error: no project description provided.", file=sys.stderr)
        sys.exit(1)

    # Determine project name
    project_name = args.project or _slugify(description.split(".")[0][:60])

    # Build pipeline
    if args.agents:
        pipeline = [a.strip() for a in args.agents.split(",")]
    elif args.resume:
        try:
            start_idx = DEFAULT_PIPELINE.index(args.resume)
            pipeline = DEFAULT_PIPELINE[start_idx:]
            print(f"Resuming from agent: {args.resume} (step {start_idx + 1}/{len(DEFAULT_PIPELINE)})")
        except ValueError:
            print(f"Error: agent '{args.resume}' not found in pipeline.", file=sys.stderr)
            sys.exit(1)
    else:
        pipeline = DEFAULT_PIPELINE

    # Run
    print(f"\n🏭  AI Django Factory")
    print(f"   Project : {project_name}")
    print(f"   Agents  : {len(pipeline)}")
    print(f"   Output  : {args.output or f'generated/{project_name}'}")
    print()

    orch = Orchestrator(
        project_name=project_name,
        output_dir=args.output,
        pipeline=pipeline,
    )
    orch.run(description)


if __name__ == "__main__":
    main()
