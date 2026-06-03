"""Alpaca paper broker adapter implementation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from agentic_trader.config import Settings
from agentic_trader.engine.alpaca_mapping import (
    alpaca_order_kwargs,
    open_order_snapshot_from_alpaca_order,
    outcome_from_alpaca_order,
    portfolio_snapshot_from_alpaca_account,
    position_snapshot_from_alpaca_position,
)
from agentic_trader.engine.alpaca_risk import (
    RiskExposureProjection,
    basic_preflight_outcome,
    blocked_alpaca_outcome,
    gross_limit_outcome,
    limit_order_preflight_outcome,
    position_limit_outcome,
    risk_exposure_projection,
)
from agentic_trader.engine.broker_utils import (
    alpaca_credentials_ready,
    alpaca_uses_paper_endpoint,
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
        return blocked_alpaca_outcome(
            intent,
            backend_name=self.backend_name,
            reason=reason,
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
        return basic_preflight_outcome(intent, backend_name=self.backend_name)

    def _limit_order_preflight_outcome(
        self, intent: ExecutionIntent
    ) -> ExecutionOutcome | None:
        return limit_order_preflight_outcome(intent, backend_name=self.backend_name)

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

    def _risk_exposure_projection(
        self,
        *,
        intent: ExecutionIntent,
        positions: list[PositionSnapshot],
        equity: float,
    ) -> RiskExposureProjection:
        return risk_exposure_projection(
            intent=intent,
            positions=positions,
            equity=equity,
            max_position_pct=self.settings.max_position_pct,
            max_gross_exposure_pct=self.settings.max_gross_exposure_pct,
        )

    def _position_limit_outcome(
        self,
        intent: ExecutionIntent,
        projection: RiskExposureProjection,
    ) -> ExecutionOutcome | None:
        return position_limit_outcome(
            intent,
            projection,
            backend_name=self.backend_name,
        )

    def _gross_limit_outcome(
        self,
        intent: ExecutionIntent,
        projection: RiskExposureProjection,
    ) -> ExecutionOutcome | None:
        return gross_limit_outcome(
            intent,
            projection,
            backend_name=self.backend_name,
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

        projection = self._risk_exposure_projection(
            intent=intent,
            positions=positions,
            equity=equity,
        )
        return self._position_limit_outcome(
            intent,
            projection,
        ) or self._gross_limit_outcome(intent, projection)

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
                order_data=request_cls(**alpaca_order_kwargs(intent))
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
        return outcome_from_alpaca_order(
            intent,
            order,
            adapter_name=self.backend_name,
        )

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
        return outcome_from_alpaca_order(
            intent,
            order,
            adapter_name=self.backend_name,
            action="refreshed",
        )

    def cancel_order(self, order_id: str) -> bool:
        """
        Cancel the Alpaca order identified by the given order ID.

        Returns:
            True if the cancellation request was issued.
        """
        self.client.cancel_order_by_id(order_id=order_id)
        return True

    def get_positions(self) -> list[PositionSnapshot]:
        return [
            position_snapshot_from_alpaca_position(item)
            for item in self.client.get_all_positions()
        ]

    def get_account_state(self) -> PortfolioSnapshot:
        account = self.client.get_account()
        positions = self.get_positions()
        return portfolio_snapshot_from_alpaca_account(
            account,
            positions=positions,
        )

    def get_open_orders(self) -> list[OpenOrderSnapshot]:
        from alpaca.trading.enums import QueryOrderStatus
        from alpaca.trading.requests import GetOrdersRequest

        orders = self.client.get_orders(
            filter=GetOrdersRequest(status=QueryOrderStatus.OPEN)
        )
        return [open_order_snapshot_from_alpaca_order(item) for item in orders]

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
