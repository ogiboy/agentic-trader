You are planning work for the Agentic Trader repository.

Read, in priority order:

Core guardrails:

- AGENTS.instructions.md
- .ai/profile.instructions.md

Current project state:

- README.md
- ROADMAP.md
- .ai/architecture.instructions.md
- .ai/current-state.instructions.md
- .ai/tasks.instructions.md
- .ai/decisions.instructions.md

Workflow guidance:

- .ai/workflows/README.instructions.md
- .ai/workflows/external-tooling-policy.instructions.md

If any listed file is missing, renamed, or incomplete, name the exact path,
explain how that limits the plan, and continue using the remaining evidence.

Goal input is supplied by the caller outside this template. Before planning,
restate the concrete goal in one sentence. If the caller did not provide a
concrete goal, return a short missing-input note and ask for it.

Produce:

1. a short diagnosis of the current relevant architecture
2. the smallest safe implementation plan
3. the files most likely to change
4. risks or edge cases
5. a suggested Codex task prompt

Prioritize implementation decisions that preserve strict runtime gates,
local-first setup, and existing module boundaries.
