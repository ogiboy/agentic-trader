from __future__ import annotations

import json
from importlib.metadata import version

from crewai.flow import Flow, start
from pydantic import BaseModel, Field

from research_crewai.contracts import ResearchCrewRequest, build_contract_output


class ResearchCrewState(BaseModel):
    """State contract for the placeholder research CrewAI Flow."""

    status: str = "ready"
    backend: str = "crewai"
    message: str = (
        "CrewAI sidecar scaffold is installed but not wired to researchd yet."
    )
    contract_version: str = "research-crewai.v1"
    raw_web_text_injected: bool = False
    broker_access: bool = False
    next_steps: list[str] = Field(
        default_factory=lambda: [
            "Read normalized research snapshots from the root runtime feed.",
            "Emit validated world-state or finding packets only.",
            "Keep execution and policy changes owned by the core runtime.",
        ]
    )


class ResearchCrewFlow(Flow[ResearchCrewState]):
    """Minimal CrewAI Flow boundary for future deep-dive research loops."""

    @start()
    def prepare_contract(self) -> dict[str, object]:
        payload = build_contract_output(ResearchCrewRequest()).model_dump(mode="json")
        print(json.dumps(payload, indent=2))
        return payload


def kickoff() -> None:
    """Run the placeholder CrewAI flow."""
    ResearchCrewFlow().kickoff()


def check() -> None:
    """Emit a dependency smoke payload without invoking LLM-backed agents."""
    payload = {
        "status": "ok",
        "package": "research-crewai",
        "crewai_version": version("crewai"),
        "contract_version": ResearchCrewState().contract_version,
    }
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    kickoff()
