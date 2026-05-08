# Strategy Research Pack

This folder contains repo-native strategy research guidance for Agentic Trader.
It is not a runtime strategy engine and does not import external strategy code.

Use it with:

- `.ai/agents/market-strategist.md`
- `.ai/playbooks/strategy-research-and-sweeps.md`
- `.ai/playbooks/news-intelligence.md`
- `agentic_trader/finance/ideas.py`
- `agentic_trader/backtest/`
- proposal and broker-adapter contracts

## Ground Rules

- V1 strategy work is US-equities, paper-first, and manual-review only.
- Scanner output is research/watch evidence until converted into a pending
  proposal.
- No strategy may approve, execute, or mutate broker settings.
- Every strategy idea needs data requirements, freshness checks, risk/sizing
  assumptions, and validation evidence.
- Raw web/news/social text is not strategy input; normalized evidence is.
- Backtests must preserve data windows and avoid lookahead.

## Current Durable Catalog

Read `v1-strategy-catalog.md` before adding scanner presets, backtest baselines,
or proposal-enrichment logic.
