# Generated Artifact Harvest

This record captures the useful practices adopted from a local advisory-tool
init and the content rejected for this repository. It is not an operational
dependency. The actual working guidance lives in `.ai/agents/`,
`.ai/workflows/`, `.ai/playbooks/`, `.ai/helpers/`, and `.ai/skills/`.

If an inventory item or generated source is no longer available, treat this file
as the durable summary. Do not recreate generated scaffolding just to verify the
old source; use current `.ai` guidance and git history instead.

## Inventory Summary

The generated advisory scaffold contained about 270 files across these groups:

| Group | Adopted | Rejected |
| --- | --- | --- |
| Core planning, coding, review, research, and testing roles | Task decomposition, dependency mapping, evidence-first research, reviewer-first findings, focused test planning | Hook blocks, neural-training claims, auto-dispatch, external memory writes |
| Security roles | STRIDE thinking, secrets review, dependency audit, route/origin checks, prompt/data-poisoning checks | Generic OWASP regex dumps as authoritative scanners, auto CVE fixes, generated reports outside repo QA |
| GitHub and release roles | PR base verification, release preview, version coordination, go/no-go review | Auto-merge, auto-release, project-board mutation, generated release daemons |
| Performance roles and commands | Bottleneck inventory, setup/check runtime measurement, cache/build/test analysis, concurrency review | Auto-optimization, topology mutation, background performance workers |
| Trading predictor content | Position limits, concentration limits, liquidity/stale-data checks, stress scenarios, audit trail | Latency arbitrage, temporal-advantage execution, high-frequency or cross-market execution claims |
| Helpers | Validate setup, scan secrets, checkpoint before mutation, cap outputs, record audit evidence | Auto-commit, repo-local hooks, daemon/statusline, generated memory databases |
| Skill copies | Browser verification, GitHub/release review, security audit, verification quality, memory/retrieval ideas | Making AgentDB, ReasoningBank, RuVector, Claude-flow, or Flow Nexus a project dependency |

## Adopted Into This Repo

- `.ai/agents/researcher.agent.md`
- `.ai/agents/security-auditor.agent.md`
- `.ai/agents/release-manager.agent.md`
- `.ai/agents/performance-engineer.agent.md`
- `.ai/agents/finance-ops.agent.md`
- `.ai/workflows/feature-workflow.instructions.md`
- `.ai/workflows/security-workflow.instructions.md`
- `.ai/workflows/release-pr-workflow.instructions.md`
- `.ai/workflows/qa-workflow.instructions.md`
- `.ai/workflows/performance-workflow.instructions.md`
- `.ai/workflows/multi-agent-handoff.instructions.md`
- `.ai/playbooks/pr-enhance.instructions.md`
- `.ai/playbooks/code-review.instructions.md`
- `.ai/playbooks/setup-validation.instructions.md`
- `.ai/playbooks/security-scan.instructions.md`
- `.ai/playbooks/browser-qa.instructions.md`
- `.ai/playbooks/memory-retrieval.instructions.md`
- `.ai/playbooks/ruflo-advisory-checks.instructions.md`
- `.ai/helpers/README.instructions.md`
- `.ai/skills/README.instructions.md`
- `.ai/skills/ruflo-codex.instructions.md`
- `.ai/agents/market-strategist.agent.md`
- `.ai/workflows/continuous-research-loop.instructions.md`
- `.ai/playbooks/news-intelligence.instructions.md`
- `.ai/playbooks/strategy-research-and-sweeps.instructions.md`
- `.ai/playbooks/finance-evidence-reconciliation.instructions.md`
- `.ai/skills/market-news-research.instructions.md`
- `.ai/strategies/README.instructions.md`
- `.ai/strategies/v1-strategy-catalog.instructions.md`

## External Benchmark Ideas Adopted

The second harvest focused on financial-intelligence patterns rather than
assistant tooling. Useful ideas were translated into self-contained Agentic
Trader guidance:

- continuous research-loop phases: pre-flight, monitor, analyze, propose, digest
- source-attributed news evidence with fetcher source, attempts, freshness,
  materiality, and fallback/staleness semantics
- scanner-to-proposal discipline with no agent direct execution
- strategy research taxonomy for momentum, gap review, mean reversion,
  breakout/reclaim, VWAP/opening-range, regime-adaptive, and ensemble ideas
- vectorized indicator/backtest guidance, no-lookahead checks, declarative
  sweep design, and confidence review beyond raw return
- finance-reporting patterns that separate trades, cash, fees, interest,
  dividends, corporate actions, currency, and source ids before deriving
  portfolio truth

## Rejection Rules

- Auto-commit and auto-merge helpers are rejected.
- Repo-local advisory hooks are rejected.
- Background advisory daemons and status lines are rejected.
- Generated advisory memory databases are rejected.
- Cloud-only Flow Nexus style agents are rejected unless a future roadmap item
  explicitly adopts a cloud integration.
- Trading agents that claim predictive execution, latency arbitrage, or
  temporal advantage are rejected for V1 and V2 unless a separate legal,
  broker, market-data, and risk review accepts a bounded research-only scope.
- IBKR gateway/container scripts, flex-report ingestion, options execution,
  global/FX, multi-currency accounting, and short/pairs execution patterns are
  deferred to V2 unless the roadmap explicitly pulls a narrow read-only slice
  into V1.

## Verification

After harvest, the generated artifacts should not be present in `git status`.
Operational `.ai` files must not require those artifacts to be read later.
If `git status` shows generated advisory state, classify it as disposable unless
a separate decision says to track a minimal config.
