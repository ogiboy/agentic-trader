# Agentic Trader

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

Start the runtime directly from the root launcher:

```bash
python main.py launch --symbols AAPL,MSFT --interval 1d --lookback 180d
```

Run continuously:

```bash
python main.py launch --symbols AAPL,MSFT --interval 1d --lookback 180d --continuous --poll-seconds 300
```

Inspect the paper portfolio:

```bash
python main.py portfolio
```

## Notes

- This project starts with paper trading only.
- The trading runtime is strict by default: if Ollama or the configured model is unavailable, the core runtime should not start.
- Deterministic fallbacks are kept for diagnostics, not for silent trade generation in the main launcher.
- The main menu is intended to become the long-running operator surface for preferences, logs, start/stop controls, and runtime visibility.
- Live broker adapters can be added once the planning and portfolio pipeline behaves consistently.
