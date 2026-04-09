# Working Memory

## Stable Facts

- Default local model path is Ollama-class
- Role-based model routing already exists
- The project persists runtime artifacts into DuckDB
- The project already includes a lightweight retrieval layer
- The project now includes a hybrid heuristic + vector-style retrieval layer
- Shared memory bus entries are propagated across specialist stages
- The project already includes operator chat and safe instruction parsing
- The project already includes replay and backtesting surfaces

## Important Constraints

- Do not collapse specialist roles into a generic single-agent flow
- Do not mix conversational memory with trading memory
- Do not introduce silent cloud dependence
- Do not weaken strict runtime gating
- Do not let operator chat history bleed into execution-time context assembly

## Current Architectural Direction

- extend current memory rather than replacing it
- add provider adapters rather than changing agent workflow semantics
- keep operator-facing inspection strong
- keep runtime behavior replayable and reviewable
- keep memory writes explicit, inspectable, and role-aware
