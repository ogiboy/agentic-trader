# Decisions

## Decision Log

### The repository's own runtime remains the orchestration source of truth

Reason:
The project already has a specialist graph, manager layer, memory assembly, storage, replay, and operator surfaces.
Adding an external orchestrator as the central control plane would duplicate and distort existing architecture.

### External AI coding tools are development helpers, not runtime dependencies

Reason:
ChatGPT, Codex, and similar tools may help plan and implement changes, but they should not become assumptions inside the trading runtime.

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

### External data must normalize into canonical analysis snapshots

Reason:
Provider payloads differ by source, market, region, and availability.
The runtime now uses provider interfaces for market, fundamental, news, disclosure, and macro data, then aggregates them into a `CanonicalAnalysisSnapshot`.
Agents still consume the compact `DecisionFeatureBundle`, but the canonical snapshot preserves source attribution, freshness, completeness, and explicit missing sections for prompts, persistence, memory, dashboard JSON, and future UI review surfaces.
Yahoo remains a fallback market/news source rather than the sole source of truth, while SEC EDGAR, KAP, macro indicators, transcripts, and vendor APIs can be added behind the same adapter seam.
