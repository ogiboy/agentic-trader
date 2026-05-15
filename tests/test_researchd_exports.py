from agentic_trader import researchd


def test_researchd_exports_sidecar_contracts() -> None:
    assert researchd.ResearchSidecarBackend is not None
    assert researchd.ResearchSidecar is not None
    assert researchd.ResearchPipelineResult is not None
    assert researchd.build_research_sidecar_state is not None
