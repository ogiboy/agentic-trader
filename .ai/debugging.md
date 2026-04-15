# Debugging Notes

## Debugging Priorities

1. preserve runtime truth
2. identify the smallest failing boundary
3. verify whether the issue is:
   - data input
   - Market Context Pack generation
   - market feature generation
   - Training vs Operation mode gating
   - model/provider access
   - memory retrieval
   - specialist output contract
   - manager merge logic
   - execution guard logic
   - broker persistence
   - CLI/TUI presentation only

## Common Questions To Ask

- Is the runtime in strict mode?
- Was the configured model available?
- Which model was routed for this role?
- Which runtime mode was active: Training or Operation?
- What Market Context Pack was generated, and did its bars/window coverage match the requested lookback?
- What memory context was attached?
- Why were the retrieved memories selected?
- Did the issue happen before or after manager synthesis?
- Did the guard reject the proposal for a valid reason?
- Is this a logic issue or only a display issue?
- Is the persisted trace consistent with the operator surface?

## Debugging Style

- reproduce first
- inspect persisted traces
- inspect the persisted context pack and retrieval explanations
- inspect runtime status/log surfaces
- change one thing at a time
- document meaningful findings in `.ai/decisions.md`
