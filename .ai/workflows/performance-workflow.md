# Performance Workflow

Use this for slow setup/check/build paths, runtime-cycle latency, provider
timeouts, memory retrieval cost, WebGUI/docs build performance, and smoke QA
runtime.

## Inventory First

Classify the bottleneck before optimizing:

- dependency install/sync
- Python import or test collection
- Node lint/type/build
- provider network calls
- sidecar subprocess startup
- DuckDB or JSON artifact I/O
- memory retrieval/ranking
- WebGUI dashboard polling
- Rich/Ink rendering
- CI/release packaging

## Measurement Rules

- Capture command, environment, duration, and artifact path.
- Compare focused command versus full command.
- Avoid auto-optimizing without a measured bottleneck.
- Prefer caching or command-surface cleanup over hidden background workers.
- Keep runtime safety and observability ahead of raw speed.

## Advisory Commands

```bash
ruflo route task "performance: <short description>"
ruflo performance bottleneck
ruflo performance benchmark --help
ruflo analyze complexity agentic_trader tests scripts
ruflo analyze diff --risk
```

Use `--help` first for optimization or benchmark subcommands that may write
local metrics.

## Optimization Checklist

- Can setup be explicit without reinstalling every dependency?
- Can checks be split into root, WebGUI, docs, TUI, sidecar, and QA tiers?
- Can provider calls be bounded by timeout, retry budget, and source health?
- Can sidecar runtime use an already-synced environment without implicit
  installs?
- Can memory retrieval explain ranking without expensive global scans?
- Can UI polling avoid stale overwrites and unnecessary refresh loops?

## Acceptance Criteria

- Improvement is measured or the cleanup removes a real footgun.
- Failure behavior remains visible and safe.
- No hidden daemon, hook, or auto-fix path is introduced.
- QA docs and setup docs reflect any changed command surface.

## Measurement Template

```text
Command:
Before:
After:
Environment:
Artifact:
Bottleneck:
Change:
Safety impact:
```
