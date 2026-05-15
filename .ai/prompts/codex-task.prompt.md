Read these files before making changes, in priority order:

Core guardrails:

- AGENTS.instructions.md
- .ai/profile.instructions.md
- .ai/rules.instructions.md

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
state what context is unavailable, and continue from the remaining repository
evidence instead of inventing content.

Task input is supplied by the caller outside this template. Before acting,
restate the concrete task in one sentence. If the caller did not provide a
concrete task, stop after summarizing the missing input and ask for it.

Requirements:

Highest priority:

- preserve the existing architecture
- do not introduce an external orchestration framework
- keep the project local-first
- preserve strict runtime behavior

Implementation preferences:

- make the smallest coherent change
- follow existing naming and package boundaries
- explain changed files briefly
- update `.ai/current-state.instructions.md` or `.ai/decisions.instructions.md` if the change affects project assumptions

If constraints conflict, preserve architecture, local-first behavior, and strict
runtime gates before minimizing the patch size.
