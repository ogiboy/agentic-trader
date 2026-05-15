# Memory Retrieval Playbook

Use this when changing retrieval, memory injection, trade context, review,
traces, or memory UI surfaces.

If the memory database, vector index, replay artifact, or UI inspection surface
is unavailable, record the missing dependency and validate the fallback path
with deterministic fixtures or persisted sample rows. Do not claim learning or
retrieval success without a stored record and a prompt/context consumer.

## Required Contracts

- Retrieval outputs include why a memory was selected.
- Explanation payloads keep score components, freshness/as-of status, outcome
  tag, regime/strategy alignment, and diversity bucket when available.
- Trade memory and operator chat memory remain separate domains.
- Persistence stores enough explanation summary for replay and review.
- UI surfaces show explanation summaries without replacing structured evidence.

## Checks

- targeted unit tests for retrieval ranking/explanation
- agent context tests for prompt-facing summaries
- trade-context persistence tests
- CLI JSON smoke for memory/review surfaces
- Ink/Web display review when those surfaces changed
- advisory route/risk:
  - `ruflo route task "memory retrieval explanation change"`
  - `ruflo analyze diff --risk`
  - `ruflo analyze complexity agentic_trader/memory agentic_trader/agents`

## Edge Cases

- missing timestamp
- stale memory
- failed or blocked prior trade
- same-symbol duplicates
- no matching memory
- legacy vector rows with local-hashing metadata

When retrieval evidence conflicts with chat history, runtime traces, or stored
trade context, prefer the domain-specific trading memory contract for trading
decisions and keep operator chat memory explanatory only.

## Explanation Output Template

```text
Memory:
Why selected:
Score components:
Freshness/as_of:
Outcome tag:
Regime/strategy alignment:
Diversity bucket:
Operator surface:
```
