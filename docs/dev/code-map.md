# Developer Code Map

This file is a lightweight orientation guide for future maintainers and agentic
coding passes. It complements inline docstrings: docstrings explain local
behavior, while this map explains where to look and how the pieces connect.

## Runtime Entrypoints

- `main.py` delegates to `agentic_trader.cli:app` so `python main.py ...` and the installed `agentic-trader ...` command share the same command surface.
- `agentic_trader/cli.py` is the main Typer command module. It owns operator commands, JSON payload builders for UI clients, Rich renderers, and root command dispatch.
- `agentic_trader/tui.py` is the legacy/admin Rich control room. It remains useful for fallback workflows and manual operator menus.
- `tui/index.mjs` is the primary Ink control room. It talks to Python through the installed CLI and read-only JSON payload commands.

## Orchestration

- `agentic_trader/workflows/run_once.py` runs one strict agent cycle from market data or a prepared snapshot, persists stage traces, and emits progress callbacks.
- `agentic_trader/workflows/service.py` wraps `run_once` in continuous/background orchestration, heartbeats, stop requests, lifecycle events, and daemon-friendly launch metadata.
- `agentic_trader/runtime_feed.py` writes small sidecar JSON feeds for status, events, stop requests, and chat history so UI surfaces can observe runtime state without owning DuckDB writer locks.
- `agentic_trader/runtime_status.py` derives user-facing runtime status and agent activity views from persisted service state and events.

## Agent Layer

- `agentic_trader/agents/coordinator.py` chooses the research focus for a cycle.
- `agentic_trader/agents/regime.py` classifies market regime from snapshot/context.
- `agentic_trader/agents/planner.py` chooses strategy family and action.
- `agentic_trader/agents/risk.py` sizes the plan and sets stop/take-profit levels.
- `agentic_trader/agents/manager.py` arbitrates specialist outputs, applies calibration, resolves conflicts, and determines final execution posture.
- `agentic_trader/agents/consensus.py` captures pre-manager specialist agreement/disagreement.
- `agentic_trader/agents/review.py` creates post-plan review notes.
- `agentic_trader/agents/operator_chat.py` handles operator-facing chat and safe preference instructions.
- `agentic_trader/agents/context.py` builds the shared agent context bundle from market state, memory, tool outputs, portfolio state, and upstream outputs.
- `agentic_trader/agents/constants.py` stores agent-level repeated text such as fallback reasons.

## Market, Memory, And Execution

- `agentic_trader/market/data.py` fetches or reads cached OHLCV data and normalizes yfinance output.
- `agentic_trader/market/features.py` computes the compact feature snapshot plus the first Market Context Pack, which makes the configured lookback window visible through multi-horizon summaries, data-quality flags, and coverage metadata.
- `agentic_trader/market/calendar.py` infers a lightweight market-session status for local runtime context.
- `agentic_trader/market/news.py` defines the optional tool-driven news/event feed boundary.
- `agentic_trader/memory/retrieval.py` retrieves historically similar runs for context injection.
- `agentic_trader/memory/embeddings.py` owns the lightweight vector-style document and similarity helpers.
- `agentic_trader/memory/policy.py` defines which actors may write to which memory domains.
- `agentic_trader/engine/guard.py` is the deterministic execution approval layer.
- `agentic_trader/engine/broker.py` defines the broker adapter boundary.
- `agentic_trader/engine/paper_broker.py` implements paper fills, positions, cash, journals, and position plans.
- `agentic_trader/engine/position_manager.py` manages open position exits bar by bar.

## Persistence And Schemas

- `agentic_trader/schemas.py` is the contract layer. Add new agent/runtime payload fields here before wiring them into storage or UI. `MarketContextPack` lives here so agents, storage, dashboards, and future UI clients share the same lookback-truth contract.
- `agentic_trader/storage/db.py` is the DuckDB persistence boundary. It stores runs, orders, fills, service state/events, preferences, memory vectors, trade context, and journals.
- `agentic_trader/config.py` centralizes environment-driven settings, runtime paths, runtime mode, provider routing, and directory setup.
- `agentic_trader/ui_text.py` is the first shared UI text catalog. Put repeated operator-facing labels/prompts here instead of duplicating them across CLI, Rich, Ink, and future WebUI surfaces.

## QA And Developer Tooling

- `scripts/qa/smoke_qa.py` is the terminal smoke harness. It checks installed CLI commands, Ink/Rich entrypoints, `python main.py`, optional `ruff`, `pytest`, `pyright`, coverage XML, and optional SonarQube submission.
- `.ai/qa/qa-smoke-script.md` documents how to run the smoke harness and where artifacts are written.
- `.ai/current-state.md`, `.ai/tasks.md`, and `.ai/decisions.md` should be updated when architecture or workflow assumptions change.
- `pyrightconfig.json` scopes static type checking to source, tests, and scripts while excluding generated/build/runtime artifacts.

## Documentation Conventions

- Prefer docstrings on public functions, public classes, CLI commands, and non-obvious private helpers.
- Keep trivial private helpers readable rather than mechanically documenting every single line.
- When a file owns a major subsystem, prefer a module docstring or an entry in this code map.
- If a new operator-facing label is repeated in more than one surface, add it to `agentic_trader/ui_text.py`.
