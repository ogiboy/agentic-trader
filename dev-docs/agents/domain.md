# Domain Docs

Agentic Trader is a single-context product: the Python runtime, Web GUI, docs
site, TUI, QA scripts, and `.ai` guidance all support the same local-first
paper-trading system.

## Current Sources Of Truth

Read these before using architecture, diagnosis, TDD, PRD, or issue-writing
skills:

- `README.md`
- `ROADMAP.md`
- `AGENTS.instructions.md`
- `.ai/profile.instructions.md`
- `.ai/rules.instructions.md`
- `.ai/architecture.instructions.md`
- `.ai/current-state.instructions.md`
- `.ai/tasks.instructions.md`
- `.ai/decisions.instructions.md`
- `.ai/workflows/README.instructions.md`
- `.ai/workflows/external-tooling-policy.instructions.md`

For QA, runtime, broker, Web GUI, setup, security, or operator-surface work,
also read the relevant `.ai/qa/`, `.ai/playbooks/`, `.ai/agents/`, and
`.ai/security/` guidance.

## Target Layout

The preferred long-term domain-doc layout is single-context:

```text
/
├── CONTEXT.md
└── docs/adr/
```

`CONTEXT.md` and `docs/adr/` do not exist yet. Proceed using the current sources
of truth above, and create those missing domain-doc artifacts only when a
dedicated documentation or ADR task asks for them.

## Vocabulary Rules

Use the project's existing terms:

- local-first
- paper-first
- strict runtime gates
- manual-review trade proposals
- broker adapter boundary
- V1 US equities / Alpaca readiness
- V2 Turkey expansion
- operator-visible evidence
- research sidecar as evidence companion

Do not describe V1 as a passive demo. V1 is intended to be active-trading
capable through approved, auditable paper/external-paper paths once readiness
gates pass.

## ADR Conflicts

If future `docs/adr/` files exist and your proposed change contradicts one,
surface the contradiction explicitly instead of silently overriding the
decision.
