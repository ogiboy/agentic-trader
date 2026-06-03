# Visual And Security QA Scenarios

These scenarios extend the primary terminal smoke list in
[`qa-scenarios.instructions.md`](qa-scenarios.instructions.md). Use them for
changes that affect real-screen operator readability, command language, local
web/API hardening, or security posture.

## Scenario 14: Computer Use Visual Operator Pass

Purpose: verify the real terminal screen, not only stdout snapshots, for changed
CLI/Rich/Ink operator flows.

Precondition:

- Computer Use is available in the current Codex/Desktop environment.
- If Computer Use is unavailable, record that this scenario was skipped and run
  the matching pexpect/tmux/asciinema flow instead.

Steps:

```bash
agentic-trader
agentic-trader tui
agentic-trader menu
agentic-trader dashboard-snapshot
agentic-trader broker-status
```

Interact:

- navigate to the changed Ink or Rich page
- trigger the changed hotkey or command path
- capture a screenshot or screen observation
- cross-check visible runtime/broker/review claims against JSON output

Expected:

- screen layout is readable and stable at the tested terminal size
- critical state is not truncated, hidden, or contradicted by JSON/runtime truth
- first-launch logo/header fits without hiding the primary controls
- resize behavior is checked at compact, normal, and wide terminal sizes when feasible
- Rich menu navigation has consistent back, cancel, close, and exit behavior
- menu labels explain the purpose and destination clearly enough for a non-developer operator
- CLI help for changed commands is checked with `--help` and `-h` when supported
- finance/accounting values such as cash, equity, PnL, exposure, positions, currency, and backend state are clearly labeled
- execution backend, paper/live status, kill switch, runtime mode, and rejection
  reasons are visible wherever the scenario requires them
- no screenshot or visual report is treated as proof by itself without a
  contract or persistence cross-check
- confusing or inconsistent behavior produces a repair recommendation, not only
  a pass/fail result

## Scenario 15: CLI Help And Operator Language Audit

Purpose: verify command discoverability and language clarity from an operator
perspective, not only command success.

Steps:

```bash
agentic-trader --help
agentic-trader -h
agentic-trader run --help
agentic-trader broker-status --help
agentic-trader trade-context --help
agentic-trader tui --help
agentic-trader menu --help
```

Expected:

- top-level and changed commands explain what they do in operator language
- short and long help forms work where supported
- examples or defaults are present for commands that can affect runtime,
  broker, review, or portfolio state
- option names are consistent across CLI, Rich, and Ink mental models
- blocked/live/safety wording is explicit and not ambiguous
- confusing help or naming produces a smallest-safe repair recommendation and a
  V1/V2 classification

## Scenario 16: Security Posture Smoke

Purpose: verify local-first hardening controls without changing runtime product
scope or enabling live execution.

Steps:

```bash
uv run --locked --all-extras --group dev python -m pytest -q tests/test_security_helpers.py tests/test_observer_api.py tests/test_research_sidecar.py tests/test_cli_json.py tests/test_data_providers.py
pnpm --filter webgui run typecheck
pnpm --filter webgui run lint
AGENTIC_TRADER_OBSERVER_API_TOKEN=local-token agentic-trader observer-api --host 127.0.0.1 --port 8765
```

Manual negative checks:

```bash
agentic-trader observer-api --host 0.0.0.0 --port 8765
agentic-trader observer-api --host '' --port 8765
curl -i http://127.0.0.1:8765/health
curl -i -H "X-Agentic-Trader-Observer-Token: local-token" http://127.0.0.1:8765/health
curl -i -H "Origin: http://evil.local" -H "Content-Type: application/json" --data '{"kind":"restart"}' http://localhost:3210/api/runtime
```

Expected:

- non-loopback and empty observer binds are rejected by default
- token-protected observer endpoint returns `401` without the token and JSON with the token
- observer responses include `Cache-Control: no-store` and browser hardening headers
- Web GUI mutating routes reject foreign origins and oversized/malformed JSON
- repeated runtime/chat/instruction API calls are cooldown or single-flight guarded
- CLI supervisor tails, Web errors, provider exception notes, and sidecar errors redact fake key/token values
- runtime feed and service log artifacts prefer owner-only permissions on local filesystems
- operation/live gates are unchanged: paper remains default, supported V1 active trading must pass approval/readiness gates, and ungated real-money execution remains blocked
