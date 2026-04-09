# Agent Instructions

This repository already contains its own trading-agent runtime.
Do not introduce an external orchestration framework or rewrite the project around a new agent platform.

When working in this repository, treat the existing codebase as the source of truth.

## Read Before Making Changes

Always read these files first:

- `README.md`
- `ROADMAP.md`
- `.ai/profile.md`
- `.ai/rules.md`
- `.ai/architecture.md`
- `.ai/current-state.md`
- `.ai/memory.md`
- `.ai/tasks.md`
- `.ai/decisions.md`

If the task is related to debugging or runtime behavior, also read:

- `.ai/debugging.md`

## Core Principles

- Keep the project local-first
- Preserve strict paper-trading discipline
- Prefer incremental changes over rewrites
- Preserve schema-first, execution-safe contracts
- Keep the runtime inspectable and deterministic where required
- Do not replace structured outputs with chatty free-form behavior
- Do not add hidden side effects to operator chat or instruction flows

## Existing Runtime Reality

This project already has:

- a staged specialist graph
- role-based model routing
- unified agent context assembly
- a lightweight memory layer
- DuckDB-backed storage
- CLI, monitor, and TUI surfaces
- background runtime support
- backtesting and replay surfaces

New work should extend those systems instead of bypassing them.

## Working Style

- Prefer minimal, targeted changes
- Preserve module boundaries
- Avoid speculative abstraction
- Avoid introducing new dependencies unless clearly justified
- Keep names explicit and domain-oriented
- Prefer extending current contracts over inventing parallel ones
- Update `.ai/current-state.md`, `.ai/tasks.md`, and `.ai/decisions.md` when a meaningful change is made

## Architecture Guardrails

- `agentic_trader/agents/` owns specialist and manager logic
- `agentic_trader/llm/` owns model/provider access and routing
- `agentic_trader/memory/` owns retrieval and memory assembly
- `agentic_trader/storage/` owns persistence
- `agentic_trader/engine/` and `agentic_trader/workflows/` own orchestration and runtime flow
- CLI/TUI surfaces should stay aligned with the same underlying contracts

## AI Assistant Behavior

When asked to implement something:

1. inspect the smallest relevant module surface
2. explain the intended change briefly
3. make the minimal code change
4. keep tests and typing in mind
5. update project memory files if the change affects architecture, workflow, or assumptions

## Do Not

- do not replace the current agent graph with a new framework
- do not add cloud-only assumptions to the main runtime
- do not silently weaken strict runtime gates
- do not hide behavior in prompts that should live in code or config
- do not turn operator chat into an uncontrolled execution path
