from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, Protocol, cast
from uuid import uuid4

from agentic_trader.config import Settings
from agentic_trader.engine.paper_broker import PaperBroker
from agentic_trader.execution.intent import (
    BrokerHealthcheck,
    ExecutionIntent,
    ExecutionOutcome,
    OpenOrderSnapshot,
)
from agentic_trader.schemas import (
    ExecutionBackend,
    ExecutionDecision,
    PortfolioSnapshot,
    PositionExitDecision,
    PositionSnapshot,
    StrategyPlan,
)
from agentic_trader.security import redact_sensitive_text
from agentic_trader.storage.db import TradingDatabase


ALPACA_PAPER_ENDPOINT_HOST = "paper-api.alpaca.markets"
PAPER_BROKER_ACTIVE_MESSAGE = "Paper broker adapter is active."
ALPACA_REJECTED_STATUSES = {"rejected", "canceled", "cancelled", "expired"}


def _deterministic_unit_interval(seed: str, label: str) -> float:
    digest = hashlib.blake2b(f"{seed}:{label}".encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(digest, "big") / float(1 << 64)


def _deterministic_uniform(seed: str, label: str, low: float, high: float) -> float:
    return low + ((high - low) * _deterministic_unit_interval(seed, label))


class BrokerAdapter(Protocol):
    backend_name: str

    def place_order(self, intent: ExecutionIntent) -> ExecutionOutcome: ...

    def cancel_order(self, order_id: str) -> bool: ...

    def get_positions(self) -> list[PositionSnapshot]: ...

    def get_account_state(self) -> PortfolioSnapshot: ...

    def get_open_orders(self) -> list[OpenOrderSnapshot]: ...

    def healthcheck(self) -> BrokerHealthcheck: ...

    def record_position_plan(
        self,
        *,
        symbol: str,
        decision: ExecutionDecision,
        strategy: StrategyPlan,
        max_holding_bars: int,
    ) -> None: ...

    def close_position(self, decision: PositionExitDecision) -> str: ...


@dataclass(slots=True)
class PaperBrokerAdapter:
    db: TradingDatabase
    settings: Settings
    backend_name: str = "paper"
    _broker: PaperBroker = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._broker = PaperBroker(self.db, self.settings)

    def place_order(self, intent: ExecutionIntent) -> ExecutionOutcome:
        return self._broker.place_order(
            intent.model_copy(
                update={
                    "adapter_name": self.backend_name,
                    "execution_backend": "paper",
                }
            )
        )

    def submit(self, decision: ExecutionDecision) -> str:
        return self._broker.submit(decision)

    def cancel_order(self, order_id: str) -> bool:
        # Paper orders are immediate-fill/no-fill records, so there is nothing open to cancel.
        return any(order.order_id == order_id for order in self.get_open_orders())

    def get_positions(self) -> list[PositionSnapshot]:
        return self.db.list_positions()

    def get_account_state(self) -> PortfolioSnapshot:
        return self.db.get_account_snapshot()

    def get_open_orders(self) -> list[OpenOrderSnapshot]:
        return []

    def healthcheck(self) -> BrokerHealthcheck:
        return BrokerHealthcheck(
            adapter_name=self.backend_name,
            execution_backend="paper",
            ok=True,
            simulated=False,
            live=False,
            blocked=False,
            message=PAPER_BROKER_ACTIVE_MESSAGE,
        )

    def record_position_plan(
        self,
        *,
        symbol: str,
        decision: ExecutionDecision,
        strategy: StrategyPlan,
        max_holding_bars: int,
    ) -> None:
        self._broker.record_position_plan(
            symbol=symbol,
            decision=decision,
            strategy=strategy,
            max_holding_bars=max_holding_bars,
        )

    def close_position(self, decision: PositionExitDecision) -> str:
        return self._broker.close_position(decision)


@dataclass(slots=True)
class SimulatedRealBrokerAdapter:
    """Non-live adapter scaffold that applies deterministic market-friction metadata."""

    db: TradingDatabase
    settings: Settings
    backend_name: str = "simulated_real"
    _broker: PaperBroker = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._broker = PaperBroker(self.db, self.settings)

    def _simulation_metadata(self) -> dict[str, object]:
        return {
            "non_live": True,
            "simulated": True,
            "latency_ms": self.settings.simulated_latency_ms,
            "slippage_bps": self.settings.simulated_slippage_bps,
            "spread_bps": self.settings.simulated_spread_bps,
            "price_drift_bps": self.settings.simulated_price_drift_bps,
            "partial_fill_probability": self.settings.simulated_partial_fill_probability,
            "order_rejection_probability": self.settings.simulated_order_rejection_probability,
        }

    def _simulated_price(self, intent: ExecutionIntent) -> float:
        direction = 1.0 if intent.side == "buy" else -1.0
        drift_bps = _deterministic_uniform(
            intent.intent_id,
            "price_drift_bps",
            -self.settings.simulated_price_drift_bps,
            self.settings.simulated_price_drift_bps,
        )
        friction_bps = direction * (
            self.settings.simulated_slippage_bps
            + (self.settings.simulated_spread_bps / 2.0)
        )
        multiplier = 1.0 + ((friction_bps + drift_bps) / 10_000.0)
        return max(0.000001, intent.reference_price * multiplier)

    def _fill_ratio(self, intent: ExecutionIntent) -> float:
        if (
            _deterministic_unit_interval(intent.intent_id, "partial_fill_gate")
            >= self.settings.simulated_partial_fill_probability
        ):
            return 1.0
        return _deterministic_uniform(
            intent.intent_id,
            "partial_fill_ratio",
            self.settings.simulated_partial_fill_min_ratio,
            1.0,
        )

    def place_order(self, intent: ExecutionIntent) -> ExecutionOutcome:
        metadata = self._simulation_metadata()
        if (
            intent.approved
            and intent.side != "hold"
            and _deterministic_unit_interval(intent.intent_id, "order_rejection")
            < self.settings.simulated_order_rejection_probability
        ):
            rejected_intent = intent.model_copy(
                update={
                    "approved": False,
                    "adapter_name": self.backend_name,
                    "execution_backend": "simulated_real",
                    "thesis": f"Simulated-real rejection hook blocked the order. {intent.thesis}",
                }
            )
            outcome = self._broker.place_order(
                rejected_intent,
                order_prefix="simulated",
                simulated_metadata=metadata,
            )
            return outcome.model_copy(
                update={
                    "status": "rejected",
                    "adapter_name": self.backend_name,
                    "execution_backend": "simulated_real",
                    "rejection_reason": "simulated_rejection_hook",
                    "message": "Simulated-real adapter rejected the intent before fill.",
                    "simulated_metadata": metadata,
                }
            )

        fill_ratio = (
            self._fill_ratio(intent) if intent.approved and intent.side != "hold" else 1.0
        )
        simulated_intent = intent.model_copy(
            update={
                "adapter_name": self.backend_name,
                "execution_backend": "simulated_real",
                "reference_price": (
                    self._simulated_price(intent)
                    if intent.side != "hold"
                    else intent.reference_price
                ),
                "quantity": (
                    intent.quantity * fill_ratio
                    if intent.quantity is not None
                    else None
                ),
                "notional": (
                    intent.notional * fill_ratio
                    if intent.notional is not None
                    else None
                ),
                "backend_metadata": {
                    **intent.backend_metadata,
                    "simulated_fill_ratio": fill_ratio,
                },
            }
        )
        metadata["fill_ratio"] = fill_ratio
        outcome = self._broker.place_order(
            simulated_intent,
            order_prefix="simulated",
            simulated_metadata=metadata,
        )
        if outcome.status == "filled" and fill_ratio < 1.0:
            return outcome.model_copy(
                update={
                    "status": "partially_filled",
                    "message": "Simulated-real adapter produced a partial fill.",
                    "simulated_metadata": metadata,
                }
            )
        return outcome.model_copy(update={"simulated_metadata": metadata})

    def cancel_order(self, order_id: str) -> bool:
        return any(order.order_id == order_id for order in self.get_open_orders())

    def get_positions(self) -> list[PositionSnapshot]:
        return self.db.list_positions()

    def get_account_state(self) -> PortfolioSnapshot:
        return self.db.get_account_snapshot()

    def get_open_orders(self) -> list[OpenOrderSnapshot]:
        return []

    def healthcheck(self) -> BrokerHealthcheck:
        return BrokerHealthcheck(
            adapter_name=self.backend_name,
            execution_backend="simulated_real",
            ok=True,
            simulated=True,
            live=False,
            blocked=False,
            message="Simulated-real broker scaffold is active; no live trading is enabled.",
        )

    def record_position_plan(
        self,
        *,
        symbol: str,
        decision: ExecutionDecision,
        strategy: StrategyPlan,
        max_holding_bars: int,
    ) -> None:
        self._broker.record_position_plan(
            symbol=symbol,
            decision=decision,
            strategy=strategy,
            max_holding_bars=max_holding_bars,
        )

    def close_position(self, decision: PositionExitDecision) -> str:
        return self._broker.close_position(decision)


def _coerce_float(value: object, *, default: float = 0.0) -> float:
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


def alpaca_credentials_ready(settings: Settings) -> bool:
    return bool(settings.alpaca_api_key and settings.alpaca_secret_key)


def alpaca_uses_paper_endpoint(settings: Settings) -> bool:
    return ALPACA_PAPER_ENDPOINT_HOST in settings.alpaca_base_url.lower()


def is_v1_us_equity_symbol(symbol: str) -> bool:
    normalized = symbol.strip().upper()
    if not normalized or len(normalized) > 10:
        return False
    if not all(char.isalnum() or char in {".", "-"} for char in normalized):
        return False
    parts = normalized.split(".")
    if len(parts) > 2:
        return False
    if len(parts) == 2 and len(parts[1]) != 1:
        return False
    return True


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

    def _blocked_outcome(
        self, intent: ExecutionIntent, *, reason: str, message: str
    ) -> ExecutionOutcome:
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
        if intent.side == "sell" and not self.settings.allow_short:
            return self._blocked_outcome(
                intent,
                reason="shorting_disabled",
                message="Short sell intent blocked because shorting is disabled.",
            )
        if intent.quantity is None and intent.notional is None:
            return self._blocked_outcome(
                intent,
                reason="missing_size",
                message="Alpaca paper adapter requires quantity or notional.",
            )
        return None

    @staticmethod
    def _order_kwargs(intent: ExecutionIntent) -> dict[str, object]:
        from alpaca.trading.enums import OrderSide, OrderType, TimeInForce

        kwargs: dict[str, object] = {
            "symbol": intent.symbol.upper(),
            "side": OrderSide.BUY if intent.side == "buy" else OrderSide.SELL,
            "type": OrderType.MARKET,
            "time_in_force": TimeInForce.DAY,
        }
        if intent.quantity is not None:
            kwargs["qty"] = intent.quantity
        elif intent.notional is not None:
            kwargs["notional"] = intent.notional
        return kwargs

    def _outcome_from_order(self, intent: ExecutionIntent, order: object) -> ExecutionOutcome:
        filled_quantity = _coerce_float(getattr(order, "filled_qty", 0.0))
        average_fill_price = _coerce_float(
            getattr(order, "filled_avg_price", None), default=0.0
        )
        raw_status = str(getattr(order, "status", "accepted")).lower()
        status = "filled" if filled_quantity > 0 else "accepted"
        if raw_status in ALPACA_REJECTED_STATUSES:
            status = "rejected"
        return ExecutionOutcome(
            intent_id=intent.intent_id,
            order_id=str(getattr(order, "id", f"alpaca-paper-{uuid4().hex[:12]}")),
            status=status,
            adapter_name=self.backend_name,
            execution_backend="alpaca_paper",
            filled_quantity=filled_quantity,
            average_fill_price=average_fill_price or None,
            rejection_reason=(
                str(getattr(order, "reject_reason", "")) or None
                if status == "rejected"
                else None
            ),
            message=f"Alpaca paper order submitted with broker status {raw_status}.",
        )

    def place_order(self, intent: ExecutionIntent) -> ExecutionOutcome:
        preflight = self._preflight_outcome(intent)
        if preflight is not None:
            return preflight

        try:
            from alpaca.trading.requests import MarketOrderRequest
        except Exception as exc:  # pragma: no cover - dependency import failure path
            raise RuntimeError(
                f"alpaca-py trading request types are unavailable: {exc}"
            ) from exc

        try:
            order = self.client.submit_order(
                order_data=MarketOrderRequest(**self._order_kwargs(intent))
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

    def cancel_order(self, order_id: str) -> bool:
        self.client.cancel_order_by_id(order_id=order_id)
        return True

    def get_positions(self) -> list[PositionSnapshot]:
        positions: list[PositionSnapshot] = []
        for item in self.client.get_all_positions():
            positions.append(
                PositionSnapshot(
                    symbol=str(getattr(item, "symbol", "")),
                    quantity=_coerce_float(getattr(item, "qty", 0.0)),
                    average_price=_coerce_float(getattr(item, "avg_entry_price", 0.0)),
                    market_price=_coerce_float(getattr(item, "current_price", 0.0)),
                    market_value=_coerce_float(getattr(item, "market_value", 0.0)),
                    unrealized_pnl=_coerce_float(getattr(item, "unrealized_pl", 0.0)),
                )
            )
        return positions

    def get_account_state(self) -> PortfolioSnapshot:
        account = self.client.get_account()
        positions = self.get_positions()
        return PortfolioSnapshot(
            cash=_coerce_float(getattr(account, "cash", 0.0)),
            market_value=_coerce_float(getattr(account, "long_market_value", 0.0))
            + _coerce_float(getattr(account, "short_market_value", 0.0)),
            equity=_coerce_float(getattr(account, "portfolio_value", 0.0)),
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
                    quantity=_coerce_float(getattr(item, "qty", 0.0)) or None,
                    notional=_coerce_float(getattr(item, "notional", 0.0)) or None,
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
        if not decision.should_exit:
            return f"alpaca-paper-noop-{uuid4().hex[:12]}"
        if not is_v1_us_equity_symbol(decision.symbol):
            return f"alpaca-paper-blocked-{uuid4().hex[:12]}"
        response = self.client.close_position(decision.symbol.upper())
        return str(getattr(response, "id", f"alpaca-paper-close-{uuid4().hex[:12]}"))


def get_broker_adapter(*, db: TradingDatabase, settings: Settings) -> BrokerAdapter:
    if settings.execution_kill_switch_active:
        raise RuntimeError(
            "Execution kill switch is active. No broker adapter may submit orders."
        )
    if settings.execution_backend == "paper":
        return PaperBrokerAdapter(db, settings)
    if settings.execution_backend == "simulated_real":
        return SimulatedRealBrokerAdapter(db, settings)
    if settings.execution_backend == "alpaca_paper":
        return AlpacaPaperBrokerAdapter(db, settings)
    if settings.execution_backend == "live":
        if not settings.live_execution_enabled:
            raise RuntimeError(
                "Live execution backend was requested but live execution is disabled."
            )
        raise RuntimeError(
            "Live execution backend is configured but no live broker adapter is implemented yet."
        )
    raise RuntimeError(f"Unsupported execution backend: {settings.execution_backend}")


def _healthcheck_payload(settings: Settings) -> dict[str, object]:
    backend = cast(ExecutionBackend, settings.execution_backend)
    if settings.execution_kill_switch_active:
        return BrokerHealthcheck(
            adapter_name=backend,
            execution_backend=backend,
            ok=False,
            blocked=True,
            simulated=backend == "simulated_real",
            live=backend == "live",
            message="Execution kill switch is active.",
        ).model_dump(mode="json")
    if backend == "paper":
        return BrokerHealthcheck(
            adapter_name="paper",
            execution_backend="paper",
            ok=True,
            message=PAPER_BROKER_ACTIVE_MESSAGE,
        ).model_dump(mode="json")
    if backend == "simulated_real":
        return BrokerHealthcheck(
            adapter_name="simulated_real",
            execution_backend="simulated_real",
            ok=True,
            simulated=True,
            message="Simulated-real broker scaffold is active; no live trading is enabled.",
        ).model_dump(mode="json")
    if backend == "alpaca_paper":
        blocked_reasons: list[str] = []
        if not settings.alpaca_paper_trading_enabled:
            blocked_reasons.append("explicit_enablement_missing")
        if not alpaca_credentials_ready(settings):
            blocked_reasons.append("credentials_missing")
        if not alpaca_uses_paper_endpoint(settings):
            blocked_reasons.append("paper_endpoint_missing")
        ok = not blocked_reasons
        return BrokerHealthcheck(
            adapter_name="alpaca_paper",
            execution_backend="alpaca_paper",
            ok=ok,
            blocked=not ok,
            message=(
                "Alpaca paper adapter is configured for paper trading."
                if ok
                else f"Alpaca paper adapter is blocked: {', '.join(blocked_reasons)}."
            ),
        ).model_dump(mode="json")
    live_message = (
        "Live backend requested but live execution is disabled."
        if not settings.live_execution_enabled
        else "Live backend requested but no live broker adapter is implemented yet."
    )
    return BrokerHealthcheck(
        adapter_name="live",
        execution_backend="live",
        ok=False,
        live=True,
        blocked=True,
        message=live_message,
    ).model_dump(mode="json")


def broker_runtime_payload(settings: Settings) -> dict[str, object]:
    backend = settings.execution_backend
    live_requested = backend == "live"
    if settings.execution_kill_switch_active:
        state = "blocked"
        message = "Execution kill switch is active."
    elif backend == "paper":
        state = "paper"
        message = PAPER_BROKER_ACTIVE_MESSAGE
    elif backend == "simulated_real":
        state = "simulated"
        message = (
            "Simulated-real broker scaffold is active; live trading remains disabled."
        )
    elif backend == "alpaca_paper":
        healthcheck = _healthcheck_payload(settings)
        state = "alpaca_paper_ready" if healthcheck.get("ok") else "blocked"
        message = str(healthcheck.get("message", "Alpaca paper adapter status unknown."))
    elif not settings.live_execution_enabled:
        state = "blocked"
        message = "Live backend requested but live execution is disabled."
    else:
        state = "pending_live_adapter"
        message = (
            "Live backend requested but no live broker adapter is implemented yet."
        )
    return {
        "backend": backend,
        "adapter_name": backend,
        "execution_mode": backend,
        "simulated": backend == "simulated_real",
        "live": live_requested,
        "external_paper": backend == "alpaca_paper",
        "alpaca_paper_trading_enabled": settings.alpaca_paper_trading_enabled,
        "alpaca_paper_endpoint": settings.alpaca_base_url,
        "alpaca_data_feed": settings.alpaca_data_feed,
        "alpaca_credentials_configured": alpaca_credentials_ready(settings),
        "live_execution_enabled": settings.live_execution_enabled,
        "kill_switch_active": settings.execution_kill_switch_active,
        "state": state,
        "message": message,
        "live_requested": live_requested,
        "live_ready": False,
        "healthcheck": _healthcheck_payload(settings),
    }
