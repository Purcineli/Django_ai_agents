# 🏭 AI Django Factory

An autonomous AI system that generates complete, production-grade Django web applications from a single product description.

The factory simulates a full software engineering team — 19 specialised AI agents coordinated by a Python orchestrator — each contributing their expertise to build a complete Django project.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     ORCHESTRATOR                         │
│  (orchestrator.py)                                       │
│                                                          │
│  ┌──────────┐  ┌────────────┐  ┌──────────────────────┐ │
│  │  Agent   │  │  Memory    │  │  Context Selector    │ │
│  │  Loader  │  │  Manager   │  │  (token optimizer)   │ │
│  └──────────┘  └────────────┘  └──────────────────────┘ │
│                                                          │
│  ┌──────────┐  ┌────────────┐  ┌──────────────────────┐ │
│  │  Agent   │  │  Artifact  │  │  File Generator      │ │
│  │  Runner  │  │  Manager   │  │  (FILE: parser)      │ │
│  └──────────┘  └────────────┘  └──────────────────────┘ │
└─────────────────────────────────────────────────────────┘
            │
            ▼
    ┌───────────────┐
    │  Anthropic    │
    │  Claude API   │
    │  (streaming)  │
    └───────────────┘
```

## System Components

| Module | File | Responsibility |
|--------|------|----------------|
| **Orchestrator** | `orchestrator/orchestrator.py` | Runs the full agent pipeline. Loads context, calls agents, updates memory, generates files. |
| **Agent Runner** | `orchestrator/agent_runner.py` | Wraps the Anthropic streaming API. Resolves model aliases. Handles retries. |
| **Agent Loader** | `orchestrator/agent_loader.py` | Reads and parses agent `.md` definition files (YAML frontmatter + sections). |
| **Memory Manager** | `orchestrator/memory_manager.py` | Reads/writes persistent memory files. Extracts relevant sections from agent output. |
| **Context Selector** | `orchestrator/context_selector.py` | Maps each agent to the memory files and prior artifacts it needs. Prevents token bloat. |
| **File Generator** | `orchestrator/file_generator.py` | Parses `FILE: path` + code block format from agent responses. Writes files safely. |
| **Artifact Manager** | `orchestrator/artifact_manager.py` | Saves and loads raw agent outputs. Maintains an index for the current project. |
| **Token Optimizer** | `orchestrator/token_optimizer.py` | Estimates token counts. Trims prompts that exceed the budget. |

## Agent Pipeline (in order)

| # | Agent | Model | Responsibility |
|---|-------|-------|----------------|
| 1 | **Product Manager** | Opus | Product requirements, user stories, feature prioritisation |
| 2 | **Business Analyst** | Opus | Business rules, data dictionary, process flows |
| 3 | **CTO** | Opus | Technology stack, architecture decisions (ADRs) |
| 4 | **System Architect** | Opus | Detailed system design, component contracts |
| 5 | **Django Architect** | Sonnet | Project scaffold, settings, URL config, core app |
| 6 | **Database Engineer** | Sonnet | Django models, migrations, admin configuration |
| 7 | **API Engineer** | Sonnet | DRF serializers, ViewSets, permissions, URL routing |
| 8 | **Backend Engineer** | Sonnet | Services, Celery tasks, signals, middleware |
| 9 | **Frontend Engineer** | Sonnet | HTML templates, Tailwind components, Alpine.js, HTMX |
| 10 | **UI/UX Designer** | Sonnet | Design system, wireframes, interaction patterns |
| 11 | **Security Engineer** | Opus | Security audit, hardened settings, rate limiting, audit logs |
| 12 | **DevOps Engineer** | Sonnet | Dockerfile, docker-compose, GitHub Actions, Nginx |
| 13 | **Testing Engineer** | Sonnet | pytest test suite, factories, coverage configuration |
| 14 | **Performance Engineer** | Sonnet | Query optimisation, caching, indexing |
| 15 | **Refactoring Engineer** | Sonnet | SOLID principles, type hints, DRY cleanup |
| 16 | **Documentation Engineer** | Sonnet | README, API docs, deployment guide |

## Project Memory System

Memory persists across agents in `memory/`:

| File | Contents |
|------|----------|
| `architecture.md` | Tech stack, system design, component decisions |
| `database.md` | Schema, models, relationships |
| `api.md` | Endpoints, serializers, permissions |
| `ui.md` | Frontend structure, components, design tokens |
| `decisions.md` | Key decisions, trade-offs, reasoning |

Each agent reads **only the memory files relevant to its role** (context selection).

## Token Optimisation

- Each agent receives only the memory files it needs (see `context_selector.py`)
- Artifacts are truncated to a configurable max (default: 3,000 chars per artifact)
- Memory files are summarised when they exceed 1,500 chars (most-recent content kept)
- Full conversation history is **never** sent — only selected context
- A budget check prevents prompts from exceeding the model's context window

## Model Assignment

| Task Complexity | Model | Use Case |
|----------------|-------|----------|
| Heavy reasoning | `claude-opus-4-6` | PM, BA, CTO, System Architect, Security |
| Coding | `claude-sonnet-4-6` | Django code generation, tests, DevOps |
| Light tasks | `claude-haiku-4-5` | (available for future light tasks) |

---

## Quick Start

### 1. Clone & Install

```bash
git clone <repo>
cd ai-django-factory
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure API Key

```bash
cp .env.example .env
# Edit .env and set ANTHROPIC_API_KEY=sk-ant-...
```

### 3. Generate a Project

```bash
# From a description string
python main.py "A SaaS invoicing app for freelancers with clients, invoices, and PDF export"

# From a file
python main.py "$(cat prompts/example_saas.txt)"

# Interactive mode (no description argument)
python main.py

# Custom project name
python main.py "My app description" --project my_invoicing_app

# Run only specific agents
python main.py "My app" --agents product_manager,business_analyst,cto

# Resume from a specific agent
python main.py "My app" --resume backend_engineer

# List available agents
python main.py --list-agents
```

### 4. Find Generated Files

```
generated/
└── <project_name>/
    ├── config/
    │   └── settings/
    ├── apps/
    │   ├── core/
    │   ├── users/
    │   └── <feature_apps>/
    ├── templates/
    ├── static/
    ├── docs/
    ├── Dockerfile
    ├── docker-compose.yml
    ├── requirements/
    └── README.md
```

---

## Agent Output Format

All agents generate files using this format:

```
FILE: apps/users/models.py
```python
from django.db import models

class User(AbstractUser):
    pass
```
```

The **File Generator** (`file_generator.py`) parses these blocks and writes them to disk automatically.

---

## Adding a New Agent

1. Create `agents/my_agent.md` with YAML frontmatter and sections.
2. Add it to `DEFAULT_PIPELINE` in `orchestrator/orchestrator.py` at the right position.
3. Update `AGENT_MEMORY_NEEDS` and `AGENT_ARTIFACT_NEEDS` in `context_selector.py`.
4. Update `AGENT_MEMORY_MAP` in `memory_manager.py`.

---

## Project Structure

```
ai-django-factory/
├── agents/                    # 19 agent definition files (markdown)
├── orchestrator/
│   ├── orchestrator.py        # Main pipeline coordinator
│   ├── agent_runner.py        # Anthropic API wrapper (streaming)
│   ├── agent_loader.py        # Markdown agent file parser
│   ├── memory_manager.py      # Persistent memory read/write
│   ├── context_selector.py    # Token optimisation: select relevant context
│   ├── file_generator.py      # Parse FILE: blocks and write files
│   ├── artifact_manager.py    # Save/load per-agent outputs
│   └── token_optimizer.py     # Estimate and trim token usage
├── memory/                    # Project memory files (populated at runtime)
├── artifacts/                 # Raw agent outputs (populated at runtime)
├── generated/                 # Generated Django projects (output)
├── logs/                      # Log files + logger module
├── prompts/                   # Example project descriptions
├── main.py                    # CLI entry point
├── requirements.txt
└── .env.example
```
