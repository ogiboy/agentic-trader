from agentic_trader.schemas import InvestmentPreferences, SymbolIdentity


def _first_or_none(values: list[str]) -> str | None:
    return values[0] if values else None


def resolve_symbol_identity(
    symbol: str,
    preferences: InvestmentPreferences | None = None,
) -> SymbolIdentity:
    """Infer a structured symbol identity from the raw ticker and operator preferences."""
    normalized = symbol.strip().upper()
    if normalized.endswith(".IS"):
        return SymbolIdentity(
            symbol=normalized,
            exchange="BIST",
            currency="TRY",
            region="TR",
            asset_class="equity",
        )
    if normalized.endswith("-USD") or normalized.endswith("USDT"):
        return SymbolIdentity(
            symbol=normalized,
            exchange="CRYPTO",
            currency="USD",
            region="GLOBAL",
            asset_class="crypto",
        )

    exchange = _first_or_none(preferences.exchanges) if preferences else "NASDAQ"
    currency = _first_or_none(preferences.currencies) if preferences else "USD"
    region = _first_or_none(preferences.regions) if preferences else "US"
    return SymbolIdentity(
        symbol=normalized,
        exchange=exchange or "NASDAQ",
        currency=currency or "USD",
        region=region or "US",
        asset_class="equity",
    )
