from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from urllib.parse import urlparse
from typing import Any, Callable, Protocol, cast
from uuid import uuid4

from agentic_trader.config import Settings
from agentic_trader.engine.paper_broker import PaperBroker
from agentic_trader.execution.intent import (
    BrokerHealthcheck,
    ExecutionIntent,
    ExecutionOutcome,
    OpenOrderSnapshot,
)
from agentic_trader.execution.symbols import is_v1_us_equity_symbol
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
ALPACA_CANCELLED_STATUSES = {"canceled", "cancelled"}
ALPACA_NO_FILL_STATUSES = {"expired"}
ALPACA_REJECTED_STATUSES = {"rejected"}


def _deterministic_unit_interval(seed: str, label: str) -> float:
    """
    Deterministically derive a float in the interval [0, 1) from a seed and label.
    
    Parameters:
        seed (str): Primary seed value used to derive the output.
        label (str): Secondary label to produce a distinct value for the same seed.
    
    Returns:
        float: A deterministic pseudorandom value in [0, 1).
    """
    digest = hashlib.blake2b(f"{seed}:{label}".encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(digest, "big") / float(1 << 64)


def _deterministic_uniform(seed: str, label: str, low: float, high: float) -> float:
    """
    Map a deterministic pseudo-random value derived from `seed` and `label` into the interval [low, high).
    
    Parameters:
    	seed (str): Primary seed string used to derive the deterministic value.
    	label (str): Secondary label appended to the seed to namespace the result.
    	low (float): Lower bound of the target interval (inclusive).
    	high (float): Upper bound of the target interval (exclusive).
    
    Returns:
    	A float in the interval [low, high).
    """
    return low + ((high - low) * _deterministic_unit_interval(seed, label))


def _alpaca_client_order_id(intent_id: str) -> str:
    """
    Produce a sanitized client order identifier suitable for Alpaca: contains only alphanumeric characters, hyphen, or underscore and is at most 48 characters long.
    
    Parameters:
        intent_id (str): Original intent identifier to sanitize.
    
    Returns:
        str: A client order id containing only letters, digits, '-' and '_' truncated to 48 characters. If `intent_id` contains no allowed characters, returns a generated identifier starting with `"intent-"`.
    """
    cleaned = "".join(
        char for char in intent_id if char.isalnum() or char in {"-", "_"}
    )
    return (cleaned or f"intent-{uuid4().hex[:12]}")[:48]


class BrokerAdapter(Protocol):
    backend_name: str

    def place_order(self, intent: ExecutionIntent) -> ExecutionOutcome:
        """
        Submit an execution intent and return the broker outcome.

        Parameters:
            intent: Order intent containing symbol, side, sizing, pricing, and execution metadata.

        Returns:
            Snapshot of the accepted, filled, rejected, cancelled, blocked, or no-fill order state.
        """
        ...

    def get_order_outcome(
        self, *, order_id: str, intent: ExecutionIntent
    ) -> ExecutionOutcome:
        """
        Fetch the latest execution outcome for a previously submitted order.

        Parameters:
            order_id: Broker-assigned identifier for the order to refresh.
            intent: Original execution intent used as lookup context.

        Returns:
            ExecutionOutcome: The canonical execution outcome record for the given order and intent.
        """
        ...

    def cancel_order(self, order_id: str) -> bool:
        """
        Attempt to cancel an order by its identifier.

        Parameters:
            order_id: Broker-specific order identifier to cancel.

        Returns:
            True when the order was successfully cancelled, otherwise false.
        """
        ...

    def get_positions(self) -> list[PositionSnapshot]:
        """
        Return current account position snapshots.

        Returns:
            Current position snapshots, or an empty list when there are no positions.
        """
        ...

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

    def close_position(self, decision: PositionExitDecision) -> str:
        """
        Perform a requested position exit and return the close-action identifier.

        Parameters:
            decision: Exit decision containing the symbol and whether an exit is required.

        Returns:
            No-op, blocked, broker-provided, or fallback identifier for the close action.
        """
        ...


class OrderOutcomeReader(Protocol):
    def get_order_outcome(
        self, *, order_id: str, intent: ExecutionIntent
    ) -> ExecutionOutcome:
        """
        Fetch the latest execution outcome for a previously submitted order.

        Parameters:
            order_id: Broker-assigned identifier for the order to refresh.
            intent: Original execution intent used as lookup context.

        Returns:
            ExecutionOutcome: The canonical execution outcome record for the given order and intent.
        """
        ...


@dataclass(slots=True)
class _ReadOnlyOrderOutcomeReader:
    _get_order_outcome: Callable[..., ExecutionOutcome]

    def get_order_outcome(
        self, *, order_id: str, intent: ExecutionIntent
    ) -> ExecutionOutcome:
        """
        Fetches the latest execution outcome for the specified order and intent.
        
        Parameters:
            order_id (str): Broker order identifier to refresh.
            intent (ExecutionIntent): The original execution intent associated with the order.
        
        Returns:
            ExecutionOutcome: The persisted or refreshed execution outcome for the specified order.
        """
        return self._get_order_outcome(order_id=order_id, intent=intent)


@dataclass(slots=True)
class PaperBrokerAdapter:
    db: TradingDatabase
    settings: Settings
    backend_name: str = "paper"
    _broker: PaperBroker = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._broker = PaperBroker(self.db, self.settings)

    def place_order(self, intent: ExecutionIntent) -> ExecutionOutcome:
        """
        Submit the given execution intent to the paper broker after tagging it with this adapter and the paper execution backend.
        
        Parameters:
            intent (ExecutionIntent): The execution intent to place; a copy will be created with `adapter_name` set to this adapter's backend name and `execution_backend` set to "paper" before submission.
        
        Returns:
            ExecutionOutcome: The recorded outcome of the placed order.
        """
        return self._broker.place_order(
            intent.model_copy(
                update={
                    "adapter_name": self.backend_name,
                    "execution_backend": "paper",
                }
            )
        )

    def get_order_outcome(
        self, *, order_id: str, intent: ExecutionIntent
    ) -> ExecutionOutcome:
        """
        Refreshes and returns the persisted ExecutionOutcome for a paper order after validating the stored execution record matches the provided order id.
        
        Parameters:
            order_id (str): The broker order identifier to match against the stored execution record.
            intent (ExecutionIntent): The execution intent whose intent_id is used to locate the persisted execution record.
        
        Returns:
            ExecutionOutcome: The outcome reconstructed from the persisted outcome payload.
        
        Raises:
            RuntimeError: If there is no execution record matching the intent and order_id, or if the persisted outcome payload is not a dictionary.
        """
        record = self.db.get_execution_record(intent.intent_id)
        if record is None or record.get("order_id") != order_id:
            raise RuntimeError("Paper order refresh has no matching execution record.")
        outcome_payload = record.get("outcome")
        if not isinstance(outcome_payload, dict):
            raise RuntimeError("Paper order refresh has no persisted outcome payload.")
        return ExecutionOutcome.model_validate(outcome_payload)

    def submit(self, decision: ExecutionDecision) -> str:
        """
        Submit an execution decision to the configured broker.
        
        Parameters:
            decision (ExecutionDecision): The execution decision describing the action to perform.
        
        Returns:
            str: Broker-provided identifier for the submitted execution (e.g., an order id or a unique token).
        """
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
        """
        Simulates placing an order using deterministic market-friction rules and returns the resulting execution outcome.
        
        The method either:
        - triggers a deterministic rejection hook (when the intent is approved and not a "hold") and returns an outcome with status `"rejected"` and `rejection_reason` set to `"simulated_rejection_hook"`, or
        - computes a deterministic fill ratio and simulated execution price, submits a modified intent to the underlying paper broker, and returns the broker outcome augmented with `simulated_metadata`. If the broker reports `"filled"` but the simulated fill ratio is less than 1.0, the returned outcome is converted to `"partially_filled"`.
        
        Parameters:
            intent (ExecutionIntent): The execution intent to simulate; approval state, side, quantity/notional, and reference_price influence rejection gating and simulated fill behavior.
        
        Returns:
            ExecutionOutcome: The execution outcome representing the simulated submission, including `simulated_metadata` describing the deterministic simulation parameters and, when applicable, `rejection_reason` or a `"partially_filled"` status.
        """
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
            self._fill_ratio(intent)
            if intent.approved and intent.side != "hold"
            else 1.0
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

    def get_order_outcome(
        self, *, order_id: str, intent: ExecutionIntent
    ) -> ExecutionOutcome:
        """
        Refresh an execution outcome by loading and validating the persisted execution record for the given intent.
        
        Loads the execution record for intent.intent_id from the trading database and returns an ExecutionOutcome built from the stored outcome payload.
        
        Returns:
            ExecutionOutcome: The outcome reconstructed from the persisted outcome payload.
        
        Raises:
            RuntimeError: If no execution record exists for the intent or the record's order_id does not match `order_id`.
            RuntimeError: If the persisted outcome payload is missing or not a dictionary.
        """
        record = self.db.get_execution_record(intent.intent_id)
        if record is None or record.get("order_id") != order_id:
            raise RuntimeError(
                "Simulated-real order refresh has no matching execution record."
            )
        outcome_payload = record.get("outcome")
        if not isinstance(outcome_payload, dict):
            raise RuntimeError(
                "Simulated-real order refresh has no persisted outcome payload."
            )
        return ExecutionOutcome.model_validate(outcome_payload)

    def cancel_order(self, order_id: str) -> bool:
        """
        Check whether an open order with the given order_id exists.
        
        Parameters:
            order_id (str): Broker order identifier to search for.
        
        Returns:
            `True` if an open order with `order_id` exists, `False` otherwise.
        """
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
    """
    Check whether the configured Alpaca base URL targets the Alpaca paper endpoint.

    Parameters:
        settings (Settings): Application settings containing `alpaca_base_url`.

    Returns:
        True if the `alpaca_base_url` contains the Alpaca paper endpoint host, False otherwise.
    """
    parsed = urlparse(settings.alpaca_base_url)
    return parsed.hostname == ALPACA_PAPER_ENDPOINT_HOST


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
            "client_order_id": _alpaca_client_order_id(intent.intent_id),
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
        filled_quantity = _coerce_float(getattr(order, "filled_qty", 0.0))
        average_fill_price = _coerce_float(
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


def _adapter_for_backend(*, db: TradingDatabase, settings: Settings) -> BrokerAdapter:
    """
    Selects and constructs the BrokerAdapter implementation corresponding to the configured execution backend.
    
    Parameters:
        db (TradingDatabase): Database used by the adapter for persistence and lookups.
        settings (Settings): Runtime settings containing `execution_backend` and related flags.
    
    Returns:
        BrokerAdapter: An adapter instance for the configured backend (`paper`, `simulated_real`, or `alpaca_paper`).
    
    Raises:
        RuntimeError: If `execution_backend` is `"live"` but `live_execution_enabled` is false.
        RuntimeError: If `execution_backend` is `"live"` and no live adapter has been implemented.
        RuntimeError: If `execution_backend` has an unsupported value.
    """
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


def get_broker_adapter(*, db: TradingDatabase, settings: Settings) -> BrokerAdapter:
    """
    Selects and returns the BrokerAdapter implementation appropriate for the configured execution backend.
    
    Determines the adapter from `settings.execution_backend` and constructs it using `db` and `settings`. If the global execution kill switch is enabled, this function raises an error to prevent any adapter that can submit orders from being created.
    
    Parameters:
        db: TradingDatabase used by the adapter for persistence and state lookups.
        settings: Settings that determine which execution backend to use and configure the adapter.
    
    Returns:
        A BrokerAdapter instance matching the configured execution backend.
    
    Raises:
        RuntimeError: If `settings.execution_kill_switch_active` is true, preventing adapter creation.
    """
    if settings.execution_kill_switch_active:
        raise RuntimeError(
            "Execution kill switch is active. No broker adapter may submit orders."
        )
    return _adapter_for_backend(db=db, settings=settings)


def get_broker_order_reader(
    *, db: TradingDatabase, settings: Settings
) -> OrderOutcomeReader:
    """
    Create a read-only order outcome reader for the configured execution backend.
    
    This constructs the appropriate backend adapter from the provided database and settings,
    then returns a wrapper that exposes only `get_order_outcome`, preventing access to mutating
    adapter methods.
    
    Returns:
        OrderOutcomeReader: An object that exposes `get_order_outcome(order_id, intent)` for the selected backend.
    """

    adapter = _adapter_for_backend(db=db, settings=settings)
    return _ReadOnlyOrderOutcomeReader(adapter.get_order_outcome)


def _healthcheck_payload(settings: Settings) -> dict[str, object]:
    """
    Builds a broker healthcheck payload reflecting the configured execution backend and current settings.
    
    Parameters:
        settings (Settings): Application settings used to determine execution backend, kill switch state, Alpaca configuration, and related flags.
    
    Returns:
        dict[str, object]: A JSON-serializable dictionary representing the BrokerHealthcheck payload describing adapter name, execution backend, readiness flags, and a human-readable message.
    """
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
    """
    Produce a runtime status payload describing the configured broker backend, high-level readiness, and related Alpaca configuration flags.
    
    Parameters:
        settings (Settings): Application settings that determine execution backend, Alpaca configuration, kill switch, and related flags.
    
    Returns:
        dict[str, object]: A JSON-serializable dictionary containing runtime fields including:
          - "backend"/"adapter_name"/"execution_mode": configured execution backend identifier.
          - "simulated": `True` when using the simulated-real scaffold.
          - "live": `True` when a live backend was requested.
          - "external_paper": `True` when configured to use Alpaca paper.
          - Alpaca configuration flags: "alpaca_paper_trading_enabled", "alpaca_paper_endpoint", "alpaca_data_feed", "alpaca_credentials_configured".
          - "live_execution_enabled": whether live execution is permitted by settings.
          - "kill_switch_active": whether the execution kill switch is active.
          - "state": a short state token (e.g., "blocked", "paper", "simulated", "alpaca_paper_ready", "pending_live_adapter").
          - "message": a human-readable status message.
          - "live_requested": mirror of the requested live flag.
          - "live_ready": always `False` (no live adapter implemented).
          - "healthcheck": a broker healthcheck payload produced by _healthcheck_payload(settings).
    """
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
        message = str(
            healthcheck.get("message", "Alpaca paper adapter status unknown.")
        )
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
