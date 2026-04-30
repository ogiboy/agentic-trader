# Research CrewAI Sidecar

Tracked but isolated CrewAI Flow project for future deep-dive research loops.

This sidecar is intentionally separate from the root `agentic-trader` Poetry
runtime. It uses `uv`, Python 3.13, and its own lockfile so CrewAI dependency
constraints do not leak into broker, runtime, memory, or operator surfaces.

## Setup

```bash
pnpm run setup:research-crewai
```

## Check

```bash
pnpm run check:research-crewai
```

The check command compiles the sidecar, imports CrewAI, verifies the installed
Python version, and runs the pure JSON contract command used by the root
`ResearchSidecarBackend`.

## Run

```bash
pnpm run run:research-crewai
```

The run command is a visible placeholder until the CrewAI backend is wired to
the research snapshot contract. It must not submit orders, mutate policy, or
inject raw web/social text into trading prompts.

## Contract

The root runtime calls the sidecar through `uv run --locked --no-sync
research-crewai-contract`, passing one JSON request on stdin and reading one JSON
response from stdout. This command is deterministic and does not run LLM-backed
research tasks yet.

The contract now returns planned task definitions for:

- company dossiers
- timeline reconstruction
- contradiction checks
- watch-next lists
- sector briefs

These plans describe future CrewAI work and are safe to persist as metadata; they
are not trade-memory writes and they do not execute broker or policy actions.
