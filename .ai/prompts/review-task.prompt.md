Review the recent implementation for Agentic Trader.

Read, in priority order:

Core guardrails:

- AGENTS.instructions.md
- .ai/rules.instructions.md

Current project state:

- README.md
- ROADMAP.md
- .ai/architecture.instructions.md
- .ai/current-state.instructions.md
- .ai/decisions.instructions.md

Workflow guidance:

- .ai/workflows/README.instructions.md
- .ai/workflows/external-tooling-policy.instructions.md

If any listed file is missing, renamed, or incomplete, report the path and
continue the review from available source, tests, and runtime contracts.

Focus input is supplied by the caller outside this template. Before reviewing,
restate the concrete focus in one sentence. If the caller did not provide a
specific focus, review the changed files for correctness, safety, tests, and
operator-visible behavior.

Check:

1. correctness, security, and strict runtime behavior
2. architectural fit and local-first assumptions
3. existing module boundaries
4. memory, routing, or operator-facing behavior that changed unexpectedly
5. missing tests, docs, or QA evidence

Return:

1. what changed
2. what is correct
3. what is risky
4. what should be cleaned up next
