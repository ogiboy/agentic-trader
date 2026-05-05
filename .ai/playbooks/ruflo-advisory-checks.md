# RuFlo Advisory Checks Playbook

Use this playbook when a task is broad enough that advisory routing or risk
classification can save time.

## Quick Start

```bash
ruflo route task "describe the current task"
ruflo hooks route -t "describe the current task"
ruflo analyze diff --risk
```

If Codex exposes RuFlo MCP tools, use:

- `mcp__ruflo__hooks_worker_detect`
- `mcp__ruflo__analyze_diff_risk`
- `mcp__ruflo__analyze_diff`
- `mcp__ruflo__analyze_file_risk`
- `mcp__ruflo__hooks_pre_command`

## Worker Trigger Map

| Trigger | Use When | Repo Follow-Up |
| --- | --- | --- |
| `audit` | security, auth, route, observer, subprocess, provider, artifact changes | Run `.ai/workflows/security-workflow.md` and negative tests |
| `optimize` | setup/check/build/runtime slowdown | Run `.ai/workflows/performance-workflow.md` with measurements |
| `testgaps` | feature adds behavior or surfaces | Run `.ai/workflows/qa-workflow.md` and add focused tests |
| `map` | five or more files or unclear ownership | Ask `researcher.md` or `repo-architect.md` for boundary mapping |
| `document` | public/operator behavior changes | Ask `product-docs.md` to update operator-facing docs |
| `deepdive` | ambiguous architecture or provider behavior | Ask `researcher.md` to produce source-grounded findings |

Do not auto-dispatch write-capable workers. Treat suggested triggers as a
checklist for what a human/Codex pass should inspect.

## Command Risk Gate

Before expensive or potentially mutating commands, run:

```bash
ruflo hooks pre-command -- "command to assess"
```

Use this for:

- release commands
- cleanup commands
- dependency sync/update
- long QA runs
- commands touching runtime artifacts
- commands with network side effects

Never use an advisory "low risk" verdict to bypass explicit user approval for
destructive operations.

## Diff Risk Template

```text
RuFlo advisory:
- risk: low | medium | high
- risky files:
- suggested reviewers:
- suggested tests:

Local verification:
- source contracts checked:
- focused tests:
- broader checks:
- accepted residual risk:
```

## No-Write Rule

These checks can guide the work, but the repo should not track RuFlo databases,
generated state, daemon logs, or local MCP config. Durable output belongs in
the normal `.ai` files and test artifacts.
