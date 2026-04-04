from agentic_trader.schemas import ConfidenceCalibration, MarketSnapshot, TradeJournalEntry
from agentic_trader.storage.db import TradingDatabase


def _matching_entries(
    entries: list[TradeJournalEntry],
    snapshot: MarketSnapshot,
    *,
    strategy_family: str | None = None,
) -> list[TradeJournalEntry]:
    matches: list[TradeJournalEntry] = []
    for entry in entries:
        if entry.journal_status != "closed" or entry.realized_pnl is None:
            continue
        if entry.symbol == snapshot.symbol:
            matches.append(entry)
            continue
        if strategy_family is not None and entry.strategy_family == strategy_family:
            matches.append(entry)
    return matches


def build_confidence_calibration(
    db: TradingDatabase,
    snapshot: MarketSnapshot,
    *,
    strategy_family: str | None = None,
    limit: int = 100,
) -> ConfidenceCalibration:
    entries = db.list_trade_journal(limit=limit)
    matches = _matching_entries(entries, snapshot, strategy_family=strategy_family)
    if not matches:
        return ConfidenceCalibration(
            sample_size=0,
            closed_trades=0,
            win_rate=0.0,
            average_pnl=0.0,
            confidence_multiplier=1.0,
            notes=["No closed historical trades matched the current context."],
        )

    wins = sum(1 for entry in matches if (entry.realized_pnl or 0.0) > 0)
    average_pnl = sum(entry.realized_pnl or 0.0 for entry in matches) / len(matches)
    win_rate = wins / len(matches)

    multiplier = 1.0
    notes: list[str] = []
    if win_rate < 0.4 and average_pnl <= 0:
        multiplier = 0.85
        notes.append(
            "Historical results for similar trades were weak, so confidence should be capped."
        )
    elif win_rate < 0.5 and average_pnl < 0:
        multiplier = 0.92
        notes.append(
            "Historical results were slightly negative, so a mild confidence haircut is appropriate."
        )
    else:
        notes.append("Historical results do not require a defensive confidence haircut.")

    return ConfidenceCalibration(
        sample_size=len(matches),
        closed_trades=len(matches),
        win_rate=round(win_rate, 4),
        average_pnl=round(average_pnl, 4),
        confidence_multiplier=multiplier,
        notes=notes,
    )
