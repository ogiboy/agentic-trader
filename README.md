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

## Architecture

The first strict runtime uses three LLM agents:

1. `Regime Agent`
   Classifies the market state from recent price/volume features.
2. `Trade Planner Agent`
   Chooses a strategy family and proposes a directional trade plan.
3. `Risk Agent`
   Sets position sizing, stop loss, take profit, and invalidation logic.

Those outputs are then passed to:

4. `Execution Guard`
   Rejects low-confidence or poor-risk proposals.
5. `Paper Broker`
   Records simulated orders, fills, account state, and open positions into DuckDB.

## Stack

- Python `3.13+`
- `Pydantic` for contracts and validation
- `Typer` for CLI
- `httpx` against Ollama's native HTTP API
- `yfinance` for initial market data
- `DuckDB` for event and order storage

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

Smoke check the environment:

```bash
python main.py doctor
```

Run a single strict paper-trade cycle:

```bash
python main.py run --symbol AAPL --interval 1d --lookback 180d
```

Open the root launcher and control room:

```bash
python main.py
```

Attach to the live monitor:

```bash
python main.py monitor --refresh-seconds 1.0
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

Export the latest run review as Markdown:

```bash
python main.py export-report --output runtime/latest-run-review.md
```

Run a walk-forward backtest with the current agent pipeline:

```bash
python main.py backtest --symbol AAPL --interval 1d --lookback 2y --warmup-bars 120
```

Inspect orchestrator runtime state and recent events:

```bash
python main.py status
python main.py logs --limit 20
```

## Notes

- This project starts with paper trading only.
- The trading runtime is strict by default: if Ollama or the configured model is unavailable, the core runtime should not start.
- Deterministic fallbacks are kept for diagnostics, not for silent trade generation in the main launcher.
- The main menu is intended to become the long-running operator surface for preferences, logs, start/stop controls, and runtime visibility.
- Live broker adapters can be added once the planning and portfolio pipeline behaves consistently.

## Near-Term Direction

- deepen the control room with a denser live dashboard and richer operator workflows
- keep growing the specialist + manager orchestration layer with more portfolio-aware reasoning
- add backtesting and replay so journaled decisions can be scored against deterministic baselines
- keep the runtime daemon-capable so the TUI can attach to a long-running service instead of owning it directly
