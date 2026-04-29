"""Research sidecar contracts for local-first intelligence gathering."""

from agentic_trader.researchd.orchestrator import (
    ResearchPipelineResult,
    ResearchSidecar,
    ResearchSidecarBackend,
)
from agentic_trader.researchd.status import build_research_sidecar_state

__all__ = [
    "ResearchPipelineResult",
    "ResearchSidecar",
    "ResearchSidecarBackend",
    "build_research_sidecar_state",
]
