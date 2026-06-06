from __future__ import annotations

import pytest
from rich.console import Console

from agentic_trader.ui_text import (
    TITLE_DESK_ACCOUNTING_CONTEXT,
    TITLE_FINANCE_LEDGER_CATEGORIES,
    TITLE_FINANCE_OPERATIONS_CHECKS,
)
from agentic_trader.cli_modules import finance_rendering


def test_finance_table_helpers_render_checks_and_accounting() -> None:
    checks = [
        {
            "name": "broker_health_visible",
            "passed": True,
            "blocking": True,
            "details": "broker ready",
        }
    ]
    accounting = {
        "currency": "USD",
        "mark_created_at": "2026-06-02T12:00:00Z",
        "mark_source": "test",
        "mark_status": "marked",
        "cost_model": {"fees": "not modeled", "slippage_bps": 12.5},
        "rejection_evidence": "execution outcomes",
    }
    ledger_categories = [
        {"name": "cash", "v1_source": "portfolio", "purpose": "cash tracking"}
    ]
    console = Console(record=True, width=140)

    console.print(finance_rendering.finance_checks_table(checks))
    console.print(finance_rendering.finance_accounting_table(accounting))
    console.print(finance_rendering.finance_ledger_table(ledger_categories))
    output = console.export_text()

    assert TITLE_FINANCE_OPERATIONS_CHECKS in output
    assert "broker_health_visible" in output
    assert "pass" in output
    assert TITLE_DESK_ACCOUNTING_CONTEXT in output
    assert "12.5 bps" in output
    assert TITLE_FINANCE_LEDGER_CATEGORIES in output
    assert "cash tracking" in output
    assert finance_rendering.finance_ledger_table([]) is None


def test_finance_renderers_print_operator_panels(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    console = Console(record=True, width=140)
    monkeypatch.setattr(finance_rendering, "console", console)

    finance_rendering.render_finance_ops(
        {
            "ready": True,
            "summary": "Finance operations ready.",
            "checks": [
                {
                    "name": "paper_evidence_visible",
                    "passed": True,
                    "blocking": False,
                    "details": "evidence visible",
                }
            ],
            "accounting": {
                "currency": "USD",
                "cost_model": {"fees": "not modeled", "slippage_bps": None},
                "ledger_categories": [
                    {
                        "name": "orders",
                        "v1_source": "trade journal",
                        "purpose": "order accounting",
                    }
                ],
            },
        }
    )
    finance_rendering.render_position_plan_repair(
        {
            "applied": True,
            "summary": "Position plan repairs applied.",
            "repairs": [
                {
                    "symbol": "AAPL",
                    "status": "created",
                    "proposal_id": "proposal-1",
                    "entry_price": 190,
                    "stop_loss": 185.125,
                    "take_profit": None,
                    "reason": "missing plan",
                }
            ],
        }
    )
    output = console.export_text()

    assert "Finance operations ready." in output
    assert "paper_evidence_visible" in output
    assert "orders" in output
    assert "Position plan repairs applied." in output
    assert "AAPL" in output
    assert "190.0000" in output
    assert "185.1250" in output
    assert finance_rendering.format_optional_float(None) == "-"
