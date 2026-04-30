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
- Root daily development targets Python 3.13 through the active `trader` Conda environment, while Poetry remains the root dependency lock/install owner
- The tracked CrewAI project lives under `sidecars/research-crewai/` and uses uv independently of the root Poetry environment
- The root runtime may call the CrewAI sidecar only through a subprocess JSON contract; it should not import CrewAI directly

## Important Constraints

- Do not collapse specialist roles into a generic single-agent flow
- Do not mix conversational memory with trading memory
- Do not introduce silent cloud dependence
- Do not weaken strict runtime gating
- Do not let operator chat history bleed into execution-time context assembly
- Do not let research sidecars or CrewAI loops become hidden execution, policy mutation, or raw web-text prompt injection paths
- Do not add CrewAI to the root Poetry dependency graph unless the sidecar boundary is intentionally redesigned
- Do not let runtime commands implicitly sync or upgrade the sidecar environment; setup/check commands own uv sync

## Current Architectural Direction

- extend current memory rather than replacing it
- add research sidecar memory inputs as normalized, source-attributed packets only
- evolve the CrewAI sidecar through explicit JSON contracts, not direct imports from the core trading runtime
- evaluate root uv migration separately as a plan-and-approval-gated simplification track
- add provider adapters rather than changing agent workflow semantics
- keep operator-facing inspection strong
- keep runtime behavior replayable and reviewable
- keep memory writes explicit, inspectable, and role-aware
