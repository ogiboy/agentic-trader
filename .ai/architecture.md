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
  LLM provider access, model routing, and role-based model selection

- `agentic_trader/market/`
  Market data loading, feature preparation, and calendar/session context

- `agentic_trader/memory/`
  Similar-run retrieval, hybrid vector-style memory support, memory assembly, and memory inspection support

- `agentic_trader/storage/`
  DuckDB persistence for runs, fills, positions, journals, traces, and reports

- `agentic_trader/engine/`
  Runtime execution and orchestration mechanics

- `agentic_trader/workflows/`
  Higher-level flow composition, replay, backtesting, review, and operator workflows

- `agentic_trader/cli.py`, `main.py`, `agentic_trader/tui.py`
  Operator-facing control surfaces

- `agentic_trader/runtime_status.py`
  Shared runtime state interpretation and derived agent-activity summaries for observer surfaces

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
- improve replay and backtest fidelity

## Architectural Anti-Goals

- replacing the current runtime with an external orchestration framework
- building a cloud-first dependency into core trading flow
- converting the system into a generic assistant shell
