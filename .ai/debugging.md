# Debugging Notes

## Debugging Priorities

1. preserve runtime truth
2. identify the smallest failing boundary
3. verify whether the issue is:
   - data input
   - Market Context Pack generation
   - market feature generation
   - provider aggregation or canonical analysis snapshot generation
   - decision feature bundle generation
   - fundamental or macro/news feature scaffolds
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
- If runtime mode is Operation, is strict LLM gating enabled before provider/model checks run?
- If runtime mode is Training, is any deterministic fallback limited to a backtest/evaluation command?
- What does `runtime-mode-checklist` report for the target mode, and which blocking checks failed?
- Was the configured model available?
- Which model was routed for this role?
- Which runtime mode was active: Training or Operation?
- What Market Context Pack was generated, and did its bars/window coverage match the requested lookback?
- What Decision Feature Bundle was attached, and did it include symbol identity plus technical, fundamental, and macro context?
- What Canonical Analysis Snapshot was attached, and which provider sections were missing, stale, fallback, or inferred?
- Did the prompt render compact summaries, or did raw persisted runtime/provider JSON leak into the agent-facing context?
- Was the LLM call using Ollama schema format, or did it fall back to plain JSON mode?
- If no-trade risk output shows odd price levels, did the risk finalizer normalize reference stop/take levels around the latest close?
- If no agents ran, did Market Context Pack generation fail closed because coverage was below the safety threshold?
- What `as_of` timestamp did the snapshot carry, and did replay decisions stay within the first/last decision timestamps reported by the backtest?
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
- inspect `.ai/qa/artifacts/<run>/runtime_cycle.log` after opt-in runtime smoke checks
- change one thing at a time
- document meaningful findings in `.ai/decisions.md`
