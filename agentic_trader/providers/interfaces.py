"""Typed provider contracts for external data sources."""

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

import pandas as pd

from agentic_trader.schemas import (
    DisclosureEvent,
    FundamentalSnapshot,
    MacroSnapshot,
    MarketDataSnapshot,
    ProviderMetadata,
    SymbolIdentity,
    NewsEvent,
)


@dataclass(frozen=True)
class MarketDataResult:
    """Normalized market bars plus their canonical metadata snapshot."""

    frame: pd.DataFrame
    snapshot: MarketDataSnapshot


@runtime_checkable
class MarketDataProvider(Protocol):
    """Provider contract for OHLCV-style market data."""

    def metadata(self) -> ProviderMetadata:
        """Return provider identity, source role, and operational metadata."""
        ...

    def get_market_data(
        self, symbol: SymbolIdentity, *, interval: str, lookback: str
    ) -> MarketDataResult:
        """Fetch and normalize market data for the symbol/window."""
        ...


@runtime_checkable
class FundamentalDataProvider(Protocol):
    """Provider contract for structured company fundamentals."""

    def metadata(self) -> ProviderMetadata:
        """Return provider identity, source role, and operational metadata."""
        ...

    def get_fundamental_data(self, symbol: SymbolIdentity) -> FundamentalSnapshot:
        """Fetch or build a canonical fundamental snapshot."""
        ...


@runtime_checkable
class NewsProvider(Protocol):
    """Provider contract for structured company, sector, and macro news."""

    def metadata(self) -> ProviderMetadata:
        """Return provider identity, source role, and operational metadata."""
        ...

    def get_news(self, symbol: SymbolIdentity, *, limit: int) -> list[NewsEvent]:
        """Fetch canonical news events for a symbol."""
        ...


@runtime_checkable
class DisclosureProvider(Protocol):
    """Provider contract for filings, disclosures, and material events."""

    def metadata(self) -> ProviderMetadata:
        """Return provider identity, source role, and operational metadata."""
        ...

    def get_disclosures(
        self, symbol: SymbolIdentity, *, limit: int
    ) -> list[DisclosureEvent]:
        """Fetch canonical disclosure events for a symbol."""
        ...


@runtime_checkable
class MacroDataProvider(Protocol):
    """Provider contract for regional macro context."""

    def metadata(self) -> ProviderMetadata:
        """Return provider identity, source role, and operational metadata."""
        ...

    def get_macro_context(self, symbol: SymbolIdentity) -> MacroSnapshot:
        """Fetch or build a canonical macro snapshot for the symbol region."""
        ...
