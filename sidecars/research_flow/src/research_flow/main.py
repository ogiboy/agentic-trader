from __future__ import annotations

import json
from importlib.metadata import version

from crewai.flow import Flow, start
from pydantic import BaseModel, Field

from research_flow.contracts import (
    CONTRACT_VERSION,
    ResearchFlowRequest,
    build_contract_output,
)


class ResearchFlowState(BaseModel):
    """State contract for the placeholder research CrewAI Flow."""

    status: str = "ready"
    backend: str = "crewai"
    package: str = "research_flow"
    message: str = "CrewAI Flow sidecar is installed and contract-ready."
    contract_version: str = CONTRACT_VERSION
    raw_web_text_injected: bool = False
    broker_access: bool = False
    next_steps: list[str] = Field(
        default_factory=lambda: [
            "Read normalized research packets from the root researchd process.",
            "Emit validated world-state, finding, and task-plan packets only.",
            "Keep execution and policy changes owned by the core runtime.",
        ]
    )


class ResearchFlow(Flow[ResearchFlowState]):
    """Minimal CrewAI Flow boundary for future deep-dive research loops."""

    @start()
    def prepare_contract(self) -> dict[str, object]:
        payload = build_contract_output(ResearchFlowRequest()).model_dump(mode="json")
        print(json.dumps(payload, indent=2))
        return payload


def kickoff() -> None:
    """Run the placeholder CrewAI Flow."""
    ResearchFlow().kickoff()


def plot() -> None:
    """Render the CrewAI Flow graph for local inspection."""
    ResearchFlow().plot()


def check() -> None:
    """Emit a dependency smoke payload without invoking LLM-backed agents."""
    payload = {
        "status": "ok",
        "package": "research_flow",
        "crewai_version": version("crewai"),
        "contract_version": CONTRACT_VERSION,
    }
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    kickoff()
