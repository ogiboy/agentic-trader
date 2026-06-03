"""Order record payload builders for the paper broker."""

from datetime import datetime, timezone

from agentic_trader.schemas import ExecutionDecision, PositionExitDecision


def order_record_from_decision(
    order_id: str,
    decision: ExecutionDecision,
) -> dict[str, object]:
    return {
        "order_id": order_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "symbol": decision.symbol,
        "side": decision.side,
        "approved": decision.approved,
        "entry_price": decision.entry_price,
        "stop_loss": decision.stop_loss,
        "take_profit": decision.take_profit,
        "position_size_pct": decision.position_size_pct,
        "confidence": decision.confidence,
        "rationale": decision.rationale,
    }


def exit_order_record(
    order_id: str,
    decision: PositionExitDecision,
) -> dict[str, object]:
    return {
        "order_id": order_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "symbol": decision.symbol,
        "side": decision.side,
        "approved": True,
        "entry_price": decision.exit_price,
        "stop_loss": decision.exit_price,
        "take_profit": decision.exit_price,
        "position_size_pct": 0.0,
        "confidence": 1.0,
        "rationale": f"Exit triggered: {decision.reason}. {decision.rationale}",
    }
