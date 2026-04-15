[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=ogiboy_agentic-trader&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=ogiboy_agentic-trader)


```text
 █████╗  ██████╗ ███████╗███╗   ██╗████████╗██╗ ██████╗    ████████╗██████╗  █████╗ ██████╗ ███████╗██████╗
██╔══██╗██╔════╝ ██╔════╝████╗  ██║╚══██╔══╝██║██╔════╝    ╚══██╔══╝██╔══██╗██╔══██╗██╔══██╗██╔════╝██╔══██╗
███████║██║  ███╗█████╗  ██╔██╗ ██║   ██║   ██║██║            ██║   ██████╔╝███████║██║  ██║█████╗  ██████╔╝
██╔══██║██║   ██║██╔══╝  ██║╚██╗██║   ██║   ██║██║            ██║   ██╔══██╗██╔══██║██║  ██║██╔══╝  ██╔══██╗
██║  ██║╚██████╔╝███████╗██║ ╚████║   ██║   ██║╚██████╗       ██║   ██║  ██║██║  ██║██████╔╝███████╗██║  ██║
╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚═╝  ╚═══╝   ╚═╝   ╚═╝ ╚═════╝       ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝╚═════╝ ╚══════╝╚═╝  ╚═╝
```

# Agentic Trader

> Strict, local-first, multi-agent paper trading for Ollama-class models.

Agentic Trader is a strict, local-first, multi-agent paper trading system designed for Ollama-class models such as Qwen.

The core idea is simple:

- agents decide market regime, strategy family, and risk plan
- a deterministic guard decides whether a trade proposal is allowed
- a paper broker records the simulated order
- every run is logged so we can measure what the system is actually doing

This is intentionally not a "chatty report generator." The system is built around structured outputs and execution-safe contracts.

The runtime also has an explicit mode contract. The default `operation` mode is still paper-first and requires strict LLM gating plus provider/model readiness before one-shot, launch, or service execution can proceed. `training` mode is reserved for replay/backtest evaluation and may use diagnostic fallback there without enabling hidden trade generation in the live paper runtime.

## Architecture

The current strict runtime uses a staged specialist graph:

1. `Research Coordinator`
   Sets cycle focus, priority signals, and caution flags.
2. `Regime Agent`
   Classifies the market state from recent price and volume features.
3. `Strategy Selector`
   Chooses a strategy family and directional action.
4. `Risk Agent`
   Sets position sizing, stop loss, take profit, and invalidation logic.
5. `Manager Agent`
   Combines specialist outputs into a final execution posture.
6. `Execution Guard`
   Rejects low-confidence or poor-risk proposals.
7. `Paper Broker`
   Records simulated orders, fills, account state, position plans, and journals into DuckDB.

Every agent cycle now receives a unified context bundle that can include:

- the current market snapshot
- a Market Context Pack with lookback coverage, multi-horizon returns, volatility, drawdown, trend votes, range structure, and data-quality flags
- operator preferences
- portfolio state
- recent run summaries
- trade-journal memory hints
- upstream agent outputs

If the fetched market data materially under-covers the requested lookback window in operation/runtime flows, snapshot generation fails before any agents run. That keeps a `180d` or `1y` request from silently becoming a short-window decision. Training replay can still use growing windows, but the context pack keeps that undercoverage visible as data quality context.

The LLM layer also supports role-based model routing, so different local models can be assigned to coordinator, regime, strategy, risk, manager, explainer, and instruction parsing roles.

The current memory layer is still lightweight, but it can already retrieve historically similar recorded runs and inject those summaries into agent context before a cycle. Memory documents now also include the Market Context Pack summary so later retrieval can reason about the broader lookback, not only the latest indicator row. Stored memory vectors include embedding provider, model, version, and dimensionality metadata so future semantic embeddings can migrate without hiding how old memories were produced.

## Stack

- Python `3.12+` (currently exercised with a Conda `3.14` environment)
- `Pydantic` for contracts and validation
- `Typer` for CLI
- `Rich` for the legacy/admin control room
- `Ink` + React for the primary terminal control room
- `httpx` against Ollama's native HTTP API
- `yfinance` for initial market data
- `DuckDB` for event and order storage
- `ruff`, `pytest`, `pyright`, and optional SonarQube/`pysonar` for local QA

## Quick Start

Create and activate a project-local Conda environment:

```bash
conda create -n trader python=3.14
conda activate trader
```

Install the project:

```bash
python -m pip install -e ".[dev]"
```

Install the Ink control-room dependencies if you want the primary terminal UI:

```bash
cd tui
npm install
cd ..
```

If you want the installed console entrypoint instead of the root launcher, it is:

```bash
agentic-trader doctor
```

If your shell resolves `pip` to a different Python, prefer `python -m pip` so the active interpreter and installer always match.

Set Ollama settings if you want to override defaults:

```bash
export AGENTIC_TRADER_MODEL=qwen3:8b
export AGENTIC_TRADER_BASE_URL=http://localhost:11434/v1
```

Optional per-role model routing overrides:

```bash
export AGENTIC_TRADER_REGIME_MODEL_NAME=qwen3:8b
export AGENTIC_TRADER_RISK_MODEL_NAME=qwen3:14b
export AGENTIC_TRADER_EXPLAINER_MODEL_NAME=llama3.1:8b
```

Smoke check the environment:

```bash
python main.py doctor
```

Run a single strict paper-trade cycle:

```bash
python main.py run --symbol AAPL --interval 1d --lookback 180d
```

Open the root launcher. By default this launches the primary Ink control room when the Node dependencies under `tui/` are installed:

```bash
agentic-trader
```

The Python root launcher is still available:

```bash
python main.py
```

Open the legacy Rich/admin menu:

```bash
agentic-trader menu
```

Attach to the live monitor:

```bash
python main.py monitor --refresh-seconds 1.0
```

Open the Ink-based next-generation control room:

```bash
agentic-trader tui
```

Ink control room hotkeys:

```text
1 overview   2 runtime   3 portfolio   4 review   5 memory   6 chat
r refresh    s start background runtime    x stop runtime    q quit
[ and ] switch chat persona on the chat page
```

Start the runtime directly from the root launcher:

```bash
python main.py launch --symbols AAPL,MSFT --interval 1d --lookback 180d
```

Run continuously:

```bash
python main.py launch --symbols AAPL,MSFT --interval 1d --lookback 180d --continuous --poll-seconds 300
```

Run continuously in the background:

```bash
python main.py launch --symbols AAPL,MSFT --interval 1d --lookback 180d --continuous --background
python main.py status
python main.py logs --limit 20
python main.py stop-service
```

Talk to the built-in operator chat:

```bash
python main.py chat --persona operator_liaison --message "What is the runtime doing right now?"
```

Parse a safe operator instruction and optionally apply it:

```bash
python main.py instruct --message "Switch the system to a more conservative, explanatory posture" --apply
```

Inspect the paper portfolio:

```bash
python main.py portfolio
```

Inspect the trade journal:

```bash
python main.py journal --limit 20
```

Inspect the daily paper risk report:

```bash
python main.py risk-report
```

Inspect the latest persisted run in detail:

```bash
python main.py review-run
```

Inspect the per-stage agent trace for the latest run:

```bash
python main.py trace-run
```

Export the latest run review as Markdown:

```bash
python main.py export-report --output runtime/latest-run-review.md
```

Inspect historically similar recorded runs for the current snapshot:

```bash
python main.py memory-explorer --symbol AAPL --interval 1d --lookback 180d --limit 5
```

Inspect which retrieved memories and context bundles were attached to each agent stage:

```bash
python main.py retrieval-inspection
```

Inspect inferred market session state:

```bash
python main.py calendar-status --symbol THYAO.IS
```

Manage repeatable market snapshot cache:

```bash
python main.py cache-market-data --symbol AAPL --interval 1d --lookback 180d
python main.py market-cache --json
```

Run a walk-forward backtest with the current agent pipeline:

```bash
python main.py backtest --symbol AAPL --interval 1d --lookback 2y --warmup-bars 120
```

Compare the agent replay against a deterministic baseline:

```bash
python main.py backtest --symbol AAPL --interval 1d --lookback 2y --warmup-bars 120 --compare-baseline
```

Backtests run under the same runtime mode contract as the rest of the system. In `operation` mode, provider/model readiness must pass. In `training` mode, backtest/evaluation commands can fall back to deterministic diagnostics when the model is unavailable, but `run`, `launch`, and background service execution remain strict.

Replay artifacts also carry timing boundaries: market snapshots include `as_of`, and backtest reports include data-window plus first/last decision timestamps so future-data leakage can be audited.

Check the approved mode-transition plan before moving between Training and Operation:

```bash
python main.py runtime-mode-checklist operation
python main.py runtime-mode-checklist training --json
```

This command reports a schema-backed checklist only. Runtime mode changes still require explicit configuration; operator chat and free-form instructions cannot silently mutate execution policy.

Inspect orchestrator runtime state and recent events:

```bash
python main.py status
python main.py logs --limit 20
```

Machine-readable status surfaces for future UI shells:

```bash
agentic-trader doctor --json
agentic-trader status --json
agentic-trader logs --json --limit 8
agentic-trader preferences --json
agentic-trader portfolio --json
```

## QA And Code Quality

Developer orientation notes live in [docs/dev/code-map.md](docs/dev/code-map.md).

Fast checks:

```bash
python -m ruff check .
pyright
python -m pytest -q -p no:cacheprovider
node --check tui/index.mjs
```

Terminal smoke checks:

```bash
python scripts/qa/smoke_qa.py
python scripts/qa/smoke_qa.py --include-quality
```

Full local QA with SonarQube submission:

```bash
SONAR_TOKEN=... python scripts/qa/smoke_qa.py --include-quality --include-sonar
```

Smoke artifacts are written to timestamped folders under:

```text
.ai/qa/artifacts/smoke-YYYYMMDD-HHMMSS/
```

The current QA harness validates installed CLI entrypoints, the primary Ink TUI, `python main.py`, the Rich menu, read-only JSON status surfaces, optional coverage XML generation, `pyright`, and optional `pysonar` submission. SonarQube may still report a failing Quality Gate while coverage and remaining complexity refactors are being improved; the latest local cleanup reduced open code smells from `20` to `8`.

## Notes

- This project starts with paper trading only.
- The trading runtime is strict by default: if Ollama or the configured model is unavailable, the core runtime should not start.
- Deterministic fallbacks are kept for diagnostics and Training-mode evaluation, not for silent trade generation in the main launcher or background runtime.
- The Ink control room is the primary terminal operator surface; the Rich menu remains useful as a legacy/admin fallback.
- UI text is starting to move behind a shared catalog so CLI, Rich, Ink, and a future WebUI can grow toward multi-language support without duplicating labels.
- Live broker adapters can be added once the planning and portfolio pipeline behaves consistently.

## Near-Term Direction

- reduce the remaining Sonar complexity issues in `tui.py`, `service.py`, `walk_forward.py`, and service-state persistence
- add focused coverage around storage service-state transitions, runtime-control paths, and operator surfaces
- keep Ink, Rich, CLI, and future WebUI surfaces attached to the same daemon/status contracts
- continue evolving memory retrieval and inspection while keeping memory writes policy-controlled and reviewable
- preserve paper trading as the default until backtest and journal evidence justify any live adapter work
