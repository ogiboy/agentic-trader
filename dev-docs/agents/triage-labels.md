# Triage Labels

Engineering skills use five canonical triage roles. This repository currently
uses the default label names directly in GitHub Issues.

| Skill role | GitHub label | Meaning |
| --- | --- | --- |
| `needs-triage` | `needs-triage` | Maintainer needs to evaluate the issue |
| `needs-info` | `needs-info` | Waiting on reporter for more information |
| `ready-for-agent` | `ready-for-agent` | Fully specified and ready for an AFK agent |
| `ready-for-human` | `ready-for-human` | Requires human implementation or judgment |
| `wontfix` | `wontfix` | Will not be actioned |

When a skill asks for an AFK-ready label, use `ready-for-agent`.

When labels do not exist yet in GitHub, create or apply the exact strings above
instead of inventing near-duplicates.

Keep V1 trading blockers explicit: if an issue prevents safe paper-operation,
Alpaca-paper readiness, operator review, or evidence traceability, keep it
visible with `needs-triage` until it is either fixed or deliberately moved to a
later release scope.
