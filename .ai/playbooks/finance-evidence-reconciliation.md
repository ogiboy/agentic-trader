# Finance Evidence Reconciliation Playbook

Use this playbook when improving account, broker, portfolio, PnL, fills,
reporting, fees, slippage, tax/fee placeholders, or finance-ops surfaces.

## Goal

Make operator-facing financial truth reconcile like a small trading desk:

- account state
- cash and buying power
- equity and net liquidation
- positions and cost basis
- fills and order status
- fees, commissions, and slippage assumptions
- realized/unrealized/daily PnL
- risk, exposure, and concentration
- source, mark time, and stale status

## Evidence Sources

| Evidence | Preferred Source | Missing-State Behavior |
| --- | --- | --- |
| Broker backend | settings and broker adapter status | show backend unavailable or disabled |
| Account/cash/equity | broker account snapshot or paper account store | mark unavailable, do not infer from orders |
| Positions | broker/paper position store | show zero only when source confirms zero |
| Fills/orders | execution outcomes and fill journal | preserve rejected/partial/simulated status |
| Fees/slippage | broker fill fields or configured cost model | show assumption, not fact |
| PnL | account marks plus fills/positions | show source and timestamp |
| Exposure/HHI | daily risk report or computed portfolio snapshot | show unavailable when report missing |
| External broker health | explicit adapter health/preflight | keep separate from local paper health |

## Reconciliation Questions

1. Does every displayed number have a source?
2. Is the timestamp visible?
3. Is the currency visible?
4. Is the sign convention clear?
5. Are fees and slippage actual, estimated, or unavailable?
6. Can a rejected or partial order be confused with a fill?
7. Can simulated paper fills be confused with external paper fills?
8. Can a missing mark look like a clean zero?
9. Does the same truth appear in CLI, dashboard, observer, Rich, Ink, Web GUI,
   and evidence bundles?
10. Does the proposal audit chain connect to the broker outcome?

## Reporting Lessons To Carry Forward

When external broker statements or flex-style reports become relevant, ingest
them as ledger evidence, not UI decoration:

- trades
- dividends
- fees and taxes
- cash deposits/withdrawals
- interest
- corporate actions
- currency
- security identifiers
- split adjustments

V1 is Alpaca-paper-oriented, so IBKR/TWS/Flex workflows are V2 unless the
roadmap explicitly pulls them forward. The accounting pattern is still useful:
separate ledger categories, preserve original source ids, and reconcile derived
portfolio statistics from those ledgers.

## Negative Tests

Add tests for:

- missing account snapshot
- stale quote/mark timestamp
- rejected order
- partial fill shape
- fee unavailable versus zero fee
- paper versus external paper label
- live backend blocked
- proposal approval failure updates proposal status
- evidence bundle includes finance-ops payload

## Output Format

```text
Surface:
Field:
Source:
Timestamp:
Currency/sign:
Missing/stale behavior:
Risk if wrong:
Test:
```
