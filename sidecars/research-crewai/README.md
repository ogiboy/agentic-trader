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

## Run

```bash
pnpm run run:research-crewai
```

The run command is a visible placeholder until the CrewAI backend is wired to
the research snapshot contract. It must not submit orders, mutate policy, or
inject raw web/social text into trading prompts.
