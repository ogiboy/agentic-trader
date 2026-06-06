from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Protocol

from agentic_trader.ui_text import (
    MESSAGE_GROSS_EXPOSURE_ABOVE_EQUITY,
    MESSAGE_LARGEST_POSITION_ABOVE_EQUITY,
    MESSAGE_OPEN_POSITION_COUNT_ELEVATED,
    MESSAGE_PORTFOLIO_CONCENTRATION_HHI,
)
from agentic_trader.cli_modules.common import open_db
from agentic_trader.config import Settings
from agentic_trader.diagnostics import v1_readiness_payload
from agentic_trader.engine.broker import broker_runtime_payload, get_broker_adapter
from agentic_trader.engine.broker_contracts import BrokerAdapter
from agentic_trader.finance.strategy_catalog import (
    finance_reconciliation_contract_payload,
)
from agentic_trader.json_utils import object_mapping
from agentic_trader.schemas import (
    AccountMark,
    DailyRiskReport,
    InvestmentPreferences,
    PortfolioSnapshot,
    PositionPlanSnapshot,
    PositionSnapshot,
)
from agentic_trader.storage.db import TradingDatabase


class OpenDbProvider(Protocol):
    def __call__(self, settings: Settings, *, read_only: bool) -> TradingDatabase: ...


class BrokerAdapterProvider(Protocol):
    def __call__(self, *, db: TradingDatabase, settings: Settings) -> BrokerAdapter: ...


def portfolio_payload(
    settings: Settings,
    *,
    open_db_provider: OpenDbProvider = open_db,
    broker_adapter_provider: BrokerAdapterProvider = get_broker_adapter,
) -> dict[str, object]:
    source = "unavailable"
    try:
        db = open_db_provider(settings, read_only=True)
        try:
            if settings.execution_backend == "alpaca_paper":
                broker = broker_adapter_provider(db=db, settings=settings)
                snapshot = broker.get_account_state()
                positions = broker.get_positions()
                source = "broker_adapter"
            else:
                snapshot = db.get_account_snapshot()
                positions = db.list_positions()
                source = "runtime_database"
            latest_marks = db.list_account_marks(limit=1)
        finally:
            db.close()
        available = True
        error = None
    except Exception as exc:
        snapshot = PortfolioSnapshot(
            cash=0.0,
            market_value=0.0,
            equity=0.0,
            realized_pnl=0.0,
            unrealized_pnl=0.0,
            open_positions=0,
        )
        positions: list[PositionSnapshot] = []
        latest_marks: list[AccountMark] = []
        available = False
        error = str(exc)
    currency = primary_account_currency(settings, open_db_provider=open_db_provider)
    latest_mark = latest_marks[0].model_dump(mode="json") if latest_marks else None
    return {
        "available": available,
        "error": error,
        "source": source if available else "unavailable",
        "snapshot": snapshot.model_dump(mode="json"),
        "positions": [position.model_dump(mode="json") for position in positions],
        "accounting": {
            "currency": currency,
            "mark_created_at": latest_mark["created_at"] if latest_mark else None,
            "mark_source": latest_mark["source"] if latest_mark else None,
            "mark_note": latest_mark["note"] if latest_mark else None,
            "mark_status": "marked" if latest_mark else "mark_time_unavailable",
        },
    }


def position_plan_coverage_payload(
    settings: Settings,
    *,
    open_db_provider: OpenDbProvider = open_db,
    broker_adapter_provider: BrokerAdapterProvider = get_broker_adapter,
) -> dict[str, object]:
    source = "unavailable"
    try:
        db = open_db_provider(settings, read_only=True)
        try:
            if settings.execution_backend == "alpaca_paper":
                positions = broker_adapter_provider(
                    db=db, settings=settings
                ).get_positions()
                source = "broker_adapter"
            else:
                positions = db.list_positions()
                source = "runtime_database"
            plans = db.list_position_plans()
        finally:
            db.close()
        available = True
        error = None
    except (
        Exception
    ) as exc:  # noqa: BLE001 - observer payload should degrade when DB reads fail
        positions: list[PositionSnapshot] = []
        plans: list[PositionPlanSnapshot] = []
        available = False
        error = str(exc)

    open_symbols = sorted(
        position.symbol for position in positions if position.quantity != 0
    )
    open_symbol_set = set(open_symbols)
    planned_symbol_set = {plan.symbol for plan in plans}
    planned_open_symbols = sorted(open_symbol_set & planned_symbol_set)
    missing_symbols = sorted(open_symbol_set - planned_symbol_set)
    extra_plan_symbols = sorted(planned_symbol_set - open_symbol_set)
    coverage_ratio = (
        len(planned_open_symbols) / len(open_symbols) if open_symbols else 1.0
    )
    return {
        "available": available,
        "error": error,
        "source": source if available else "unavailable",
        "open_symbols": open_symbols,
        "planned_symbols": planned_open_symbols,
        "missing_symbols": missing_symbols,
        "extra_plan_symbols": extra_plan_symbols,
        "coverage_ratio": round(coverage_ratio, 4),
    }


def primary_account_currency(
    settings: Settings,
    *,
    open_db_provider: OpenDbProvider = open_db,
) -> str:
    try:
        db = open_db_provider(settings, read_only=True)
        try:
            preferences = db.load_preferences()
        finally:
            db.close()
    except Exception:
        preferences = InvestmentPreferences()
    return (preferences.currencies[0] if preferences.currencies else "USD").upper()


def execution_cost_model(settings: Settings) -> dict[str, object]:
    if settings.execution_backend == "simulated_real":
        return {
            "fees": "not modeled",
            "slippage_bps": settings.simulated_slippage_bps,
            "spread_bps": settings.simulated_spread_bps,
            "latency_ms": settings.simulated_latency_ms,
            "partial_fill_probability": settings.simulated_partial_fill_probability,
            "rejection_probability": settings.simulated_order_rejection_probability,
        }
    if settings.execution_backend == "alpaca_paper":
        return {
            "fees": "reported by external paper broker when available",
            "slippage_bps": None,
            "spread_bps": None,
            "latency_ms": None,
            "partial_fill_probability": None,
            "rejection_probability": None,
        }
    return {
        "fees": "not modeled",
        "slippage_bps": 0.0,
        "spread_bps": 0.0,
        "latency_ms": 0,
        "partial_fill_probability": 0.0,
        "rejection_probability": 0.0,
    }


def risk_report_from_portfolio(
    *,
    settings: Settings,
    snapshot: PortfolioSnapshot,
    positions: list[PositionSnapshot],
    report_date: str | None = None,
) -> DailyRiskReport:
    resolved_date = report_date or datetime.now(timezone.utc).date().isoformat()
    gross_exposure = sum(abs(position.market_value) for position in positions)
    largest_position = max(
        (abs(position.market_value) for position in positions), default=0.0
    )
    top_positions = sorted(
        positions, key=lambda position: abs(position.market_value), reverse=True
    )
    equity = snapshot.equity if snapshot.equity != 0 else 1.0
    portfolio_hhi = (
        sum(
            (abs(position.market_value) / gross_exposure) ** 2 for position in positions
        )
        if gross_exposure > 0
        else 0.0
    )

    warnings: list[str] = []
    if snapshot.open_positions >= settings.max_open_positions:
        warnings.append(MESSAGE_OPEN_POSITION_COUNT_ELEVATED)
    if gross_exposure / equity > settings.max_gross_exposure_pct:
        warnings.append(
            MESSAGE_GROSS_EXPOSURE_ABOVE_EQUITY.format(
                limit=f"{settings.max_gross_exposure_pct:.0%}"
            )
        )
    if largest_position / equity > settings.max_position_pct:
        warnings.append(
            MESSAGE_LARGEST_POSITION_ABOVE_EQUITY.format(
                limit=f"{settings.max_position_pct:.0%}"
            )
        )
    if portfolio_hhi > 0.25:
        warnings.append(
            MESSAGE_PORTFOLIO_CONCENTRATION_HHI.format(score=portfolio_hhi)
        )

    return DailyRiskReport(
        report_date=resolved_date,
        generated_at=datetime.now(timezone.utc).isoformat(),
        cash=snapshot.cash,
        market_value=snapshot.market_value,
        equity=snapshot.equity,
        realized_pnl=snapshot.realized_pnl,
        unrealized_pnl=snapshot.unrealized_pnl,
        open_positions=snapshot.open_positions,
        fills_today=0,
        marks_recorded=0,
        daily_realized_pnl=0.0,
        gross_exposure_pct=gross_exposure / equity,
        largest_position_pct=largest_position / equity,
        portfolio_hhi=portfolio_hhi,
        top_position_symbols=[position.symbol for position in top_positions[:5]],
        drawdown_from_peak_pct=0.0,
        warnings=warnings,
    )


def risk_report_payload(
    settings: Settings,
    *,
    report_date: str | None = None,
    open_db_provider: OpenDbProvider = open_db,
    broker_adapter_provider: BrokerAdapterProvider = get_broker_adapter,
) -> dict[str, object]:
    source = "unavailable"
    try:
        db = open_db_provider(settings, read_only=True)
        try:
            if settings.execution_backend == "alpaca_paper":
                broker = broker_adapter_provider(db=db, settings=settings)
                report = risk_report_from_portfolio(
                    settings=settings,
                    snapshot=broker.get_account_state(),
                    positions=broker.get_positions(),
                    report_date=report_date,
                )
                source = "broker_adapter"
            else:
                report = db.build_daily_risk_report(report_date=report_date)
                source = "runtime_database"
        finally:
            db.close()
        available = True
        error = None
    except Exception as exc:
        report = None
        available = False
        error = str(exc)
    return {
        "available": available,
        "error": error,
        "source": source if available else "unavailable",
        "report": report.model_dump(mode="json") if report is not None else None,
    }


def broker_payload(settings: Settings) -> dict[str, object]:
    return broker_runtime_payload(settings)


def finance_check(
    name: str, passed: bool, details: str, *, blocking: bool = True
) -> dict[str, object]:
    return {
        "name": name,
        "passed": passed,
        "details": details,
        "blocking": blocking,
    }


def position_plan_coverage_details(payload: Mapping[str, object]) -> str:
    if not bool(payload.get("available")):
        return str(payload.get("error") or "position plan coverage unavailable")
    open_symbols = payload.get("open_symbols")
    missing_symbols = payload.get("missing_symbols")
    planned_symbols = payload.get("planned_symbols")
    return (
        f"open={open_symbols if isinstance(open_symbols, list) else []} "
        f"planned={planned_symbols if isinstance(planned_symbols, list) else []} "
        f"missing={missing_symbols if isinstance(missing_symbols, list) else []}"
    )


def finance_ops_payload(
    settings: Settings,
    *,
    open_db_provider: OpenDbProvider = open_db,
    broker_adapter_provider: BrokerAdapterProvider = get_broker_adapter,
) -> dict[str, object]:
    broker = broker_payload(settings)
    portfolio = portfolio_payload(
        settings,
        open_db_provider=open_db_provider,
        broker_adapter_provider=broker_adapter_provider,
    )
    position_plan_coverage = position_plan_coverage_payload(
        settings,
        open_db_provider=open_db_provider,
        broker_adapter_provider=broker_adapter_provider,
    )
    risk_report = risk_report_payload(
        settings,
        open_db_provider=open_db_provider,
        broker_adapter_provider=broker_adapter_provider,
    )
    readiness = v1_readiness_payload(settings, check_provider=False)
    reconciliation = finance_reconciliation_contract_payload()
    checks = finance_ops_checks(
        settings=settings,
        broker=broker,
        portfolio=portfolio,
        position_plan_coverage=position_plan_coverage,
        risk_report=risk_report,
        readiness=readiness,
    )
    blocking_passed = finance_ops_blocking_passed(checks)
    return {
        "ready": blocking_passed,
        "mode": settings.runtime_mode,
        "backend": settings.execution_backend,
        "checks": checks,
        "broker": broker,
        "portfolio": portfolio,
        "positionPlanCoverage": position_plan_coverage,
        "riskReport": risk_report,
        "paperEvidence": readiness.get("paper_evidence"),
        "reconciliation": reconciliation,
        "accounting": finance_ops_accounting(
            settings=settings,
            portfolio=portfolio,
            reconciliation=reconciliation,
            open_db_provider=open_db_provider,
        ),
        "summary": finance_ops_summary(blocking_passed),
    }


def finance_ops_checks(
    *,
    settings: Settings,
    broker: Mapping[str, object],
    portfolio: Mapping[str, object],
    position_plan_coverage: Mapping[str, object],
    risk_report: Mapping[str, object],
    readiness: Mapping[str, object],
) -> list[dict[str, object]]:
    snapshot = portfolio.get("snapshot")
    snapshot_mapping = object_mapping(snapshot)
    return [
        finance_check(
            "paper_or_external_paper_only",
            settings.execution_backend in {"paper", "alpaca_paper"}
            and not settings.live_execution_enabled,
            f"backend={settings.execution_backend} live_execution_enabled={settings.live_execution_enabled}",
        ),
        finance_check(
            "broker_health_visible",
            isinstance(broker.get("healthcheck"), dict),
            str(broker.get("message", "")),
        ),
        finance_check(
            "account_snapshot_visible",
            bool(portfolio.get("available")) and bool(snapshot_mapping),
            str(portfolio.get("error") or "account snapshot available"),
        ),
        finance_check(
            "pnl_and_exposure_fields_visible",
            finance_snapshot_fields_visible(snapshot_mapping),
            "cash/equity/PnL/position fields are present on the portfolio snapshot.",
        ),
        finance_check(
            "open_position_exit_plans_visible",
            bool(position_plan_coverage.get("available"))
            and not bool(position_plan_coverage.get("missing_symbols")),
            position_plan_coverage_details(position_plan_coverage),
        ),
        finance_check(
            "risk_report_visible",
            bool(risk_report.get("available"))
            and risk_report.get("report") is not None,
            str(risk_report.get("error") or "daily risk report available"),
            blocking=False,
        ),
        finance_check(
            "paper_evidence_visible",
            isinstance(readiness.get("paper_evidence"), dict),
            "v1-readiness exposes source attribution, context-pack, review artifact, and no-live evidence.",
        ),
    ]


def finance_ops_blocking_passed(checks: list[dict[str, object]]) -> bool:
    return all(
        bool(check["passed"]) for check in checks if bool(check.get("blocking", True))
    )


def finance_ops_accounting(
    *,
    settings: Settings,
    portfolio: Mapping[str, object],
    reconciliation: Mapping[str, object],
    open_db_provider: OpenDbProvider,
) -> dict[str, object]:
    accounting = object_mapping(portfolio.get("accounting"))
    return {
        "currency": accounting.get(
            "currency",
            primary_account_currency(
                settings,
                open_db_provider=open_db_provider,
            ),
        ),
        "mark_created_at": accounting.get("mark_created_at"),
        "mark_source": accounting.get("mark_source"),
        "mark_note": accounting.get("mark_note"),
        "mark_status": accounting.get("mark_status", "mark_time_unavailable"),
        "cost_model": execution_cost_model(settings),
        "ledger_categories": reconciliation["ledger_categories"],
        "rejection_evidence": (
            "Execution rejections are surfaced from execution_outcomes, "
            "trade context, broker-status, and run review payloads."
        ),
    }


def finance_ops_summary(ready: bool) -> str:
    if ready:
        return (
            "Finance operations checks have the broker/account/evidence truth "
            "needed for local paper review."
        )
    return "Finance operations checks are missing broker/account/evidence truth."


def finance_snapshot_fields_visible(snapshot: object) -> bool:
    snapshot_mapping = object_mapping(snapshot)
    if not snapshot_mapping:
        return False
    required_fields = {
        "cash",
        "equity",
        "realized_pnl",
        "unrealized_pnl",
        "open_positions",
    }
    return required_fields.issubset(snapshot_mapping)
