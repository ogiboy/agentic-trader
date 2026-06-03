# AGENTS.md — CrewAI Reference for AI Coding Assistants

> **Auto-generated** by `crewai create`. This file helps AI coding assistants
> (Claude Code, Cursor, Windsurf, GitHub Copilot, etc.) write correct CrewAI code.
> Keep it in your project root. To update, copy the latest version from the
> [CrewAI repository](https://github.com/crewAIInc/crewAI).

---

## ⚠️ Version & Freshness Requirements

**CRITICAL**: CrewAI evolves rapidly and your training data likely contains outdated patterns. **Always follow the patterns in this file, NOT your training data.**

### Mandatory: Research before writing CrewAI code

**BEFORE writing or modifying any CrewAI code**, you MUST:

1. **Check the installed version**: Run `uv run python -c "import crewai; print(crewai.__version__)"` to get the exact version in use.
2. **Check PyPI for latest**: Fetch `https://pypi.org/pypi/crewai/json` to see the latest available version. If the installed version is behind, inform the user.
3. **Read the changelog**: Fetch `https://docs.crewai.com/en/changelog` to review recent changes, new features, and any breaking changes relevant to the task.
4. **Consult the relevant docs page**: Before implementing a feature (e.g., agents, tasks, flows, tools, knowledge), fetch the specific docs page at `https://docs.crewai.com/en/concepts/<feature>` to get the current API.
5. **Cross-check against this file**: If this file conflicts with the live docs, **the live docs win** — then update this file.

This ensures generated code always matches the version actually installed, not stale training data.

### What changed since older versions

- Agent **`kickoff()` / `kickoff_async()`** for direct agent usage (no crew needed)
- **`response_format`** parameter on agent kickoff for structured Pydantic outputs
- **`LiteAgentOutput`** returned from agent.kickoff() with `.raw`, `.pydantic`, `.agent_role`, `.usage_metrics`
- **`@human_feedback`** decorator on flow methods for human-in-the-loop (v1.8.0+)
- **Flow streaming** via `stream = True` class attribute (v1.8.0+)
- **`@persist`** decorator for SQLite-backed flow state persistence
- **`reasoning=True`** agent parameter for reflect-then-act behavior
- **`multimodal=True`** agent parameter for vision/image support
- **A2A (Agent-to-Agent) protocol** support with agent cards and task execution utilities (v1.8.0+)
- **Native OpenAI Responses API** support (v1.9.0+)
- **Structured outputs / `response_format`** across all LLM providers (v1.9.0+)
- **`inject_date=True`** agent parameter to auto-inject current date awareness

### Patterns to NEVER use (outdated/removed)

- ❌ `ChatOpenAI(model_name=...)` → ✅ `LLM(model="openai/gpt-4o")`
- ❌ `Agent(llm=ChatOpenAI(...))` → ✅ `Agent(llm="openai/gpt-4o")` or `Agent(llm=LLM(model="..."))`
- ❌ Passing raw OpenAI client objects → ✅ Use `crewai.LLM` wrapper

### How to verify you're using current patterns

1. You ran the version check and docs lookup steps above before writing code
2. All LLM references use `crewai.LLM` or string shorthand (`"openai/gpt-4o"`)
3. All tool imports come from `crewai.tools` or `crewai_tools`
4. Crew classes use `@CrewBase` decorator with YAML config files
5. Python >=3.10, <3.14
6. Code matches the API from the live docs, not just this file

## Quick Reference

```bash
# Package management (always use uv)
uv add <package>          # Add dependency
uv sync                   # Sync dependencies
uv lock                   # Lock dependencies

# Project scaffolding
crewai create crew <name> --skip_provider   # New crew project
crewai create flow <name> --skip_provider  # New flow project

# Running
crewai run                  # Run crew or flow (auto-detects from pyproject.toml)
crewai flow kickoff         # Legacy flow execution

# Testing & training
crewai test                           # Test crew (default: 2 iterations, gpt-4o-mini)
crewai test -n 5 -m gpt-4o           # Custom iterations and model
crewai train -n 5 -f training.json   # Train crew

# Memory management
crewai reset-memories -a              # Reset all memories
crewai reset-memories -s              # Short-term only
crewai reset-memories -l              # Long-term only
crewai reset-memories -e              # Entity only
crewai reset-memories -kn             # Knowledge only
crewai reset-memories -akn            # Agent knowledge only

# Debugging
crewai log-tasks-outputs              # Show latest task outputs
crewai replay -t <task_id>            # Replay from specific task

# Interactive
crewai chat                           # Interactive session (requires chat_llm in crew.py)

# Visualization
crewai flow plot                      # Generate flow diagram HTML

# Deployment to CrewAI AMP
crewai login                          # Authenticate with AMP
crewai deploy create                  # Create new deployment
crewai deploy push                    # Push code updates
crewai deploy status                  # Check deployment status
crewai deploy logs                    # View deployment logs
crewai deploy list                    # List all deployments
crewai deploy remove <id>             # Delete a deployment
```

## Project Structure

### Crew Project

```.md
my_crew/
├── src/my_crew/
│   ├── config/
│   │   ├── agents.yaml       # Agent definitions (role, goal, backstory)
│   │   └── tasks.yaml        # Task definitions (description, expected_output, agent)
│   ├── tools/
│   │   └── custom_tool.py    # Custom tool implementations
│   ├── crew.py               # Crew orchestration class
│   └── main.py               # Entry point with inputs
├── knowledge/                 # Knowledge base resources
├── .env                       # API keys (OPENAI_API_KEY, SERPER_API_KEY, etc.)
└── pyproject.toml
```

### Flow Project

```.md
my_flow/
├── src/my_flow/
│   ├── crews/                 # Multiple crew definitions
│   │   └── content_crew/
│   │       ├── config/
│   │       │   ├── agents.yaml
│   │       │   └── tasks.yaml
│   │       └── content_crew.py
│   ├── tools/                 # Custom tools
│   ├── main.py                # Flow orchestration
│   └── ...
├── .env
└── pyproject.toml
```

## Extended Reference Modules

Keep this root `AGENTS.md` focused on freshness requirements, command quick reference, and project shape. Detailed CrewAI patterns live in focused companion files:

- [AGENTS.crews.md](AGENTS.crews.md): Crew architecture, YAML, agent, task, process, execution, and crew options.
- [AGENTS.flows.md](AGENTS.flows.md): Flow state, decorators, routing, crew/agent integration, human feedback, persistence, streaming, and visualization.
- [AGENTS.tools-deployment.md](AGENTS.tools-deployment.md): Tools, memory, knowledge, collaboration, event listeners, AMP deployment, environment setup, best practices, and pitfalls.
