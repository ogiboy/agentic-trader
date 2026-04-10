# Architecture Notes

## High-Level Shape

The project already follows a staged, specialist-agent trading pipeline.

Current runtime stages:

1. Research Coordinator
2. Regime Agent
3. Strategy Selector
4. Risk Agent
5. Specialist Consensus Layer
6. Manager Agent
7. Execution Guard
8. Paper Broker

## Core Package Areas

- `agentic_trader/agents/`
  Specialist, manager, explainer, and instruction-oriented agent logic

- `agentic_trader/llm/`
  LLM provider access, provider adapters, model routing, and role-based model selection

- `agentic_trader/market/`
  Market data loading, feature preparation, and calendar/session context

- `agentic_trader/memory/`
  Similar-run retrieval, hybrid vector-style memory support, memory assembly, and memory inspection support

- `agentic_trader/storage/`
  DuckDB persistence for runs, fills, positions, journals, trade contexts, traces, and reports

- `agentic_trader/engine/`
  Runtime execution and orchestration mechanics, including the broker adapter boundary and the paper broker implementation

- `agentic_trader/workflows/`
  Higher-level flow composition, replay, backtesting, review, and operator workflows

- `agentic_trader/cli.py`, `main.py`, `agentic_trader/tui.py`
  Operator-facing control surfaces

- `agentic_trader/runtime_status.py`
  Shared runtime state interpretation and derived agent-activity summaries for observer surfaces

- `agentic_trader/runtime_feed.py`
  Sidecar-friendly runtime state, event, and stop-request contract for background supervision and UI attach flows

- `agentic_trader/observer_api.py`
  Local HTTP observer surface that exposes the same read-only runtime contracts for future WebUI attach flows

- `.ai/qa/`
  Product-specific QA workflow, checklist, runbook, scenarios, and optional evidence artifacts for validating operator-facing behavior

## Configuration Reality

The runtime already supports:

- default local model selection
- role-based per-agent model overrides
- strict LLM availability checks
- market data cache directories
- news mode controls
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
- keep QA scenarios updated when runtime contracts, operator surfaces, or safety gates change
- improve replay and backtest fidelity

## Architectural Anti-Goals

- replacing the current runtime with an external orchestration framework
- building a cloud-first dependency into core trading flow
- converting the system into a generic assistant shell
