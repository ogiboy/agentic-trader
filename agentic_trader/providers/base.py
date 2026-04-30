"""Small helpers shared by canonical data providers."""

from datetime import UTC, datetime

import pandas as pd

from agentic_trader.schemas import (
    DataProviderKind,
    DataSourceAttribution,
    DataSourceRole,
    FreshnessStatus,
    MarketDataSnapshot,
    MarketSnapshot,
    ProviderMetadata,
    SymbolIdentity,
)


def utc_now_iso() -> str:
    """Return an ISO timestamp in UTC for provider fetch metadata."""
    return datetime.now(UTC).isoformat()


def source_attribution(
    *,
    source_name: str,
    provider_type: DataProviderKind,
    source_role: DataSourceRole,
    fetched_at: str | None = None,
    freshness: FreshnessStatus = "unknown",
    confidence: float = 0.0,
    completeness: float = 0.0,
    notes: list[str] | None = None,
) -> DataSourceAttribution:
    """Build a bounded attribution object without leaking provider secrets."""
    return DataSourceAttribution(
        source_name=source_name,
        provider_type=provider_type,
        source_role=source_role,
        fetched_at=fetched_at,
        freshness=freshness,
        confidence=confidence,
        completeness=completeness,
        notes=list(notes or []),
    )


def metadata(
    *,
    provider_id: str,
    name: str,
    provider_type: DataProviderKind,
    role: DataSourceRole,
    priority: int = 100,
    enabled: bool = True,
    requires_network: bool = False,
    notes: list[str] | None = None,
) -> ProviderMetadata:
    """Build provider metadata with a consistent shape."""
    return ProviderMetadata(
        provider_id=provider_id,
        name=name,
        provider_type=provider_type,
        role=role,
        priority=priority,
        enabled=enabled,
        requires_network=requires_network,
        notes=list(notes or []),
    )


def index_label(value: object) -> str | None:
    """Format a pandas index value for persisted canonical metadata."""
    if value is None:
        return None
    isoformat = getattr(value, "isoformat", None)
    if callable(isoformat):
        return str(isoformat())
    return str(value)


def market_snapshot_from_frame(
    frame: pd.DataFrame,
    *,
    symbol: SymbolIdentity,
    interval: str,
    lookback: str | None,
    attribution: DataSourceAttribution,
) -> MarketDataSnapshot:
    """Summarize normalized OHLCV bars into canonical market metadata."""
    missing = [
        field
        for field in ("open", "high", "low", "close", "volume")
        if field not in frame.columns
    ]
    window_start = index_label(frame.index[0]) if len(frame.index) else None
    window_end = index_label(frame.index[-1]) if len(frame.index) else None
    last_close = None
    if "close" in frame.columns and not frame.empty:
        last_close = float(frame["close"].iloc[-1])

    return MarketDataSnapshot(
        symbol_identity=symbol,
        interval=interval,
        lookback=lookback,
        rows=int(len(frame)),
        columns=[str(column) for column in frame.columns],
        window_start=window_start,
        window_end=window_end,
        last_close=last_close,
        attribution=attribution,
        missing_fields=missing,
        summary=(
            f"{symbol.symbol} market data contains {len(frame)} row(s) "
            f"from {window_start or '-'} to {window_end or '-'}."
        ),
    )


def market_snapshot_from_runtime_snapshot(
    snapshot: MarketSnapshot,
    *,
    symbol: SymbolIdentity,
    lookback: str | None,
    source_name: str = "runtime_market_snapshot",
) -> MarketDataSnapshot:
    """Create canonical market metadata from the already-built runtime snapshot."""
    context_pack = snapshot.context_pack
    completeness = 0.8
    rows = snapshot.bars_analyzed
    if context_pack is not None and context_pack.coverage_ratio is not None:
        completeness = max(0.0, min(1.0, context_pack.coverage_ratio))
        rows = context_pack.bars_analyzed
    attribution = source_attribution(
        source_name=source_name,
        provider_type="market",
        source_role="inferred",
        fetched_at=snapshot.as_of or utc_now_iso(),
        freshness="unknown",
        confidence=0.8,
        completeness=completeness,
        notes=["canonicalized_from_runtime_snapshot"],
    )
    return MarketDataSnapshot(
        symbol_identity=symbol,
        interval=snapshot.interval,
        lookback=lookback,
        rows=rows,
        columns=["runtime_indicators", "market_context_pack"],
        window_start=context_pack.window_start if context_pack is not None else None,
        window_end=(
            context_pack.window_end if context_pack is not None else snapshot.as_of
        ),
        last_close=snapshot.last_close,
        attribution=attribution,
        missing_fields=[] if context_pack is not None else ["market_context_pack"],
        summary=(
            f"{symbol.symbol} canonical market context uses runtime snapshot "
            f"with {rows} analyzed bar(s)."
        ),
    )
