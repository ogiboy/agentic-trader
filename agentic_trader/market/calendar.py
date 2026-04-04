from datetime import UTC, datetime, time
from zoneinfo import ZoneInfo

from agentic_trader.schemas import InvestmentPreferences, MarketSessionStatus

US_TZ = ZoneInfo("America/New_York")
TR_TZ = ZoneInfo("Europe/Istanbul")


def _is_crypto_symbol(symbol: str) -> bool:
    upper = symbol.upper()
    return (
        upper.endswith("-USD")
        or upper.endswith("-USDT")
        or upper in {"BTC", "ETH", "SOL", "BNB"}
    )


def _session_state_for_local_time(
    *,
    local_dt: datetime,
    open_time: time,
    close_time: time,
) -> str:
    if local_dt.weekday() >= 5:
        return "weekend"
    current = local_dt.time()
    if open_time <= current <= close_time:
        return "open"
    return "closed"


def infer_market_session(
    *,
    symbol: str,
    preferences: InvestmentPreferences,
    now_utc: datetime | None = None,
) -> MarketSessionStatus:
    current_utc = now_utc or datetime.now(UTC)
    upper_symbol = symbol.upper()

    if _is_crypto_symbol(upper_symbol):
        return MarketSessionStatus(
            symbol=symbol,
            venue="CRYPTO",
            asset_class="crypto",
            timezone="UTC",
            session_state="always_open",
            tradable_now=True,
            note="Crypto markets are treated as 24/7 in the current runtime.",
        )

    if (
        upper_symbol.endswith(".IS")
        or "BIST" in preferences.exchanges
        or "TR" in preferences.regions
    ):
        local_dt = current_utc.astimezone(TR_TZ)
        state = _session_state_for_local_time(
            local_dt=local_dt, open_time=time(10, 0), close_time=time(18, 0)
        )
        return MarketSessionStatus(
            symbol=symbol,
            venue="BIST",
            asset_class="equity",
            timezone="Europe/Istanbul",
            session_state=state,
            tradable_now=state == "open",
            note="BIST cash session heuristic: weekdays 10:00-18:00 Europe/Istanbul.",
        )

    local_dt = current_utc.astimezone(US_TZ)
    state = _session_state_for_local_time(
        local_dt=local_dt, open_time=time(9, 30), close_time=time(16, 0)
    )
    return MarketSessionStatus(
        symbol=symbol,
        venue="US",
        asset_class="equity",
        timezone="America/New_York",
        session_state=state,
        tradable_now=state == "open",
        note="US cash session heuristic: weekdays 09:30-16:00 America/New_York.",
    )
