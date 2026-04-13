from datetime import datetime, timezone
from dataclasses import dataclass
from uuid import uuid4

from agentic_trader.config import Settings
from agentic_trader.schemas import ExecutionDecision, PositionExitDecision, StrategyPlan
from agentic_trader.storage.db import TradingDatabase


@dataclass(frozen=True)
class FillProjection:
    cash_delta: float
    realized_pnl_delta: float
    new_quantity: float
    new_average_price: float


class PaperBroker:
    def __init__(self, db: TradingDatabase, settings: Settings):
        """
        Initialize the PaperBroker with its persistence backend and configuration.
        
        Stores the provided TradingDatabase for reading/writing orders, fills, positions, and account snapshots, and stores Settings that govern broker constraints (e.g., shorting, exposure limits).
        """
        self.db = db
        self.settings = settings

    @staticmethod
    def _weighted_average(
        current_qty: float, current_avg: float, fill_qty: float, fill_price: float
    ) -> float:
        total_qty = current_qty + fill_qty
        if total_qty == 0:
            return 0.0
        return ((current_qty * current_avg) + (fill_qty * fill_price)) / total_qty

    def _apply_buy(
        self, *, quantity: float, price: float, current_qty: float, current_avg: float
    ) -> tuple[float, float, float, float]:
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

    def _apply_sell(
        self, *, quantity: float, price: float, current_qty: float, current_avg: float
    ) -> tuple[float, float, float, float]:
        """
        Compute the cash and realized PnL effects of selling a quantity and the resulting position quantity and average price.
        
        Parameters:
            quantity (float): Quantity being sold.
            price (float): Execution price per unit.
            current_qty (float): Current position quantity (positive for long, negative for short, zero for flat).
            current_avg (float): Current average price of the position.
        
        Returns:
            tuple[float, float, float, float]: A tuple containing:
                - cash_delta: change in cash from the sale (positive for proceeds),
                - realized_pnl_delta: realized profit or loss from any closed portion of the existing position,
                - new_quantity: resulting position quantity after applying the sale,
                - new_average_price: resulting average price for the position after the sale (0.0 if no remaining position).
        """
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

    def _record_order(self, order_id: str, decision: ExecutionDecision) -> None:
        """
        Persist an order record for the given decision to the trading database.
        
        Stores a snapshot of the order including creation timestamp, symbol, side, approval flag,
        entry/stop/take-profit prices, position size percentage, confidence, and rationale.
        
        Parameters:
            order_id (str): Unique identifier to associate with the persisted order.
            decision (ExecutionDecision): The execution decision whose fields (symbol, side, approved,
                entry_price, stop_loss, take_profit, position_size_pct, confidence, rationale) are recorded.
        """
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

    def _project_fill(
        self,
        decision: ExecutionDecision,
        *,
        quantity: float,
        current_qty: float,
        current_avg: float,
    ) -> FillProjection | None:
        """
        Create a FillProjection describing the effect of applying the requested fill, or return None when the fill is not applicable under shorting rules.
        
        Parameters:
            decision (ExecutionDecision): Execution decision containing `side` and `entry_price`.
            quantity (float): Quantity to be filled.
            current_qty (float): Current position quantity for the symbol.
            current_avg (float): Current average price for the position.
        
        Returns:
            FillProjection | None: A projection with `cash_delta`, `realized_pnl_delta`, `new_quantity`, and `new_average_price` if the fill can be applied; `None` when the decision would initiate a short position but shorting is disallowed and there is no existing long position.
        """
        if decision.side == "buy":
            values = self._apply_buy(
                quantity=quantity,
                price=decision.entry_price,
                current_qty=current_qty,
                current_avg=current_avg,
            )
        elif self.settings.allow_short or current_qty > 0:
            values = self._apply_sell(
                quantity=quantity,
                price=decision.entry_price,
                current_qty=current_qty,
                current_avg=current_avg,
            )
        else:
            return None
        cash_delta, realized_pnl_delta, new_quantity, new_average_price = values
        return FillProjection(
            cash_delta=cash_delta,
            realized_pnl_delta=realized_pnl_delta,
            new_quantity=new_quantity,
            new_average_price=new_average_price,
        )

    @staticmethod
    def _rejects_same_direction(decision: ExecutionDecision, current_qty: float) -> bool:
        """
        Determine whether an execution decision would increase exposure in the same direction as the current position.
        
        Parameters:
            decision (ExecutionDecision): The proposed execution decision; `decision.side` is expected to be "buy" or "sell".
            current_qty (float): Current position quantity (positive for long, negative for short).
        
        Returns:
            bool: `True` if the decision would add to the existing position in the same direction (buy into a long, sell into a short), `False` otherwise.
        """
        return (decision.side == "buy" and current_qty > 0) or (
            decision.side == "sell" and current_qty < 0
        )

    def _would_exceed_cash(
        self, decision: ExecutionDecision, current_qty: float, projected_cash: float
    ) -> bool:
        """
        Determine whether a proposed buy would push projected cash below zero when not currently short.
        
        Parameters:
            decision (ExecutionDecision): The execution decision; only the `side` field is used.
            current_qty (float): Current position quantity for the symbol.
            projected_cash (float): Account cash after applying the proposed fill projection.
        
        Returns:
            `True` if the decision is a buy, the current position is not short (quantity >= 0), and `projected_cash` is less than 0; `False` otherwise.
        """
        return decision.side == "buy" and current_qty >= 0 and projected_cash < 0

    def _would_exceed_exposure(
        self,
        decision: ExecutionDecision,
        projection: FillProjection,
        current_market_value: float,
    ) -> bool:
        """
        Determine whether applying the projected fill would cause gross exposure to exceed the account's maximum allowed gross exposure.
        
        Parameters:
            projection (FillProjection): Projected outcome of the fill (includes `new_quantity`).
            current_market_value (float): Absolute market value of the existing position being replaced or modified.
        
        Returns:
            True if projected gross exposure would be greater than account.equity * settings.max_gross_exposure_pct, False otherwise.
        """
        account = self.db.get_account_snapshot()
        current_gross_exposure = sum(
            abs(item.market_value) for item in self.db.list_positions()
        )
        projected_gross_exposure = (
            current_gross_exposure
            - current_market_value
            + abs(projection.new_quantity * decision.entry_price)
        )
        max_allowed_exposure = max(
            0.0, account.equity * self.settings.max_gross_exposure_pct
        )
        return projected_gross_exposure > max_allowed_exposure

    def _would_exceed_open_position_limit(
        self, current_qty: float, new_quantity: float
    ) -> bool:
        """
        Determine whether applying a projected change in position quantity would exceed the broker's maximum allowed open positions.
        
        Parameters:
            current_qty (float): Current position quantity for the symbol before the change.
            new_quantity (float): Projected position quantity for the symbol after the change.
        
        Returns:
            bool: `True` if the resulting number of open positions would be greater than settings.max_open_positions, `False` otherwise.
        """
        projected_open_positions = len(self.db.list_positions())
        if current_qty == 0 and new_quantity != 0:
            projected_open_positions += 1
        elif current_qty != 0 and new_quantity == 0:
            projected_open_positions -= 1
        return projected_open_positions > self.settings.max_open_positions

    def submit(self, decision: ExecutionDecision) -> str:
        """
        Submit an execution decision to the paper broker, persist the order, and apply a simulated fill if the decision is approved and passes risk/position constraints.
        
        Processes the given ExecutionDecision by recording the order, marking the symbol price, computing target quantity from account equity and position_size_pct, projecting the fill effects, and—if approved and all checks pass—applying a simulated fill to the database. If the decision is not approved, is a "hold", results in zero quantity, is invalid under shorting rules, or fails cash/exposure/open-position limits, the order is persisted but no fill is applied.
        
        Parameters:
            decision (ExecutionDecision): The execution decision containing symbol, side, entry_price, position_size_pct, approval flag, and related metadata.
        
        Returns:
            order_id (str): A unique paper order identifier (format "paper-<12 hex>") for the persisted order.
        """
        order_id = f"paper-{uuid4().hex[:12]}"
        self._record_order(order_id, decision)

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
        current_market_value = abs(position.market_value) if position else 0.0
        if self._rejects_same_direction(decision, current_qty):
            return order_id

        projection = self._project_fill(
            decision,
            quantity=quantity,
            current_qty=current_qty,
            current_avg=current_avg,
        )
        if projection is None:
            return order_id

        if self._would_exceed_cash(
            decision, current_qty, account.cash + projection.cash_delta
        ):
            return order_id

        if self._would_exceed_exposure(decision, projection, current_market_value):
            return order_id

        if self._would_exceed_open_position_limit(
            current_qty, projection.new_quantity
        ):
            return order_id

        self.db.apply_fill(
            fill_id=f"fill-{uuid4().hex[:12]}",
            order_id=order_id,
            symbol=decision.symbol,
            side=decision.side,
            quantity=quantity,
            price=decision.entry_price,
            cash_delta=projection.cash_delta,
            realized_pnl_delta=projection.realized_pnl_delta,
            new_quantity=projection.new_quantity,
            new_average_price=projection.new_average_price,
        )
        return order_id

    def record_position_plan(
        self,
        *,
        symbol: str,
        decision: ExecutionDecision,
        strategy: StrategyPlan,
        max_holding_bars: int,
    ) -> None:
        if not decision.approved or decision.side not in {"buy", "sell"}:
            return
        self.db.save_position_plan(
            symbol=symbol,
            side=decision.side,
            entry_price=decision.entry_price,
            stop_loss=decision.stop_loss,
            take_profit=decision.take_profit,
            max_holding_bars=max_holding_bars,
            holding_bars=0,
            invalidation_logic=strategy.invalidation_logic,
        )

    def close_position(self, decision: PositionExitDecision) -> str:
        position = self.db.get_position(decision.symbol)
        if position is None or position.quantity == 0:
            return f"paper-{uuid4().hex[:12]}"

        order_id = f"paper-{uuid4().hex[:12]}"
        quantity = abs(position.quantity)
        if decision.side == "buy":
            cash_delta, realized_pnl_delta, new_qty, new_avg = self._apply_buy(
                quantity=quantity,
                price=decision.exit_price,
                current_qty=position.quantity,
                current_avg=position.average_price,
            )
        else:
            cash_delta, realized_pnl_delta, new_qty, new_avg = self._apply_sell(
                quantity=quantity,
                price=decision.exit_price,
                current_qty=position.quantity,
                current_avg=position.average_price,
            )

        self.db.insert_order(
            {
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
        )
        self.db.apply_fill(
            fill_id=f"fill-{uuid4().hex[:12]}",
            order_id=order_id,
            symbol=decision.symbol,
            side=decision.side,
            quantity=quantity,
            price=decision.exit_price,
            cash_delta=cash_delta,
            realized_pnl_delta=realized_pnl_delta,
            new_quantity=new_qty,
            new_average_price=new_avg,
        )
        self.db.delete_position_plan(decision.symbol)
        self.db.close_trade_journal(
            symbol=decision.symbol,
            exit_order_id=order_id,
            exit_reason=decision.reason,
            exit_price=decision.exit_price,
            realized_pnl=realized_pnl_delta,
            notes=decision.rationale,
        )
        self.db.record_account_mark(
            source="position_closed",
            note=f"{decision.symbol} exited via {decision.reason}.",
            symbol=decision.symbol,
        )
        return order_id
