# Pre-Push QA Checklist

Use this before pushing broad V1, runtime, WebGUI, sidecar, setup, security, or
release-sensitive work. The goal is to prove the product still behaves like a
safe paper-trading desk, not only that static checks are green.

## Tier 1: Required Fast Gate

- `git status --short --branch`
- `git diff --check`
- `pnpm run check`
- `pnpm run qa`
- confirm version files are intentionally bumped or intentionally unchanged
- confirm no runtime artifacts, `.env` files, logs, screenshots, or local tool
  state are staged accidentally

## Tier 2: Product-Readiness Gate

Run these for V1 readiness, runtime, setup, model, sidecar, WebGUI, docs, or
security work:

```bash
agentic-trader setup-status --json
agentic-trader model-service status --probe-generation --json
agentic-trader camofox-service status --json
agentic-trader webgui-service status --json
agentic-trader provider-diagnostics --json
agentic-trader v1-readiness --provider-check --json
agentic-trader finance-ops --json
agentic-trader research-status --json
agentic-trader dashboard-snapshot --provider-check
```

Expected:

- strict paper-operation gates fail closed when the model cannot generate
- optional tools report ready/degraded/missing honestly
- Firecrawl/Camofox/CrewAI sidecar state remains evidence-only
- WebGUI, Ink, Rich, observer, and CLI use the same dashboard/runtime truth
- proposal approval remains manual and auditable

## Tier 3: Behavioral Runtime Gate

Run when the change claims to affect agent cycles, memory, research, daemon
lifecycle, or paper broker behavior:

```bash
agentic-trader run --symbol AAPL --interval 1d --lookback 180d
agentic-trader review-run
agentic-trader trace-run
agentic-trader trade-context
agentic-trader journal --limit 5
agentic-trader memory-inspect --json
agentic-trader retrieval-inspect --json
```

Use this only when the configured local model can generate. If the model gate is
blocked, record that as the product-readiness result instead of bypassing the
gate with unsafe fallback behavior.

For daemon behavior:

```bash
agentic-trader launch --symbols AAPL,MSFT --interval 1d --lookback 180d --continuous --background
agentic-trader supervisor-status --json
agentic-trader monitor --refresh-seconds 1
agentic-trader stop-service
agentic-trader supervisor-status --json
```

Expected:

- background state records PID, heartbeat, log paths, launch count, and terminal
  state
- stop/exit does not leave app-owned helper processes behind
- CLI/Rich/TUI/Web surfaces do not claim the runtime is active after heartbeat
  is stale or stop is requested

## Tier 4: Visual And Browser Gate

Run when UI, docs, WebGUI, terminal rendering, or operator copy changes:

- Browser QA for `webgui/` overview, review, memory, settings, and route error
  states
- Browser QA for `docs/` changed pages
- Ink/TUI pass for hotkeys, scroll/resize artifacts, clipped labels, and clean
  exit
- Rich menu pass for submenu navigation, Ctrl+C, and observer-mode messages
- attach screenshots or terminal transcripts when the change is visual

## Tier 5: Security Gate

Run for security-sensitive or broad changes:

- WebGUI route negative tests: foreign origin, malformed JSON, oversized body,
  missing/invalid token when configured, rapid repeated runtime actions
- observer API negative tests: non-loopback bind without token, blank host,
  token-required nonlocal exposure
- subprocess/helper tests: allowed commands only, owner-only state/logs, stale
  PID protection, external process not killed
- secret-redaction tests: fake API keys, bearer tokens, provider exceptions,
  artifact bundles, log tails
- research poisoning tests: raw web text never enters trading prompts,
  provenance survives snapshots, missing/stale sources remain visible

Open a GitHub issue for real blockers that need more than a small immediate
fix. Do not create issues for tiny problems that can be repaired in the same
push.
