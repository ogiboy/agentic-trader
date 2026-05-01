# Agentic Trader Research Flow

This is the tracked, isolated CrewAI Flow sidecar for Agentic Trader research
experiments. It is intentionally outside the root dependency graph and is
managed by its own `uv` project.

## Contract

- The root runtime calls this sidecar only through subprocess JSON.
- The sidecar reads one normalized research request from stdin through
  `research-flow-contract`.
- It returns one JSON payload that matches `research-flow.v1`.
- It never imports the root trading runtime, broker, execution, DuckDB writer, or
  runtime-mode mutation code.
- It never injects raw web/social text directly into trading prompts.

## Setup

```bash
cd sidecars/research_flow
uv sync --locked
uv run --locked research-flow-check
printf '%s\n' '{"mode":"training","symbols":["AAPL"],"provider_outputs":[]}' \
  | uv run --locked --no-sync research-flow-contract
```

The project is pinned to Python `3.13` through `.python-version`, while
`requires-python` stays within CrewAI's supported `<3.14` range.

## Running

`research-flow` is a gated placeholder Flow. Use the root command for the safe
no-LLM smoke path:

```bash
AGENTIC_TRADER_ALLOW_CREWAI_NOOP=1 pnpm run run:research-flow
```

Future LLM-backed Flow steps should stay behind explicit operator configuration
and should consume only normalized provider packets from the root `researchd`
process.
