"""Alpaca paper broker adapter implementation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from agentic_trader.config import Settings
from agentic_trader.engine.broker_utils import (
    ALPACA_CANCELLED_STATUSES,
    ALPACA_NO_FILL_STATUSES,
    ALPACA_REJECTED_STATUSES,
    alpaca_client_order_id,
    alpaca_credentials_ready,
    alpaca_uses_paper_endpoint,
    coerce_float,
)
from agentic_trader.engine.paper_broker import PaperBroker
from agentic_trader.execution.intent import (
    BrokerHealthcheck,
    ExecutionIntent,
    ExecutionOutcome,
    OpenOrderSnapshot,
)
from agentic_trader.execution.symbols import is_v1_us_equity_symbol
from agentic_trader.schemas import (
    ExecutionDecision,
    PortfolioSnapshot,
    PositionExitDecision,
    PositionSnapshot,
    StrategyPlan,
)
from agentic_trader.security import redact_sensitive_text
from agentic_trader.storage.db import TradingDatabase


@dataclass(slots=True)
class AlpacaPaperBrokerAdapter:
    """Opt-in Alpaca paper adapter for V1 US-equity readiness."""

    db: TradingDatabase
    settings: Settings
    backend_name: str = "alpaca_paper"
    _client: Any | None = field(default=None, init=False, repr=False)

    def _build_client(self) -> Any:
        if not self.settings.alpaca_paper_trading_enabled:
            raise RuntimeError(
                "Alpaca paper backend was requested but "
                "AGENTIC_TRADER_ALPACA_PAPER_TRADING_ENABLED is false."
            )
        if not alpaca_credentials_ready(self.settings):
            raise RuntimeError(
                "Alpaca paper backend requires AGENTIC_TRADER_ALPACA_API_KEY and "
                "AGENTIC_TRADER_ALPACA_SECRET_KEY."
            )
        if not alpaca_uses_paper_endpoint(self.settings):
            raise RuntimeError(
                "Alpaca paper backend requires the paper API endpoint. "
                f"Configured URL: {self.settings.alpaca_base_url}"
            )
        try:
            from alpaca.trading.client import TradingClient
        except Exception as exc:  # pragma: no cover - dependency import failure path
            raise RuntimeError(f"alpaca-py is not importable: {exc}") from exc
        return TradingClient(
            api_key=self.settings.alpaca_api_key,
            secret_key=self.settings.alpaca_secret_key,
            paper=True,
        )

    @property
    def client(self) -> Any:
        if self._client is None:
            self._client = self._build_client()
        return self._client

    @client.setter
    def client(self, value: Any) -> None:
        self._client = value

    def _blocked_outcome(
        self, intent: ExecutionIntent, *, reason: str, message: str
    ) -> ExecutionOutcome:
        """
        Create an ExecutionOutcome representing a blocked Alpaca paper order for the given intent.

        Parameters:
            intent (ExecutionIntent): The execution intent being blocked; its intent_id will be copied into the outcome.
            reason (str): A short machine-readable rejection reason.
            message (str): A human-readable message describing why the intent was blocked.

        Returns:
            ExecutionOutcome: An outcome with status "blocked", a generated Alpaca-paper order_id, adapter/backend set to Alpaca paper, and the provided rejection reason and message.
        """
        return ExecutionOutcome(
            intent_id=intent.intent_id,
            order_id=f"alpaca-paper-blocked-{uuid4().hex[:12]}",
            status="blocked",
            adapter_name=self.backend_name,
            execution_backend="alpaca_paper",
            rejection_reason=reason,
            message=message,
        )

    def _preflight_outcome(self, intent: ExecutionIntent) -> ExecutionOutcome | None:
        """
        Run a sequence of preflight validation checks for an execution intent and return the first blocking outcome.

        Performs basic validation, limit-order validation, a shorting-disabled check when selling and shorting is disallowed, and a risk-limit check in that order; returns the first produced `ExecutionOutcome` that represents a blocked or rejected preflight result, or `None` if the intent passes all checks.

        Parameters:
                intent (ExecutionIntent): The execution intent to validate.

        Returns:
                ExecutionOutcome | None: An `ExecutionOutcome` describing the blocking preflight failure, or `None` when no preflight check blocks the intent.
        """
        basic_outcome = self._basic_preflight_outcome(intent)
        if basic_outcome is not None:
            return basic_outcome
        limit_outcome = self._limit_order_preflight_outcome(intent)
        if limit_outcome is not None:
            return limit_outcome
        if intent.side == "sell" and not self.settings.allow_short:
            short_check = self._shorting_disabled_outcome(intent)
            if short_check is not None:
                return short_check
        risk_limit_outcome = self._risk_limit_outcome(intent)
        if risk_limit_outcome is not None:
            return risk_limit_outcome
        return None

    def _basic_preflight_outcome(
        self, intent: ExecutionIntent
    ) -> ExecutionOutcome | None:
        """
        Perform basic preflight checks on an execution intent and return a blocked outcome if any check fails.

        Checks include: intent approval and non-hold side, US V1 equity symbol scope, order type being `market` or `limit`, and presence of either `quantity` or `notional`.

        Returns:
            `ExecutionOutcome` describing the blocking reason when a check fails, `None` when the intent passes these basic validations.
        """
        if not intent.approved or intent.side == "hold":
            return self._blocked_outcome(
                intent,
                reason="intent_not_approved",
                message="Alpaca paper adapter did not submit an unapproved or hold intent.",
            )
        if not is_v1_us_equity_symbol(intent.symbol):
            return self._blocked_outcome(
                intent,
                reason="unsupported_symbol_scope",
                message="V1 Alpaca paper adapter only accepts simple US equity symbols.",
            )
        if intent.order_type not in {"market", "limit"}:
            return self._blocked_outcome(
                intent,
                reason="unsupported_order_type",
                message="V1 Alpaca paper adapter only accepts market or limit orders.",
            )
        if intent.quantity is None and intent.notional is None:
            return self._blocked_outcome(
                intent,
                reason="missing_size",
                message="Alpaca paper adapter requires quantity or notional.",
            )
        return None

    def _limit_order_preflight_outcome(
        self, intent: ExecutionIntent
    ) -> ExecutionOutcome | None:
        """
        Validate required fields for limit orders and produce a blocked outcome when a requirement is missing.

        Parameters:
            intent (ExecutionIntent): The execution intent to validate; checks are performed only when `intent.order_type` equals `"limit"`.

        Returns:
            ExecutionOutcome: An outcome with `status="blocked"` describing the missing requirement when `limit_price` or `quantity` is absent.
            None: When `intent.order_type` is not `"limit"` or all required fields are present.
        """
        if intent.order_type != "limit":
            return None
        if intent.limit_price is None:
            return self._blocked_outcome(
                intent,
                reason="missing_limit_price",
                message="Alpaca paper limit orders require limit_price.",
            )
        if intent.quantity is None:
            return self._blocked_outcome(
                intent,
                reason="limit_quantity_required",
                message="Alpaca paper limit orders require quantity.",
            )
        return None

    def _shorting_disabled_outcome(
        self, intent: ExecutionIntent
    ) -> ExecutionOutcome | None:
        """
        Determine whether an execution intent must be blocked because it would short a symbol when shorting is disabled.

        Parameters:
                intent (ExecutionIntent): The order intent whose size and side are evaluated. If `quantity` is absent, `notional` is converted to quantity using `reference_price`.

        Returns:
                ExecutionOutcome | None: An `ExecutionOutcome` with `reason` set to one of `"missing_size"`, `"position_lookup_failed"`, or `"shorting_disabled"` when the intent is blocked; `None` when the intent is allowed.
        """
        quantity = intent.quantity
        if quantity is None and intent.notional is not None:
            quantity = intent.notional / intent.reference_price
        if quantity is None:
            return self._blocked_outcome(
                intent,
                reason="missing_size",
                message="Alpaca paper adapter requires quantity or notional.",
            )
        try:
            current_qty = 0.0
            for position in self.get_positions():
                if position.symbol.upper() == intent.symbol.upper():
                    current_qty = position.quantity
                    break
        except Exception as exc:
            return self._blocked_outcome(
                intent,
                reason="position_lookup_failed",
                message=(
                    "Alpaca paper shorting check could not read positions: "
                    f"{redact_sensitive_text(exc, max_length=160)}"
                ),
            )
        if current_qty - quantity >= -1e-9:
            return None
        return self._blocked_outcome(
            intent,
            reason="shorting_disabled",
            message="Short sell intent blocked because shorting is disabled.",
        )

    def _risk_limit_outcome(self, intent: ExecutionIntent) -> ExecutionOutcome | None:
        """
        Assess whether an execution intent violates account risk limits and produce a blocking outcome when a violation or account-check failure is detected.

        Parameters:
            intent (ExecutionIntent): The proposed execution intent to evaluate.

        Returns:
            ExecutionOutcome | None: An `ExecutionOutcome` that blocks the intent when a risk check fails (e.g., insufficient equity, projected position size or gross exposure would exceed configured limits, or account/position lookup failed); `None` if the intent passes all risk checks.
        """
        try:
            account = self.get_account_state()
            positions = self.get_positions()
        except (
            Exception
        ) as exc:  # pragma: no cover - exercised through adapter boundary
            return self._blocked_outcome(
                intent,
                reason="risk_check_unavailable",
                message=(
                    "Alpaca paper risk check could not verify account exposure: "
                    f"{redact_sensitive_text(exc, max_length=160)}"
                ),
            )

        equity = account.equity
        if equity <= 0:
            return self._blocked_outcome(
                intent,
                reason="account_equity_unavailable",
                message="Alpaca paper risk check requires positive account equity.",
            )

        reference_price = intent.reference_price
        order_quantity = (
            intent.quantity
            if intent.quantity is not None
            else (intent.notional or 0.0) / reference_price
        )
        signed_order_quantity = (
            order_quantity if intent.side == "buy" else -order_quantity
        )

        current_position = next(
            (
                position
                for position in positions
                if position.symbol.upper() == intent.symbol.upper()
            ),
            None,
        )
        current_quantity = current_position.quantity if current_position else 0.0
        projected_quantity = current_quantity + signed_order_quantity
        current_symbol_exposure = (
            abs(current_position.market_value) if current_position else 0.0
        )
        projected_symbol_exposure = abs(projected_quantity * reference_price)
        current_gross_exposure = sum(
            abs(position.market_value) for position in positions
        )
        projected_gross_exposure = (
            current_gross_exposure - current_symbol_exposure + projected_symbol_exposure
        )

        max_position_value = equity * self.settings.max_position_pct
        if projected_symbol_exposure > max_position_value:
            return self._blocked_outcome(
                intent,
                reason="max_position_exceeded",
                message=(
                    "Alpaca paper order would exceed max position size: "
                    f"projected {projected_symbol_exposure:.2f} > "
                    f"limit {max_position_value:.2f}."
                ),
            )

        max_gross_value = equity * self.settings.max_gross_exposure_pct
        if projected_gross_exposure > max_gross_value:
            return self._blocked_outcome(
                intent,
                reason="max_gross_exposure_exceeded",
                message=(
                    "Alpaca paper order would exceed max gross exposure: "
                    f"projected {projected_gross_exposure:.2f} > "
                    f"limit {max_gross_value:.2f}."
                ),
            )
        return None

    @staticmethod
    def _order_kwargs(intent: ExecutionIntent) -> dict[str, object]:
        """
        Builds a dictionary of keyword arguments suitable for Alpaca order requests from an ExecutionIntent.

        Parameters:
            intent (ExecutionIntent): Execution intent containing symbol, side, order type, quantity or notional, limit price, and intent_id.

        Returns:
            dict[str, object]: Alpaca order request kwargs including:
                - symbol: uppercased symbol
                - side: Alpaca OrderSide enum value
                - type: Alpaca OrderType enum value
                - time_in_force: set to DAY
                - client_order_id: sanitized client id
                - qty or notional: present depending on which size field is provided
                - limit_price: included when the intent is a limit order
        """
        from alpaca.trading.enums import OrderSide, OrderType, TimeInForce

        order_type = (
            OrderType.LIMIT if intent.order_type == "limit" else OrderType.MARKET
        )
        kwargs: dict[str, object] = {
            "symbol": intent.symbol.upper(),
            "side": OrderSide.BUY if intent.side == "buy" else OrderSide.SELL,
            "type": order_type,
            "time_in_force": TimeInForce.DAY,
            "client_order_id": alpaca_client_order_id(intent.intent_id),
        }
        if intent.quantity is not None:
            kwargs["qty"] = intent.quantity
        elif intent.notional is not None:
            kwargs["notional"] = intent.notional
        if intent.order_type == "limit":
            kwargs["limit_price"] = intent.limit_price
        return kwargs

    def _outcome_from_order(
        self, intent: ExecutionIntent, order: object, *, action: str = "submitted"
    ) -> ExecutionOutcome:
        """
        Convert an Alpaca order object into an internal ExecutionOutcome with normalized status and redacted rejection details.

        Maps the order's filled quantity, average fill price, raw status, and reject reason into an ExecutionOutcome. Raw Alpaca statuses are mapped into internal status buckets (e.g., `rejected`, `partially_filled`, `cancelled`, `no_fill`, `filled`, `accepted`), and any rejection reason is redacted before inclusion.

        Parameters:
            action (str): Short verb describing the context for the outcome message (e.g., "submitted" or "refreshed").

        Returns:
            ExecutionOutcome: An ExecutionOutcome populated from the order, including normalized `status`, `filled_quantity`, optional `average_fill_price`, optional `rejection_reason` (redacted) and a human-readable `message` referencing the provided `action` and the broker's raw status.
        """
        filled_quantity = coerce_float(getattr(order, "filled_qty", 0.0))
        average_fill_price = coerce_float(
            getattr(order, "filled_avg_price", None), default=0.0
        )
        raw_status = str(getattr(order, "status", "accepted")).lower()
        if raw_status in ALPACA_REJECTED_STATUSES:
            status = "rejected"
        elif filled_quantity > 0 and (
            raw_status in ALPACA_CANCELLED_STATUSES
            or raw_status in ALPACA_NO_FILL_STATUSES
            or raw_status == "partially_filled"
        ):
            status = "partially_filled"
        elif raw_status in ALPACA_CANCELLED_STATUSES:
            status = "cancelled"
        elif raw_status in ALPACA_NO_FILL_STATUSES:
            status = "no_fill"
        elif filled_quantity > 0:
            status = "filled"
        else:
            status = "accepted"
        raw_rejection_reason = str(getattr(order, "reject_reason", "")) or None
        safe_rejection_reason = (
            redact_sensitive_text(raw_rejection_reason, max_length=160)
            if raw_rejection_reason
            else None
        )
        return ExecutionOutcome(
            intent_id=intent.intent_id,
            order_id=str(getattr(order, "id", f"alpaca-paper-{uuid4().hex[:12]}")),
            status=status,
            adapter_name=self.backend_name,
            execution_backend="alpaca_paper",
            filled_quantity=filled_quantity,
            average_fill_price=average_fill_price or None,
            rejection_reason=(
                safe_rejection_reason
                if status in {"cancelled", "no_fill", "rejected"}
                else None
            ),
            message=f"Alpaca paper order {action} with broker status {raw_status}.",
        )

    def place_order(self, intent: ExecutionIntent) -> ExecutionOutcome:
        """
        Submit the given execution intent to Alpaca Paper Trading after preflight validation.

        If a preflight check blocks the intent, that blocked outcome is returned. On success, the function constructs and submits either a `LimitOrderRequest` or `MarketOrderRequest` (based on `intent.order_type`) to the Alpaca TradingClient and converts the resulting Alpaca order into an `ExecutionOutcome`. If the alpaca request types cannot be imported, a `RuntimeError` is raised. If submission to Alpaca fails, an `ExecutionOutcome` with `status="rejected"` and `rejection_reason="alpaca_api_error"` is returned with a redacted error message.

        Parameters:
            intent (ExecutionIntent): The order intent to submit.

        Returns:
            ExecutionOutcome: The normalized outcome representing the submitted order or a blocked/rejected outcome.

        Raises:
            RuntimeError: If Alpaca request types (`LimitOrderRequest`, `MarketOrderRequest`) are unavailable.
        """
        preflight = self._preflight_outcome(intent)
        if preflight is not None:
            return preflight

        try:
            from alpaca.trading.requests import LimitOrderRequest, MarketOrderRequest
        except Exception as exc:  # pragma: no cover - dependency import failure path
            raise RuntimeError(
                f"alpaca-py trading request types are unavailable: {exc}"
            ) from exc

        try:
            request_cls = (
                LimitOrderRequest
                if intent.order_type == "limit"
                else MarketOrderRequest
            )
            order = self.client.submit_order(
                order_data=request_cls(**self._order_kwargs(intent))
            )
        except Exception as exc:
            return ExecutionOutcome(
                intent_id=intent.intent_id,
                order_id=f"alpaca-paper-error-{uuid4().hex[:12]}",
                status="rejected",
                adapter_name=self.backend_name,
                execution_backend="alpaca_paper",
                rejection_reason="alpaca_api_error",
                message=(
                    "Alpaca paper order submission failed: "
                    f"{redact_sensitive_text(exc, max_length=160)}"
                ),
            )
        return self._outcome_from_order(intent, order)

    def get_order_outcome(
        self, *, order_id: str, intent: ExecutionIntent
    ) -> ExecutionOutcome:
        """
        Refreshes an Alpaca order by ID and converts the retrieved order into an ExecutionOutcome.

        Parameters:
            order_id (str): Alpaca order identifier to fetch.
            intent (ExecutionIntent): Execution intent used to contextualize the outcome conversion.

        Returns:
            ExecutionOutcome: The normalized outcome representing the refreshed order state.

        Raises:
            RuntimeError: If fetching the order from Alpaca fails; the exception message is redacted.
        """
        try:
            order = self.client.get_order_by_id(order_id)
        except Exception as exc:
            raise RuntimeError(
                "Alpaca paper order status refresh failed: "
                f"{redact_sensitive_text(exc, max_length=160)}"
            ) from exc
        return self._outcome_from_order(intent, order, action="refreshed")

    def cancel_order(self, order_id: str) -> bool:
        """
        Cancel the Alpaca order identified by the given order ID.

        Returns:
            True if the cancellation request was issued.
        """
        self.client.cancel_order_by_id(order_id=order_id)
        return True

    def get_positions(self) -> list[PositionSnapshot]:
        positions: list[PositionSnapshot] = []
        for item in self.client.get_all_positions():
            positions.append(
                PositionSnapshot(
                    symbol=str(getattr(item, "symbol", "")),
                    quantity=coerce_float(getattr(item, "qty", 0.0)),
                    average_price=coerce_float(getattr(item, "avg_entry_price", 0.0)),
                    market_price=coerce_float(getattr(item, "current_price", 0.0)),
                    market_value=coerce_float(getattr(item, "market_value", 0.0)),
                    unrealized_pnl=coerce_float(getattr(item, "unrealized_pl", 0.0)),
                )
            )
        return positions

    def get_account_state(self) -> PortfolioSnapshot:
        account = self.client.get_account()
        positions = self.get_positions()
        return PortfolioSnapshot(
            cash=coerce_float(getattr(account, "cash", 0.0)),
            market_value=coerce_float(getattr(account, "long_market_value", 0.0))
            + coerce_float(getattr(account, "short_market_value", 0.0)),
            equity=coerce_float(getattr(account, "portfolio_value", 0.0)),
            realized_pnl=0.0,
            unrealized_pnl=sum(position.unrealized_pnl for position in positions),
            open_positions=len(positions),
        )

    def get_open_orders(self) -> list[OpenOrderSnapshot]:
        from alpaca.trading.enums import QueryOrderStatus
        from alpaca.trading.requests import GetOrdersRequest

        orders = self.client.get_orders(
            filter=GetOrdersRequest(status=QueryOrderStatus.OPEN)
        )
        snapshots: list[OpenOrderSnapshot] = []
        for item in orders:
            raw_side = str(getattr(item, "side", "buy")).lower()
            side = "sell" if raw_side == "sell" else "buy"
            snapshots.append(
                OpenOrderSnapshot(
                    order_id=str(getattr(item, "id", "")),
                    intent_id=str(getattr(item, "client_order_id", "")) or None,
                    symbol=str(getattr(item, "symbol", "")),
                    side=side,
                    quantity=coerce_float(getattr(item, "qty", 0.0)) or None,
                    notional=coerce_float(getattr(item, "notional", 0.0)) or None,
                    status=str(getattr(item, "status", "open")),
                    created_at=str(getattr(item, "created_at", "")),
                )
            )
        return snapshots

    def healthcheck(self) -> BrokerHealthcheck:
        if not self.settings.alpaca_paper_trading_enabled:
            return BrokerHealthcheck(
                adapter_name=self.backend_name,
                execution_backend="alpaca_paper",
                ok=False,
                blocked=True,
                message="Alpaca paper adapter is installed but explicit enablement is off.",
            )
        if not alpaca_credentials_ready(self.settings):
            return BrokerHealthcheck(
                adapter_name=self.backend_name,
                execution_backend="alpaca_paper",
                ok=False,
                blocked=True,
                message="Alpaca paper credentials are missing.",
            )
        if not alpaca_uses_paper_endpoint(self.settings):
            return BrokerHealthcheck(
                adapter_name=self.backend_name,
                execution_backend="alpaca_paper",
                ok=False,
                blocked=True,
                message="Alpaca paper adapter is not pointed at the paper endpoint.",
            )
        try:
            account = self.client.get_account()
        except Exception as exc:
            return BrokerHealthcheck(
                adapter_name=self.backend_name,
                execution_backend="alpaca_paper",
                ok=False,
                blocked=True,
                message=(
                    "Alpaca paper account health check failed: "
                    f"{redact_sensitive_text(exc, max_length=160)}"
                ),
            )
        status = str(getattr(account, "status", "unknown"))
        trading_blocked = bool(getattr(account, "trading_blocked", False))
        ok = status.lower() == "active" and not trading_blocked
        return BrokerHealthcheck(
            adapter_name=self.backend_name,
            execution_backend="alpaca_paper",
            ok=ok,
            blocked=not ok,
            message=(
                "Alpaca paper account is active."
                if ok
                else f"Alpaca paper account is not ready: status={status}."
            ),
        )

    def record_position_plan(
        self,
        *,
        symbol: str,
        decision: ExecutionDecision,
        strategy: StrategyPlan,
        max_holding_bars: int,
    ) -> None:
        # Keep the local review surface populated even when the fill is external paper.
        PaperBroker(self.db, self.settings).record_position_plan(
            symbol=symbol,
            decision=decision,
            strategy=strategy,
            max_holding_bars=max_holding_bars,
        )

    def close_position(self, decision: PositionExitDecision) -> str:
        """
        Close the position described by `decision` via the Alpaca trading client.

        Attempts to close when `decision.should_exit` is true and `decision.symbol` is a V1 US equity symbol; otherwise returns a unique token indicating a no-op or blocked outcome.

        Parameters:
            decision (PositionExitDecision): Decision carrying `should_exit` and `symbol`; `symbol` will be uppercased before submission.

        Returns:
            str: The Alpaca close operation identifier when submitted, or a unique no-op/blocked token when the close was not attempted or was blocked.
        """
        if not decision.should_exit:
            return f"alpaca-paper-noop-{uuid4().hex[:12]}"
        if not is_v1_us_equity_symbol(decision.symbol):
            return f"alpaca-paper-blocked-{uuid4().hex[:12]}"
        response = self.client.close_position(decision.symbol.upper())
        return str(getattr(response, "id", f"alpaca-paper-close-{uuid4().hex[:12]}"))
