"""Research sidecar contracts for local-first intelligence gathering."""

from agentic_trader.researchd.orchestrator import (
    ResearchPipelineResult,
    ResearchSidecar,
    ResearchSidecarBackend,
)
from agentic_trader.researchd.control import (
    get_research_cycle_control,
    set_research_cycle_control,
)
from agentic_trader.researchd.persistence import (
    persist_research_result,
    record_from_pipeline_result,
)
from agentic_trader.researchd.status import build_research_sidecar_state

__all__ = [
    "ResearchPipelineResult",
    "ResearchSidecar",
    "ResearchSidecarBackend",
    "build_research_sidecar_state",
    "get_research_cycle_control",
    "persist_research_result",
    "record_from_pipeline_result",
    "set_research_cycle_control",
]
