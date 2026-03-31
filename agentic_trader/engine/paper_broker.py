from datetime import datetime, timezone
from uuid import uuid4

from agentic_trader.config import Settings
from agentic_trader.schemas import ExecutionDecision
from agentic_trader.storage.db import TradingDatabase


class PaperBroker:
    def __init__(self, db: TradingDatabase, settings: Settings):
        self.db = db
        self.settings = settings

    @staticmethod
    def _weighted_average(current_qty: float, current_avg: float, fill_qty: float, fill_price: float) -> float:
        total_qty = current_qty + fill_qty
        if total_qty == 0:
            return 0.0
        return ((current_qty * current_avg) + (fill_qty * fill_price)) / total_qty

    def _apply_buy(self, *, quantity: float, price: float, current_qty: float, current_avg: float) -> tuple[float, float, float, float]:
        cash_delta = -(quantity * price)
        realized_pnl_delta = 0.0

        if current_qty < 0:
            cover_qty = min(quantity, abs(current_qty))
            realized_pnl_delta += (current_avg - price) * cover_qty
            remaining_buy = quantity - cover_qty
            new_qty = current_qty + quantity
            if new_qty > 0:
                new_avg = price if remaining_buy > 0 else 0.0
            elif new_qty == 0:
                new_avg = 0.0
            else:
                new_avg = current_avg
            return cash_delta, realized_pnl_delta, new_qty, new_avg

        new_qty = current_qty + quantity
        new_avg = self._weighted_average(current_qty, current_avg, quantity, price)
        return cash_delta, realized_pnl_delta, new_qty, new_avg

    def _apply_sell(self, *, quantity: float, price: float, current_qty: float, current_avg: float) -> tuple[float, float, float, float]:
        cash_delta = quantity * price
        realized_pnl_delta = 0.0

        if current_qty > 0:
            close_qty = min(quantity, current_qty)
            realized_pnl_delta += (price - current_avg) * close_qty
            remaining_sell = quantity - close_qty
            new_qty = current_qty - quantity
            if new_qty < 0:
                new_avg = price if remaining_sell > 0 else 0.0
            elif new_qty == 0:
                new_avg = 0.0
            else:
                new_avg = current_avg
            return cash_delta, realized_pnl_delta, new_qty, new_avg

        new_qty = current_qty - quantity
        new_avg = self._weighted_average(abs(current_qty), current_avg, quantity, price)
        return cash_delta, realized_pnl_delta, new_qty, new_avg

    def submit(self, decision: ExecutionDecision) -> str:
        order_id = f"paper-{uuid4().hex[:12]}"
        self.db.insert_order(
            {
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
        )

        self.db.mark_price(decision.symbol, decision.entry_price)
        if not decision.approved or decision.side == "hold":
            return order_id

        account = self.db.get_account_snapshot()
        notional = max(0.0, account.equity * decision.position_size_pct)
        quantity = round(notional / decision.entry_price, 6)
        if quantity == 0:
            return order_id

        position = self.db.get_position(decision.symbol)
        current_qty = position.quantity if position else 0.0
        current_avg = position.average_price if position else 0.0

        if decision.side == "buy":
            cash_delta, realized_pnl_delta, new_qty, new_avg = self._apply_buy(
                quantity=quantity,
                price=decision.entry_price,
                current_qty=current_qty,
                current_avg=current_avg,
            )
        else:
            if decision.side == "sell" and not self.settings.allow_short and current_qty <= 0:
                return order_id
            cash_delta, realized_pnl_delta, new_qty, new_avg = self._apply_sell(
                quantity=quantity,
                price=decision.entry_price,
                current_qty=current_qty,
                current_avg=current_avg,
            )

        self.db.apply_fill(
            fill_id=f"fill-{uuid4().hex[:12]}",
            order_id=order_id,
            symbol=decision.symbol,
            side=decision.side,
            quantity=quantity,
            price=decision.entry_price,
            cash_delta=cash_delta,
            realized_pnl_delta=realized_pnl_delta,
            new_quantity=new_qty,
            new_average_price=new_avg,
        )
        return order_id
