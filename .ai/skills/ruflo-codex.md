# RuFlo For Codex

RuFlo is available as a system-level advisor for Codex work. Use it to improve
routing, review, security, performance, memory lookup, and risk assessment
without initializing project-local state or adding runtime dependencies.

## Priority Order

1. Prefer Codex-exposed RuFlo MCP tools when they are available.
2. Use the global `ruflo` binary for read-only/advisory commands.
3. Use `npx ruflo@latest ...` only when the global binary is unavailable.
4. Do not run repo initialization, auto-install, daemon, or cleanup commands
   unless the user explicitly asks for that operation.

## MCP Surface In Codex

When the `mcp__ruflo__` namespace is available, use these first:

| Need | MCP Tool | Use |
| --- | --- | --- |
| Diff risk | `analyze_diff_risk` | Quick risk score before publish or broad edits |
| Diff review | `analyze_diff` | File-level risk and reviewer suggestions |
| File risk | `analyze_file_risk` | Risk estimate for one changed file |
| Prompt routing | `hooks_worker_detect` | Decide whether audit/optimize/testgap/map-style advisory is useful |
| Command risk | `hooks_pre_command` | Check command risk before destructive or expensive commands |
| Hook inventory | `hooks_list` | See available hook capabilities |
| Worker status | `hooks_worker_status` | Check background advisory worker state if used |

MCP output is advisory evidence. Verify it against source, tests, and repo
contracts before editing or publishing.

## Safe CLI Commands

Run these from the repo root as read-only/advisory commands:

```bash
ruflo --help
ruflo doctor -c version
ruflo doctor -c node
ruflo doctor -c npm
ruflo mcp tools
ruflo mcp status
ruflo route task "summarize the intended change"
ruflo route list-agents
ruflo hooks route -t "summarize the intended change"
ruflo hooks explain -t "summarize the intended change"
ruflo hooks pre-command -- "pnpm run check"
ruflo analyze diff --risk
ruflo analyze code agentic_trader tests scripts
ruflo analyze deps --security
ruflo analyze complexity agentic_trader tests scripts
ruflo analyze symbols agentic_trader --type function
ruflo analyze imports agentic_trader --external
ruflo analyze dependencies agentic_trader --format dot
ruflo analyze circular agentic_trader
ruflo security secrets
ruflo security threats
ruflo security defend --help
ruflo performance bottleneck
ruflo performance benchmark --help
ruflo hooks coverage-gaps
ruflo hooks coverage-suggest --path tests
ruflo hooks token-optimize --help
ruflo route stats
ruflo workflow validate --help
ruflo embeddings providers
ruflo embeddings benchmark --help
```

If a command's flags differ by installed version, run `ruflo <command> --help`
and adapt without writing generated config files.

If the global binary is unavailable, use the same commands through `npx`:

```bash
npx ruflo@latest route task "summarize the intended change"
npx ruflo@latest analyze diff --risk
npx ruflo@latest security secrets
npx ruflo@latest performance bottleneck
npx ruflo@latest hooks pre-command -- "pnpm run check"
```

## Commands Requiring Explicit User Approval

- `ruflo init`
- `ruflo cleanup`
- `ruflo doctor --install`
- `ruflo daemon start`
- `ruflo swarm start`
- `ruflo swarm coordinate`
- `ruflo agent spawn`
- `ruflo agent wasm-create`
- `ruflo task create`
- `ruflo workflow run`
- `ruflo memory init`
- `ruflo memory store`
- `ruflo memory import`
- any command that starts long-running agents, writes local databases, mutates
  repo files, installs dependencies, or dispatches write-capable workers

## Task Recipes

### Feature Work

```bash
ruflo route task "feature: explain memory retrieval reasons in CLI Ink Web and trade context"
ruflo hooks pre-command -- "pnpm run check"
ruflo analyze diff --risk
```

Use with `.ai/workflows/feature-workflow.md`.

### Security Work

```bash
ruflo route task "security: harden observer API and Web route boundaries"
ruflo security secrets
ruflo security threats
ruflo analyze diff --risk
```

Use with `.ai/workflows/security-workflow.md`.

### QA / Test Gaps

```bash
ruflo route task "qa: find missing smoke coverage for runtime mode and broker truth"
ruflo hooks coverage-gaps
ruflo hooks coverage-suggest --path tests
ruflo analyze deps --security
ruflo analyze diff --risk
```

Use with `.ai/workflows/qa-workflow.md`.

### Performance

```bash
ruflo route task "performance: reduce setup/check time without hidden installs"
ruflo performance bottleneck
ruflo analyze complexity scripts tests agentic_trader
ruflo hooks token-optimize --help
```

Use with `.ai/workflows/performance-workflow.md`.

### Release / PR

```bash
ruflo route task "release: validate feature branch version and PR base"
ruflo analyze diff --risk
pnpm run version:plan
```

Use with `.ai/workflows/release-pr-workflow.md`.

## Memory And Retrieval Ideas

RuFlo memory, embeddings, AgentDB, RuVector, and HNSW features may inspire
future retrieval design. They must not become project dependencies until a
specific repo decision accepts:

- storage location
- privacy model
- migration path from current local-hashing vectors
- replay/review compatibility
- failure behavior when the tool is absent

For now, use them for advisory lookup only and keep product memory inside
Agentic Trader's own memory contracts.
