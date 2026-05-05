# Multi-Agent Handoff

Use this only for development collaboration. It must not be confused with the
runtime specialist graph inside `agentic_trader/`.

## When To Split Work

Use multiple agents when:

- the user explicitly allows multi-agent work
- subtasks are independent enough to avoid write conflicts
- one agent can research while another implements a disjoint surface
- security, QA, release, or performance review can run in parallel with
  implementation
- the task touches several domains such as WebGUI plus Python runtime plus docs

Keep work local when:

- the next action is blocked on one result
- the task is a small one-file fix
- the write scope is ambiguous
- the change touches a sensitive contract that needs one owner

## Safe Role Splits

| Task | Primary | Sidecar Agents |
| --- | --- | --- |
| Feature | implementer | researcher, QA, reviewer |
| Security | security-auditor | QA, reviewer |
| Release/PR | release-manager | QA, reviewer |
| Performance | performance-engineer | implementer, QA |
| Docs/operator guide | product-docs | operator-ux, QA |
| Broker/accounting | finance-ops | data, QA, reviewer |

## Advisory Routing Commands

```bash
ruflo route task "split work for: <task>"
ruflo hooks route -t "split work for: <task>"
ruflo hooks worker --help
```

When Codex exposes RuFlo MCP, prefer `mcp__ruflo__hooks_worker_detect` for a
non-mutating recommendation.

## Handoff Contract

Every delegated task must state:

- objective
- files or modules owned
- files to avoid
- expected output
- validation expected
- reminder not to revert other changes

## Prompt Template

```text
You are working in Agentic Trader.
Objective:
Owned files/modules:
Avoid:
Context to read:
Expected output:
Validation:
Do not revert user or peer-agent changes.
Do not commit or push.
```

## Merge Back

1. Review the agent output.
2. Inspect changed files before accepting.
3. Resolve conflicts by preserving user and peer-agent changes.
4. Run focused checks for each merged area.
5. Run broader checks when the integrated change crosses surfaces.
