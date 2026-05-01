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
- Root daily development targets Python 3.13 through uv-managed `.venv`, while uv owns the root dependency lock/install/run/build path
- The tracked CrewAI Flow project lives under `sidecars/research_flow/` and uses uv independently of the root uv environment
- The root runtime may call the CrewAI Flow sidecar only through a subprocess JSON contract; it should not import CrewAI directly
- SEC EDGAR submissions metadata is the first opt-in live research source, gated by `AGENTIC_TRADER_RESEARCH_SEC_EDGAR_ENABLED` and `AGENTIC_TRADER_RESEARCH_SEC_EDGAR_USER_AGENT`

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

## Current Architectural Direction

- extend current memory rather than replacing it
- add research sidecar memory inputs as normalized, source-attributed packets only
- evolve the CrewAI Flow sidecar through explicit JSON contracts, not direct imports from the core trading runtime
- keep root uv migration aligned across scripts, CI, docs, and release automation
- add provider adapters rather than changing agent workflow semantics
- expand SEC ingestion from metadata-only submissions into company facts and filing parsing only after the normalized evidence contract stays green
- keep operator-facing inspection strong
- keep runtime behavior replayable and reviewable
- keep memory writes explicit, inspectable, and role-aware
