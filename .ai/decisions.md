# Decisions

## Decision Log

### The repository's own runtime remains the orchestration source of truth

Reason:
The project already has a specialist graph, manager layer, memory assembly, storage, replay, and operator surfaces.
Adding an external orchestrator as the central control plane would duplicate and distort existing architecture.

### External AI coding tools are development helpers, not runtime dependencies

Reason:
ChatGPT, Codex, and similar tools may help plan and implement changes, but they should not become assumptions inside the trading runtime.
The `.ai/agents/` role pack documents development workflows for planner, implementer, reviewer, QA, and data-focused helpers only; it must not be interpreted as a runtime agent platform or external orchestration dependency.

### Provider expansion should happen through adapters

Reason:
The project currently assumes Ollama-class local models.
Future providers should be added behind a stable interface so agent workflow, memory, and runtime control surfaces remain consistent.

### Memory must remain inspectable and bounded

Reason:
Trading memory supports context, replay, and review.
It must not turn into a hidden policy mutation layer.

### Local-first remains the default posture

Reason:
The project's identity, safety model, and cost profile depend on local-first operation.
Future remote providers may be supported, but they should remain optional and explicit.

### CLI, monitor, and TUI should read from the same contracts

Reason:
Operator trust depends on consistent state across surfaces.
UI-specific hidden logic should be avoided.

### Operator chat memory must remain separate from trading memory

Reason:
Operator conversations are useful for coordination and explanation, but they must not silently mutate execution policy or contaminate trading-context retrieval.

### Hybrid retrieval should extend, not replace, existing inspectable memory

Reason:
The project benefits from richer similarity search, but retrieval must stay local-first, reviewable, and bounded rather than becoming opaque hidden behavior.

### Specialist disagreement should be persisted before manager synthesis

Reason:
When a manager overrides or moderates a plan, operator review should show not only the final decision but also the pre-manager alignment and disagreements that led to it.

### Memory writes must respect explicit domain policies

Reason:
Trading memory and operator chat memory serve different purposes and carry different risks.
Writes should be gated by explicit actor rules so conversational surfaces cannot silently mutate trade-memory retrieval.

### Terminal smoke QA should validate real operator entrypoints and quality gates

Reason:
The installed `agentic-trader` command, `python main.py`, Ink TUI, and Rich menu can drift independently from unit tests.
A small pexpect-based smoke harness should exercise the actual terminal surfaces, leave timestamped text artifacts, and fail loudly when the operator's PATH resolves a stale entrypoint.
Quality gates such as ruff, pytest, pyright, and SonarQube should be attached as optional QA checks without hardcoding tokens or changing the trading runtime.

### Localization should start as a shared text boundary, not a full i18n rewrite

Reason:
The CLI, Rich menu, Ink TUI, and future WebUI need consistent operator language, but the product flows are still moving.
A lightweight shared UI text catalog avoids duplicated labels today and creates a safe seam for future multi-language support without introducing translation machinery too early.

### Lookback must become an operator-verifiable artifact

Reason:
Fetching a long market window is not enough if the agent context and operator surfaces only expose compact latest-row indicators.
The next input layer should persist a Market Context Pack with multi-horizon summaries, data sufficiency, anomaly flags, and window coverage so every run can prove what history was actually considered.
If expected coverage is materially too low in operation/runtime flows, the system should fail before agent execution instead of silently treating an under-covered provider response as a valid long-window decision.
Training replay is allowed to use growing windows, but undercoverage must remain visible as context rather than being confused with production-ready coverage.

### Training and Operation should be runtime modes, not separate products

Reason:
The project needs a clear distinction between evaluation workflows and continuous paper operation, but forking the runtime would create drift.
Mode should be a shared settings/service/run attribute that changes gates, allowed commands, and UI banners while preserving one orchestration source of truth.
Operation mode therefore fails closed when strict LLM gating is disabled and still requires provider/model readiness for runtime execution.
Training mode may use deterministic diagnostic fallback only in evaluation/backtest flows so replay remains possible without silently generating paper trades.
Every replay decision should carry an auditable `as_of` boundary, and reports should preserve data-window plus decision-window timestamps so future-data leakage is visible in artifacts.
Mode transitions should be surfaced as schema-backed transition plans. The current implementation reports checklist state but does not mutate configuration, keeping chat and free-form instructions from silently changing execution policy.

### Semantic memory must preserve local-first inspectability

Reason:
True embeddings can improve recall over hashed-token pseudo-embeddings, but trading memory must remain reviewable, policy-bound, and separate from chat memory.
Embedding metadata, retrieval explanations, and migration compatibility are required before semantic memory becomes a core decision input.
The current local-hashing vectors now persist provider/model/version/dimension metadata so future semantic vectors can coexist with or migrate from existing memory rows safely.

### QA should graduate from smoke checks to terminal regression evidence

Reason:
Agentic Trader is operator-facing through terminal surfaces, so quality must include repeatable CLI, Rich, Ink, daemon, observer API, and visual-flow evidence.
The smoke harness should remain fast, but deeper tiers should capture JSON snapshots, pexpect transcripts, optional tmux/asciinema artifacts, and human-readable failure reports.
When Computer Use is available, visual CLI/Rich/Ink checks should run through the real terminal screen and capture screenshot or screen-state evidence.
Computer Use is an optional QA capability, not a runtime or CI dependency; if it is unavailable, the existing pexpect, tmux, asciinema, text, and JSON evidence flow remains valid.
Visual evidence must be cross-checked with runtime contracts or persisted truth whenever the screen claims runtime, broker, execution, or review state.
Visual QA should include UX, design, and finance/accounting readability, not only crash or smoke behavior.
The `.ai/agents/operator-ux.md` role exists for this development review lens and should stay separate from runtime agents.
When this role finds a confusing menu, command, layout, or financial display, it should propose the smallest safe repair and classify it as V1 blocker, V1 polish, or V2 redesign.

### Structured LLM calls should use provider JSON mode and safe previews

Reason:
Agent outputs are schema-bound contracts, not free-form prose.
Ollama JSON mode reduces malformed/verbose structured responses and makes one-cycle runtime QA more reliable on local models.
Provider payload previews must redact reasoning fields such as `thinking` before they reach operator surfaces or artifacts; the UI should expose stage summaries, tool usage, validation errors, and decision rationale rather than raw hidden reasoning.
When the provider supports it, structured calls should send the concrete Pydantic JSON schema as Ollama's `format`; older/incompatible Ollama responses can fall back to plain JSON mode while keeping the same Pydantic validation boundary.

### Runtime QA should have explicit performance tiers

Reason:
A real agent cycle can take several minutes on local hardware, so it should not be part of every fast smoke run.
The QA harness should keep fast terminal checks lightweight while offering opt-in runtime-cycle validation with isolated runtime storage, bounded token budgets, product-like retry behavior, request timeouts, and artifacts that show the active stage when a run fails.

### Broker execution should flow through an explicit intent and outcome contract

Reason:
Agent and guard outputs are not the same thing as broker orders.
The runtime now translates guard-approved or guard-rejected decisions into a canonical `ExecutionIntent`, sends that through a broker adapter, and records an `ExecutionOutcome`.
This keeps paper execution working while creating a reviewable seam for simulated-real rehearsal and future live broker integration.
Live execution remains blocked until a real adapter, approval gates, paper-operation evidence, and operator-visible readiness checks exist behind the same contract.
The intent contract exposes `timestamp` while preserving `created_at` for existing storage and review payload compatibility.
If both audit timestamp fields are supplied they must match, and operator review views should show backend, adapter, outcome, and rejection reason without requiring raw JSON.

### No-trade risk output should remain readable without changing execution posture

Reason:
Local models can emit technically valid but operator-hostile sentinel values for no-trade risk levels, such as tiny positive stop/take prices used only to satisfy schema bounds.
Risk output should be finalized after validation so hold/no-trade decisions keep tiny exposure and no execution approval, while operator surfaces still display reference stop/take levels around the latest close.

### Financial intelligence should flow through structured feature bundles

Reason:
Future fundamentals, news, macro, SEC, KAP, transcript, and broker data can become noisy or provider-specific quickly.
Agents should consume typed summaries rather than raw documents or hidden provider state.
The new `DecisionFeatureBundle` is the boundary between data ingestion and reasoning: it carries symbol identity, technical summaries, fundamental features, and macro/news context.
Fundamental and macro/news analysts are now specialist roles in the staged graph, but real provider ingestion remains additive future work behind the feature layer.
API keys must stay in ignored local env files and should never be serialized into prompts, logs, QA artifacts, or tracked config.
Prompt rendering should use the feature bundle as the primary agent input when it exists, while compact market snapshots remain internal runtime state for deterministic fallbacks, risk math, audit, and compatibility.
The V1 technical feature contract should expose calendar-friendly 30d, 90d, and 180d return windows even though the underlying market context still computes bar horizons.
Feature-first prompts must still surface technical data-quality flags so agents do not lose lookback or provider-quality truth when raw snapshots stay internal.
Fallback-generated fundamental and macro/news assessments must not count as consensus support; unavailable finance evidence can be noted as missing or neutral, but it must not make manager synthesis look more complete than the provider evidence actually is.
The fundamental analyst contract should behave like a cautious financial analyst: every bias must be traceable to evidence, inference, or uncertainty, and incomplete inputs must remain neutral/cautious instead of being filled with imagined business facts.
Non-neutral LLM-generated fundamental bias must include direct evidence, and prompt-facing feature summaries must expose the actual fundamental metrics instead of asking the model to infer from labels or summaries alone.

### External data must normalize into canonical analysis snapshots

Reason:
Provider payloads differ by source, market, region, and availability.
The runtime now uses provider interfaces for market, fundamental, news, disclosure, and macro data, then aggregates them into a `CanonicalAnalysisSnapshot`.
Agents still consume the compact `DecisionFeatureBundle`, but the canonical snapshot preserves source attribution, freshness, completeness, and explicit missing sections for prompts, persistence, memory, dashboard JSON, and future UI review surfaces.
Yahoo remains a fallback market/news source rather than the sole source of truth, while SEC EDGAR, KAP, macro indicators, transcripts, and vendor APIs can be added behind the same adapter seam.
Provider scaffolds for SEC EDGAR, KAP, Finnhub, and FMP should return explicit missing snapshots or empty-source attributions until real ingestion exists; absence of provider data must remain visible and must not be converted into neutral supporting evidence.

### Yahoo is degraded fallback evidence, not the target source of truth

Reason:
Yahoo/yfinance is useful for local-first bootstrap, tests, and fallback market/news evidence, but V1 financial intelligence should prefer explicit regulatory, public, or configured provider sources when available.
SEC 10-K/10-Q/8-K, earnings transcripts, macro indicators, KAP, Turkey company disclosures, CBRT-style macro data, inflation, and FX sources should normalize into canonical snapshots before reaching agents.
Finnhub, FMP, Polygon/Massive, and similar APIs are optional enrichers; their keys must remain configuration-only and their absence must be visible as missing/degraded evidence rather than hidden fallback completeness.

### V1 is Alpaca-ready and paper-first; V2 owns IBKR/global/FX expansion

Reason:
The execution boundary is ready for future broker adapters, but V1 should remain narrow enough to ship reliably.
Alpaca readiness belongs to V1 as US-equities-only preparation with manual approval, paper defaults, strict safety gates, kill switch, and broker/readiness health checks.
Interactive Brokers, global markets, multi-currency account state, FX conversion assumptions, and region-specific market QA belong in V2 so V1 does not become a broad multi-broker production rewrite.

### Python dependencies should be locked with Poetry

Reason:
The project is expected to run consistently on multiple machines, but Conda and ad hoc pip installs do not update repository manifests automatically.
`pyproject.toml` remains the direct dependency manifest and `poetry.lock` is now the committed resolver output.
Conda stays useful for selecting the Python interpreter and native environment, while Poetry owns Python package add, remove, lock, and install synchronization.

### Service state updates should use an explicit update contract

Reason:
Runtime supervision writes many related fields whenever cycle, symbol, daemon, and stop-request state changes.
Keeping those fields in a `ServiceStateUpdate` contract makes persistence updates easier to evolve and avoids long, fragile method signatures while preserving the sidecar service-state mirror used by CLI, Rich, Ink, observer, and daemon surfaces.
