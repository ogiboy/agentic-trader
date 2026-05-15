# Working Memory

If this file conflicts with current source, tests, or newer decision records,
prefer the current repository evidence and update the relevant `.ai` guidance
after the change. Missing or stale memory must not override runtime contracts.

## Stable Facts

- Default local model path is Ollama-class
- Role-based model routing already exists
- The project persists runtime artifacts into DuckDB
- The project already includes a lightweight retrieval layer
- The project now includes a hybrid heuristic + vector-style retrieval layer
- Shared memory bus entries are propagated across specialist stages
- The project already includes operator chat and safe instruction parsing
- The project already includes replay and backtesting surfaces
- Root daily development targets Python 3.13 through uv-managed `.venv`, while uv owns the root dependency lock/install/run/build path
- Add root Python packages with `uv add <package>` so `pyproject.toml` and
  `uv.lock` stay in sync; upgrade with `uv lock --upgrade` and then restore the
  developer environment with `uv sync --locked --all-extras --group dev`
- The tracked CrewAI Flow project lives under `sidecars/research_flow/` and uses uv independently of the root uv environment
- The root runtime may call the CrewAI Flow sidecar only through a subprocess JSON contract; it should not import CrewAI directly
- SEC EDGAR submissions metadata is the first opt-in live research source, gated by `AGENTIC_TRADER_RESEARCH_SEC_EDGAR_ENABLED` and `AGENTIC_TRADER_RESEARCH_SEC_EDGAR_USER_AGENT`
- Optional Firecrawl and Camofox research helpers are disabled by default under `researchd`; they produce redacted/source-attributed evidence or provider health only and must not inject raw web text into prompts
- V1 trade proposals are explicit manual-review records; proposal approval is the only path from a queued idea into broker adapter submission, and terminal proposal states should not be reopened
- V1 idea-scanner presets score research/watch candidates only; scanner output should be enriched and converted into a proposal before any approval path is available
- The first benchmark-to-runtime market intelligence slice is code, not only `.ai` guidance: `strategy-catalog`, `strategy-profile`, `idea-score` strategy readiness, `news-intelligence`, `research-cycle-plan`, and `finance-ops` ledger categories expose strategy, source-tier, materiality, continuous-loop, and finance reconciliation contracts without execution authority
- Market-intelligence guidance now lives in `.ai/agents/market-strategist.agent.md`,
  `.ai/workflows/continuous-research-loop.instructions.md`, `.ai/playbooks/news-intelligence.instructions.md`,
  `.ai/playbooks/strategy-research-and-sweeps.instructions.md`,
  `.ai/playbooks/finance-evidence-reconciliation.instructions.md`,
  `.ai/skills/market-news-research.instructions.md`, and `.ai/strategies/`; these files are
  self-contained guidance derived from external benchmark ideas and must not be
  treated as runtime orchestration or execution authority
- Stable app versions are owned by `pyproject.toml` and semantic-release; branch pushes should use `pnpm run version:plan` rather than manual package-version bumps, and `agentic_trader/__init__.py` must stay stamped with the same stable app version
- `alpaca_paper` is an explicit external-paper backend, not the default local paper backend and not live trading
- RuFlo and similar tools are system-level advisory helpers only; durable repo
  workflow knowledge belongs in `.ai/workflows/`, `.ai/playbooks/`,
  `.ai/helpers/`, `.ai/skills/`, and `.ai/agents/`, not in generated advisory
  folders or external tool memory state
- RuFlo can be used actively through Codex MCP tools or the global `ruflo`
  binary for read-only route, diff-risk, command-risk, security, performance,
  coverage, and code-boundary checks; do not run repo init, daemon, agent spawn,
  workflow run, memory mutation, or auto-install commands without explicit user
  approval

## Important Constraints

- Do not collapse specialist roles into a generic single-agent flow
- Do not mix conversational memory with trading memory
- Do not introduce silent cloud dependence
- Do not weaken strict runtime gating
- Do not let operator chat history bleed into execution-time context assembly
- Do not let research sidecars or CrewAI loops become hidden execution, policy mutation, or raw web-text prompt injection paths
- Do not add CrewAI to the root dependency graph unless the sidecar boundary is intentionally redesigned
- Do not let runtime commands implicitly sync or upgrade the sidecar environment; setup/check commands own uv sync
- Do not fetch SEC EDGAR or any future external research source without explicit provider enablement and required contact/credential configuration
- Do not let Firecrawl/Camofox errors, snippets, browser payloads, or provider raw text bypass central redaction or source-normalization before reaching CLI/observer/Web/research snapshots
- Do not let scanner, sidecar, chat, or Web surfaces approve a proposal implicitly; manual approval must remain auditable and broker-adapter backed
- Do not submit external Alpaca paper orders unless `AGENTIC_TRADER_EXECUTION_BACKEND=alpaca_paper`, credentials, the paper endpoint, and `AGENTIC_TRADER_ALPACA_PAPER_TRADING_ENABLED=true` are all explicit
- Do not adopt external trading-agent flows that imply latency arbitrage,
  predictive execution before data arrives, high-frequency execution, or live
  brokerage behavior inside V1

## Current Architectural Direction

- extend current memory rather than replacing it
- add research sidecar memory inputs as normalized, source-attributed packets only
- evolve the CrewAI Flow sidecar through explicit JSON contracts, not direct imports from the core trading runtime
- keep root uv migration aligned across scripts, CI, docs, and release automation
- add provider adapters rather than changing agent workflow semantics
- expand SEC ingestion from metadata-only submissions into company facts and filing parsing only after the normalized evidence contract stays green
- grow financial intelligence through proposal review, idea screening, source materiality, liquidity, sizing, and concentration controls before adding direct execution automation
- grow strategy intelligence through data requirements, no-lookahead checks,
  declarative sweeps, confidence intervals, source/news vetoes, and manual
  proposal handoff rather than direct strategy execution
- keep operator-facing inspection strong
- keep runtime behavior replayable and reviewable
- keep memory writes explicit, inspectable, and role-aware
