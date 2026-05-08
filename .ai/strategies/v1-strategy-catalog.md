# V1 Strategy Catalog

This catalog translates benchmark strategy ideas into Agentic Trader's current
V1 contracts. It is intentionally conservative: strategy ideas become scanner
scores, backtest baselines, or pending proposals, not direct execution.

## Current Product Status

Already implemented:

- deterministic idea-scanner presets for `momentum`, `gap-up`, `gap-down`,
  `mean-reversion`, `breakout`, and `volatile`
- runtime strategy metadata through `agentic-trader strategy-catalog`,
  `agentic-trader strategy-profile`, and `idea-score` readiness context
- runtime news/materiality planning through `agentic-trader news-intelligence`
- runtime cycle contract through `agentic-trader research-cycle-plan`
- manual-review proposal queue
- paper/external-paper broker adapter boundary
- Market Context Pack with lookback coverage and quality flags
- daily risk report with first HHI/top-position concentration visibility
- finance ledger/reconciliation categories in `finance-ops`

Still needed before strategy output feels desk-grade:

- provider/news/fundamental enrichment before proposal creation
- liquidity/ADV/spread and stale-mark penalties
- ATR/confidence sizing
- group/sector budgets and correlation warnings
- backtest confidence intervals and lookahead checks
- operator review UX across CLI/Rich/Ink/Web

## Strategy Families

### Momentum Continuation

Intent: join liquid names already moving with volume and trend alignment.

Required evidence:

- positive return over scan window
- relative volume
- price above short moving average
- RSI below exhaustion zone
- no fresh high-materiality negative catalyst

V1 mapping:

- current `momentum` preset
- proposal only after news/materiality and liquidity enrichment

Risk caveats:

- false continuation after opening exhaustion
- high spread or thin ADV
- stale news catalyst

### Gap-Up Review

Intent: identify a gap that may continue when volume and catalyst quality are
strong enough.

Required evidence:

- opening gap %
- current change %
- relative volume
- RSI headroom
- fresh catalyst or official disclosure
- spread and halt status

V1 mapping:

- current `gap-up` preset
- add catalyst freshness before proposal handoff

Risk caveats:

- gap fade
- low liquidity at open
- missing or stale catalyst

### Gap-Down Review

Intent: distinguish "avoid/sell pressure" from possible oversold reversal.

Required evidence:

- negative gap %
- RSI and distance from averages
- event type causing the gap
- volume and spread
- source tier and freshness

V1 mapping:

- current `gap-down` preset
- output should be watch/sell-bias research unless a proposal thesis includes
  explicit invalidation and catalyst analysis

Risk caveats:

- catching falling knife
- hidden downgrade/legal/accounting catalyst
- halted or illiquid symbol

### Mean Reversion

Intent: find liquid oversold names likely to revert toward average/VWAP.

Required evidence:

- RSI or z-score style oversold condition
- distance from SMA/VWAP/Bollinger-style band
- no fresh adverse high-materiality event
- spread and volume acceptable

V1 mapping:

- current `mean-reversion` preset
- news veto is mandatory before proposal creation

Risk caveats:

- adverse catalyst invalidates statistical reversion
- trend day can keep extending

### Breakout / Reclaim

Intent: detect price reclaiming VWAP or clearing moving-average structure with
volume confirmation.

Required evidence:

- VWAP or moving-average reclaim
- relative volume
- range/volatility context
- invalidation level under reclaim/range

V1 mapping:

- current `breakout` preset
- future extension: explicit reclaim subtype and invalidation guidance

Risk caveats:

- false breakout
- late entry after move already extended

### Volatile Watchlist

Intent: surface high-range names for review without treating volatility as
conviction.

Required evidence:

- intraday range %
- relative volume
- spread
- catalyst/source context

V1 mapping:

- current `volatile` preset
- watch-only by default

Risk caveats:

- slippage, wide spread, news uncertainty

### Opening Range Breakout / Fade

Intent: study first-session range behavior for intraday proposals.

Required evidence:

- session calendar and timezone
- first range high/low
- entry window
- volume confirmation
- close-by-time or max-hold rule

V1 mapping:

- research/backtest candidate
- do not queue proposals until session/timezone and no-lookahead tests exist

Risk caveats:

- timezone/session drift
- synthetic future range leaks
- EOD flattening behavior not shared across all surfaces

### VWAP Reclaim / Reversion

Intent: use session VWAP as a fair-value anchor.

Required evidence:

- session VWAP
- volume confirmation
- dip/gap context
- time window
- zero-volume handling

V1 mapping:

- research/backtest candidate
- possible future scanner subtype under breakout or mean reversion

Risk caveats:

- stale VWAP
- low-volume artifacts
- weak session handling in daily-only data

### Keltner / Bollinger Bands

Intent: compare volatility-band breakout and reversion behavior.

Required evidence:

- ATR or rolling standard deviation
- band width
- volume confirmation
- trend/regime context

V1 mapping:

- research/backtest candidate
- useful for deterministic baselines and parameter sweeps

Risk caveats:

- overfit periods/multipliers
- band signals without liquidity/news context

### Pairs Z-Score

Intent: trade spread reversion between correlated symbols.

V1 mapping:

- defer to V2 unless shorting, hedge accounting, correlation windows, and
  multi-leg proposal review are implemented

Risk caveats:

- current V1 broker/accounting surfaces are long-biased and proposal records are
  single-symbol

### Regime Adaptive

Intent: choose momentum or mean reversion based on market regime.

Required evidence:

- regime feature with no lookahead
- branch-specific entry/exit
- neutral/sit-out behavior
- confidence cap when regime is weak

V1 mapping:

- research candidate and future agent/manager input
- no hidden policy mutation

Risk caveats:

- fitting the regime on full future history
- hiding branch disagreement

### Ensemble Voting

Intent: require multiple simple signals to agree before raising confidence.

Required evidence:

- per-signal reasons
- weights
- disagreement output
- confidence cap

V1 mapping:

- research candidate for proposal enrichment
- should make disagreement visible rather than compressing everything into one
  opaque score

Risk caveats:

- false precision
- hidden correlated indicators

## Acceptance Criteria For New Strategy Work

- deterministic unit tests for score direction and warnings
- no-lookahead test for any full-window indicator path
- freshness and missing-data behavior documented
- proposal handoff keeps manual approval
- risk/sizing assumptions visible
- docs and `.ai` guidance updated if operator workflow changes
