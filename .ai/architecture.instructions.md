# Architecture Notes

## High-Level Shape

The project already follows a staged, specialist-agent trading pipeline.

Current runtime stages:

1. Research Coordinator
2. Fundamental Analyst
3. Macro / News Analyst
4. Regime Agent
5. Strategy Selector
6. Risk Agent
7. Specialist Consensus Layer
8. Manager Agent
9. Execution Guard
10. Paper Broker

## Core Package Areas

- `agentic_trader/agents/`
  Specialist, manager, explainer, and instruction-oriented agent logic

- `agentic_trader/llm/`
  LLM provider access, provider adapters, model routing, and role-based model selection

- `agentic_trader/market/`
  Market data loading, feature preparation, and calendar/session context

- `agentic_trader/features/`
  Structured decision-feature generation across symbol identity, 30d/90d/180d technical summaries, fundamental placeholders, and macro/news context

- `agentic_trader/providers/`
  Data provider interfaces and canonical aggregation for market, fundamental, news, disclosure, and macro context. Provider payloads normalize into `CanonicalAnalysisSnapshot` before features, agents, memory, persistence, or UI contracts consume them.

- `agentic_trader/memory/`
  Similar-run retrieval, hybrid vector-style memory support, memory assembly, and memory inspection support

- `agentic_trader/storage/`
  DuckDB persistence for runs, fills, positions, journals, trade contexts, traces, and reports

- `agentic_trader/finance/`
  Finance-desk helpers that do not own orchestration: manual-review trade proposals, idea-scanner scoring presets, future sizing/risk utilities, and review-only accounting logic that must pass through storage and broker adapter contracts before any paper submission

- `agentic_trader/engine/`
  Runtime execution and orchestration mechanics, including the broker adapter boundary, the local paper broker implementation, the simulated-real rehearsal adapter, and the opt-in Alpaca external-paper adapter

- `agentic_trader/execution/`
  Broker-facing execution contracts such as `ExecutionIntent`, `ExecutionOutcome`, health summaries, and translation helpers between guard decisions and adapter submissions

- `agentic_trader/workflows/`
  Higher-level flow composition, replay, backtesting, review, and operator workflows

- `agentic_trader/researchd/`
  Optional research sidecar contracts for source health, evidence normalization, opt-in SEC EDGAR submissions metadata ingestion, optional Firecrawl/Camofox helper providers, file-backed world-state snapshots, and future CrewAI-backed deep-dive loops. It is a sidecar boundary only and does not own trading runtime orchestration, broker execution, or the main DuckDB writer.

- `tools/`
  Repo-owned optional helper infrastructure for local browser/model/fetcher tools. Camofox lives here today as loopback browser infrastructure; future Ollama and Firecrawl tool roots should hold app-managed configuration/assets or adapter metadata, not secrets or mandatory runtime dependencies. Root runtime code should prefer a central tool-readiness contract over ad hoc probes.

- `sidecars/research_flow/`
  Tracked but isolated CrewAI Flow sidecar package. uv owns its Python 3.13 environment and lockfile; the root runtime reports setup/readiness and may call its pure JSON contract through subprocess, but must not import this package directly.

- `agentic_trader/cli.py`, `main.py`, `agentic_trader/tui.py`
  Operator-facing control surfaces

- `agentic_trader/runtime_status.py`
  Shared runtime state interpretation and derived agent-activity summaries for observer surfaces

- `agentic_trader/runtime_feed.py`
  Sidecar-friendly runtime state, event, and stop-request contract for background supervision and UI attach flows

- `agentic_trader/observer_api.py`
  Local HTTP observer surface that exposes the same read-only runtime contracts for future WebUI attach flows

- `webgui/`
  Next.js App Router local operator shell. It must stay thin, local-first, and delegated to the existing dashboard/runtime/chat/instruction contracts rather than becoming a second runtime.

- `docs/`
  Fumadocs-based Next.js developer docs site. It documents the existing repository truth through curated MDX pages and should share the same frontend baseline without importing runtime logic.

- `.ai/qa/`
  Product-specific QA workflow, checklist, runbook, scenarios, and optional evidence artifacts for validating operator-facing behavior

- `.ai/agents/`
  Development-only role guidance for planning, implementation, review, QA, and data architecture collaboration. These documents do not define runtime agents and must not bypass the in-repo specialist graph.

## Configuration Reality

The runtime already supports:

- default local model selection
- role-based per-agent model overrides
- strict LLM availability checks
- market data cache directories
- news mode controls
- financial data provider readiness keys such as Finnhub, FMP, Polygon/Massive, and settings-only Alpaca paper readiness fields
- portfolio and risk limits

## Memory Reality

The memory layer is lightweight but real.
It already supports retrieving historically similar recorded runs and injecting that context into agent cycles.
It also now supports:

- hybrid heuristic + vector-style retrieval scoring
- shared memory bus propagation between stages
- explicit separation between trading memory and operator chat memory
- explicit memory write-policy rules by domain and actor

It should be treated as:

- retrieval support
- operator-inspectable context
- replay-aware evidence

It should not become:

- magic hidden behavior
- uncontrolled chat memory
- an untracked policy mutation layer

## Near-Term Architectural Direction

Good changes fit into one of these buckets:

- deepen unified context assembly
- improve provider abstraction and routing
- enrich memory retrieval and inspection
- strengthen manager conflict and consensus reasoning
- strengthen portfolio-aware reasoning
- improve daemon, CLI, and TUI consistency
- keep live agent progress readable without depending on direct DB reads
- keep daemon supervision metadata readable through sidecar contracts and not only through the database writer
- keep future live broker work behind the adapter boundary and explicit execution safety gates
- keep broker submissions flowing through `ExecutionIntent -> BrokerAdapter.place_order() -> ExecutionOutcome` so paper, simulated-real, and future live adapters share one auditable contract
- keep `alpaca_paper` explicitly separate from local `paper` and from blocked `live`; it may submit external paper orders only when the operator configures credentials, paper endpoint, and explicit enablement
- keep financial intelligence behind structured feature/provider boundaries so agents consume summarized technical, fundamental, and macro context instead of raw noisy data
- keep prompt rendering feature-first when `DecisionFeatureBundle` is attached; compact snapshots may remain internal for deterministic fallback, audit, and risk math
- keep canonical source attribution and freshness metadata attached whenever external provider data enters runtime or persisted review context
- keep research sidecars as local evidence companions that consume or emit structured packets through `runtime_feed` JSON snapshots without taking the DuckDB runtime writer role
- keep official research providers explicit and opt-in; SEC EDGAR submissions metadata is allowed only with watched symbols and a configured User-Agent, and full filing/XBRL parsing remains a separate future provider layer
- keep CrewAI or any future crew loop behind an optional adapter boundary; native runtime, replay, QA, and operator surfaces must keep working without it, and the tracked uv sidecar must communicate through subprocess JSON contracts rather than direct broker/runtime imports
- keep V1 scoped to Alpaca-ready US paper-first operation; defer IBKR/global/FX accounting to V2
- keep QA scenarios updated when runtime contracts, operator surfaces, or safety gates change
- keep `webgui` and `docs` aligned on the current Next.js App Router plus Tailwind v4 plus shadcn baseline while migrating the Web GUI screen by screen instead of through a one-shot CSS rewrite
- improve replay and backtest fidelity

## Architectural Anti-Goals

- replacing the current runtime with an external orchestration framework
- letting CrewAI or another sidecar framework replace the staged specialist graph, manager layer, execution guard, or broker adapter boundary
- building a cloud-first dependency into core trading flow
- converting the system into a generic assistant shell
