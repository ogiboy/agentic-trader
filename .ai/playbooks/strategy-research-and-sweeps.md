# Strategy Research And Sweeps Playbook

Use this playbook when adding scanner presets, deterministic strategy logic,
backtest comparisons, parameter sweeps, or V1 proposal-enrichment work.

The project does not currently import a standalone strategy-engine framework.
Treat strategies as research hypotheses that feed existing feature, backtest,
idea-scanner, guard, and proposal contracts.

## Strategy Development Sequence

1. Define the strategy family and intended market behavior.
2. List required bars, provider fields, and market-session assumptions.
3. Write the entry, exit, and invalidation contract in plain language.
4. Identify safety gates: liquidity, spread, stale data, exposure, HHI,
   position count, kill switch, paper backend.
5. Decide whether this is an idea-scanner preset, an agent strategy-family hint,
   a backtest baseline, or a future strategy module.
6. Add a focused deterministic test before expanding surfaces.
7. Run a backtest or comparison only after the data window and lookahead rules
   are explicit.
8. If the idea can act, create a pending proposal; do not execute.

## V1 Strategy Catalog

| Strategy | V1 Treatment | Key Inputs | Main Risk |
| --- | --- | --- | --- |
| Momentum continuation | Existing scanner preset, can be enriched | return %, relative volume, EMA/SMA alignment, RSI headroom | chasing exhaustion |
| Gap-up review | Existing scanner preset, needs catalyst/freshness enrichment | gap %, change %, volume, RSI, news/event | opening liquidity and reversal |
| Gap-down review | Existing scanner preset, should distinguish reversal watch vs sell/avoid | gap %, RSI, moving-average distance, catalyst | catching falling knife |
| Mean reversion | Existing scanner preset, needs news veto | RSI, Bollinger/SMA/VWAP distance, volume | adverse catalyst invalidates mean reversion |
| Breakout/reclaim | Existing scanner preset, should add invalidation | VWAP, EMA/SMA, volume, prior range | false breakout |
| Volatile watchlist | Existing scanner preset, should stay watch-only by default | range %, relative volume, spread | high slippage and weak conviction |
| Opening range breakout/fade | Research candidate | first range high/low, session clock, volume | session/timezone errors and lookahead |
| VWAP reclaim/reversion | Research candidate | session VWAP, volume, time window, dip/gap context | stale VWAP or zero-volume bars |
| Keltner/Bollinger | Research candidate | ATR, EMA/SMA, band width, volume | overfit band parameters |
| Pairs z-score | V2 unless shorting/hedge contracts mature | spread, hedge ratio, correlation, z-score | shorting/accounting support |
| Regime adaptive | V1 research, not hidden policy | regime feature, trend/reversion branch, confidence cap | fitting regime with future data |
| Ensemble voting | V1 research candidate | per-signal scores, weights, conflicts | hiding disagreement behind one score |

## Fast Indicator Rules

For long backtests, compute indicator arrays once and read by index. Avoid
per-bar recomputation of expensive libraries.

Safe patterns:

- pandas `rolling()` or `ewm()`
- numpy arrays materialized once
- grouped cumulative VWAP by session/day
- O(1) reads in per-bar loops

Unsafe patterns:

- Python loops inside precompute over every bar when vectorization is possible
- centered rolling windows
- `shift(-1)` or future-label features
- global normalization using the full future series
- fitting regime or scaler models on the complete backtest history

## No-Lookahead Contract

Any backtest strategy that sees a full dataframe must prove values at index `i`
depend only on bars `0..i`.

Add checks that compare:

- full-history precompute output
- truncated-history precompute output at the same past index

The value should not change when future bars disappear.

## Sweep Plan Template

```yaml
sweeps:
  - name: v1_momentum_liquid_us
    family: momentum
    symbols: [SPY, QQQ, AAPL, MSFT, NVDA]
    data_window: 365d
    interval: 1d
    params:
      relative_volume: [1.5, 2.0, 3.0]
      rsi_max: [70, 75, 80]
    checks:
      - no_lookahead
      - stale_data
      - spread_cap
      - drawdown
      - loss_streak
      - bootstrap_confidence
```

Keep sweep manifests declarative. Dry-run the job count and wall-time estimate
before launching anything expensive.

## Confidence Review

A strong backtest should report more than raw return:

- win rate
- expectancy
- max drawdown
- exposure
- loss streak
- trade count
- profit factor
- probabilistic Sharpe or equivalent confidence signal
- bootstrap confidence interval
- data-window and decision-window timestamps
- stale-data and lookahead checks

If confidence is thin, the output can still be useful as watchlist research, but
it should not become a proposal automatically.

## Detached Long Runs

For long local sweeps, do not block the interactive session with an opaque
process. Use the repo's explicit QA/runtime conventions instead:

- write stdout/stderr to a known artifact path
- record command, start time, expected inputs, and expected output
- poll status through a small JSON/markdown summary
- keep partial failures visible
- do not start hidden daemons or write untracked state without approval

## Proposal Handoff

When a strategy candidate passes review, the handoff is a pending proposal:

```text
source=scanner|research-sidecar|manual
thesis=<strategy family + evidence>
confidence=<bounded by test/evidence quality>
reference_price=<mark source and timestamp>
stop_loss|invalidation_condition=<required>
take_profit=<optional>
review_notes=<freshness, materiality, liquidity, concentration caveats>
```

Approval is a separate operator action. The strategy research layer does not
call broker adapters.
