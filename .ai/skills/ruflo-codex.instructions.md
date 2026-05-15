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
5. Treat repo-local RuFlo init as a separate repo decision, not as normal setup.

## MCP Surface In Codex

When the `mcp__ruflo__` namespace is available, use these tools before CLI
commands:

| Need           | MCP Tool              | Use                                                                |
| -------------- | --------------------- | ------------------------------------------------------------------ |
| Server health  | `mcp_status`          | Confirm the global stdio MCP server is reachable                   |
| Hook inventory | `hooks_list`          | See available hook capabilities                                    |
| Diff risk      | `analyze_diff_risk`   | Quick risk score before publish or broad edits                     |
| Diff review    | `analyze_diff`        | File-level risk and reviewer suggestions                           |
| Diff stats     | `analyze_diff_stats`  | Fast size/status summary for the current branch                    |
| File risk      | `analyze_file_risk`   | Risk estimate for one changed file                                 |
| Task guidance  | `guidance_recommend`  | Advisory workflow/agent/tool suggestions                           |
| Prompt routing | `hooks_worker_detect` | Decide whether audit/optimize/testgap/map-style advisory is useful |
| Command risk   | `hooks_pre_command`   | Check command risk before destructive or expensive commands        |
| Worker status  | `hooks_worker_status` | Check background advisory worker state if used                     |

MCP output is advisory evidence. Verify it against source, tests, and repo
contracts before editing or publishing.

The following MCP areas are experimental in this repo until they pass repeated
serial smoke checks without `Transport closed` failures:

- `swarm_init`, `swarm_status`, `swarm_shutdown`
- `agent_spawn`, `agent_list`, `agent_terminate`
- `memory_*`, `embeddings_*`, `agentdb_*`
- `system_health`, `workflow_*`, task execution tools

Use experimental tools only for explicit diagnostics or controlled temp/global
state experiments. Do not assume that creating a swarm starts real work; it only
creates coordination state until agents and tasks are explicitly created.

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

If a command's flags differ by installed version, run `ruflo <command> --help`.
Use only flags shown in that help output and do not write generated config
files.

If the global binary is unavailable, use these fallback commands through `npx`:

```bash
npx ruflo@latest route task "summarize the intended change"
npx ruflo@latest analyze diff --risk
npx ruflo@latest security secrets
npx ruflo@latest performance bottleneck
npx ruflo@latest hooks pre-command -- "pnpm run check"
```

## Commands Requiring Explicit User Approval

- `ruflo init`
- `ruflo init --codex`
- `ruflo init --dual`
- `ruflo cleanup`
- `ruflo doctor --install`
- `ruflo daemon start`
- `ruflo swarm init`
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

## Repo-Local Init Policy

Do not run `ruflo init` inside Agentic Trader as part of normal work. Local init
generates Claude/RuFlo project state such as `.claude/`, `.claude-flow/`,
`.mcp.json`, and `CLAUDE.md`; these are not Agentic Trader source files.

Repo-local init can be reconsidered only when all of these are true:

1. the user explicitly asks for repo-local RuFlo state,
2. a temp-directory smoke run proves the exact command and generated file set,
3. global MCP completes three serial smoke rounds without `Transport closed`,
4. the plan identifies which minimal config, if any, will be tracked,
5. generated runtime state remains untracked and removable.

If a RuFlo command creates project files accidentally, inventory them, harvest
useful guidance into standalone `.ai` docs, then delete the generated state.

## Controlled Swarm Smoke

Use this only when the user asks to validate Ruflo swarm behavior. Prefer MCP
tools over CLI commands and keep the experiment outside repo-tracked state:

1. call `mcp__ruflo__.mcp_status`,
2. call `mcp__ruflo__.swarm_init` with a small mesh swarm,
3. call `mcp__ruflo__.agent_spawn` with `dryRun: true`,
4. verify with `agent_list` and `swarm_status`,
5. terminate spawned agents and shut down the swarm,
6. confirm no `.claude/`, `.claude-flow/`, `.swarm/`, `.mcp.json`, or
   `CLAUDE.md` remains in the repo.

If any Ruflo MCP call closes the transport, stop the Ruflo sequence and fall
back to Codex-native agents plus source/test review.

## Task Recipes

### Feature Work

```bash
ruflo route task "feature: explain memory retrieval reasons in CLI Ink Web and trade context"
ruflo hooks pre-command -- "pnpm run check"
ruflo analyze diff --risk
```

Use with `.ai/workflows/feature-workflow.instructions.md`.

### Security Work

```bash
ruflo route task "security: harden observer API and Web route boundaries"
ruflo security secrets
ruflo security threats
ruflo analyze diff --risk
```

Use with `.ai/workflows/security-workflow.instructions.md`.

### QA / Test Gaps

```bash
ruflo route task "qa: find missing smoke coverage for runtime mode and broker truth"
ruflo hooks coverage-gaps
ruflo hooks coverage-suggest --path tests
ruflo analyze deps --security
ruflo analyze diff --risk
```

Use with `.ai/workflows/qa-workflow.instructions.md`.

### Performance

```bash
ruflo route task "performance: reduce setup/check time without hidden installs"
ruflo performance bottleneck
ruflo analyze complexity scripts tests agentic_trader
ruflo hooks token-optimize --help
```

Use with `.ai/workflows/performance-workflow.instructions.md`.

### Release / PR

```bash
ruflo route task "release: validate feature branch version and PR base"
ruflo analyze diff --risk
pnpm run version:plan
```

Use with `.ai/workflows/release-pr-workflow.instructions.md`.

## Memory And Retrieval Ideas

RuFlo memory, embeddings, AgentDB, RuVector, and HNSW features are advisory
inputs for future retrieval design. They must not become project dependencies until a
specific repo decision accepts:

- storage location
- privacy model
- migration path from current local-hashing vectors
- replay/review compatibility
- failure behavior when the tool is absent

For now, use them for advisory lookup only and keep product memory inside
Agentic Trader's own memory contracts.
