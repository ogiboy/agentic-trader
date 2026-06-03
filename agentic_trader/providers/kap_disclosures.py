"""KAP public-disclosure provider scaffold."""

from agentic_trader.config import Settings
from agentic_trader.providers.base import metadata
from agentic_trader.schemas import DisclosureEvent, ProviderMetadata, SymbolIdentity

KAP_DISCLOSURE_NOTES = ["turkey_public_disclosure_platform", "ingestion_pending"]


class KapDisclosureProvider:
    """KAP scaffold for future Turkey public disclosure ingestion."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def metadata(self) -> ProviderMetadata:
        """Return provider metadata for the KAP disclosure scaffold."""
        return metadata(
            provider_id="kap_disclosures",
            name="KAP Disclosures",
            provider_type="disclosure",
            role="primary",
            priority=10,
            enabled=True,
            requires_network=False,
            notes=KAP_DISCLOSURE_NOTES,
        )

    def get_disclosures(
        self, symbol: SymbolIdentity, *, limit: int
    ) -> list[DisclosureEvent]:
        """Return KAP disclosure events once ingestion is implemented."""
        _ = (symbol, limit, self._settings)
        return []
