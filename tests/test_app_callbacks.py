"""Tests for agentic_trader.cli_modules.app_callbacks.

Each public factory function should return a callable that correctly delegates
to the corresponding method on the provided namespace.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, call

import pytest

from agentic_trader.cli_modules.app_callbacks import (
    apply_preference_update_callback,
    chat_with_persona_callback,
    interpret_operator_instruction_callback,
    memory_explorer_callback,
    refresh_trade_proposal_order_callback,
    retrieval_inspection_callback,
    run_ablation_callback,
    run_comparison_callback,
    run_replay_payload,
    run_service_callback,
    run_walk_forward_callback,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_namespace(**attrs: object) -> SimpleNamespace:
    """Create a SimpleNamespace with the given attributes."""
    return SimpleNamespace(**attrs)


# ---------------------------------------------------------------------------
# refresh_trade_proposal_order_callback
# ---------------------------------------------------------------------------


def test_refresh_trade_proposal_order_callback_returns_callable() -> None:
    ns = _make_namespace(refresh_trade_proposal_order=MagicMock())
    callback = refresh_trade_proposal_order_callback(ns)
    assert callable(callback)


def test_refresh_trade_proposal_order_callback_delegates_to_namespace() -> None:
    sentinel = object()
    ns = _make_namespace(refresh_trade_proposal_order=MagicMock(return_value=sentinel))
    db = MagicMock()
    settings = MagicMock()

    callback = refresh_trade_proposal_order_callback(ns)
    result = callback(db=db, settings=settings, proposal_id="p-1", review_notes="ok")

    ns.refresh_trade_proposal_order.assert_called_once_with(
        db=db,
        settings=settings,
        proposal_id="p-1",
        review_notes="ok",
    )
    assert result is sentinel


def test_refresh_trade_proposal_order_callback_propagates_exception() -> None:
    ns = _make_namespace(
        refresh_trade_proposal_order=MagicMock(side_effect=RuntimeError("boom"))
    )
    callback = refresh_trade_proposal_order_callback(ns)

    with pytest.raises(RuntimeError, match="boom"):
        callback(db=MagicMock(), settings=MagicMock(), proposal_id="p-x", review_notes="")


# ---------------------------------------------------------------------------
# chat_with_persona_callback
# ---------------------------------------------------------------------------


def test_chat_with_persona_callback_returns_callable() -> None:
    ns = _make_namespace(chat_with_persona=MagicMock())
    callback = chat_with_persona_callback(ns)
    assert callable(callback)


def test_chat_with_persona_callback_delegates_to_namespace() -> None:
    ns = _make_namespace(chat_with_persona=MagicMock(return_value="Hello!"))
    llm = MagicMock()
    db = MagicMock()
    settings = MagicMock()
    persona = MagicMock()

    callback = chat_with_persona_callback(ns)
    result = callback(
        llm=llm, db=db, settings=settings, persona=persona, user_message="Hi"
    )

    ns.chat_with_persona.assert_called_once_with(
        llm=llm, db=db, settings=settings, persona=persona, user_message="Hi"
    )
    assert result == "Hello!"


def test_chat_with_persona_callback_passes_empty_message() -> None:
    ns = _make_namespace(chat_with_persona=MagicMock(return_value=""))
    callback = chat_with_persona_callback(ns)
    result = callback(
        llm=MagicMock(), db=MagicMock(), settings=MagicMock(),
        persona=MagicMock(), user_message=""
    )
    ns.chat_with_persona.assert_called_once()
    assert result == ""


# ---------------------------------------------------------------------------
# interpret_operator_instruction_callback
# ---------------------------------------------------------------------------


def test_interpret_operator_instruction_callback_returns_callable() -> None:
    ns = _make_namespace(interpret_operator_instruction=MagicMock())
    callback = interpret_operator_instruction_callback(ns)
    assert callable(callback)


def test_interpret_operator_instruction_callback_delegates_to_namespace() -> None:
    instruction = MagicMock()
    ns = _make_namespace(
        interpret_operator_instruction=MagicMock(return_value=instruction)
    )
    llm = MagicMock()
    db = MagicMock()
    settings = MagicMock()

    callback = interpret_operator_instruction_callback(ns)
    result = callback(
        llm=llm,
        db=db,
        settings=settings,
        user_message="buy 10 AAPL",
        allow_fallback=True,
    )

    ns.interpret_operator_instruction.assert_called_once_with(
        llm=llm,
        db=db,
        settings=settings,
        user_message="buy 10 AAPL",
        allow_fallback=True,
    )
    assert result is instruction


def test_interpret_operator_instruction_callback_allow_fallback_false() -> None:
    ns = _make_namespace(interpret_operator_instruction=MagicMock(return_value=None))
    callback = interpret_operator_instruction_callback(ns)
    callback(
        llm=MagicMock(),
        db=MagicMock(),
        settings=MagicMock(),
        user_message="do something",
        allow_fallback=False,
    )
    _, kwargs = ns.interpret_operator_instruction.call_args
    assert kwargs["allow_fallback"] is False


# ---------------------------------------------------------------------------
# apply_preference_update_callback
# ---------------------------------------------------------------------------


def test_apply_preference_update_callback_returns_callable() -> None:
    ns = _make_namespace(apply_preference_update=MagicMock())
    callback = apply_preference_update_callback(ns)
    assert callable(callback)


def test_apply_preference_update_callback_delegates_to_namespace() -> None:
    prefs = MagicMock()
    ns = _make_namespace(apply_preference_update=MagicMock(return_value=prefs))
    db = MagicMock()
    update = MagicMock()

    callback = apply_preference_update_callback(ns)
    result = callback(db, update)

    ns.apply_preference_update.assert_called_once_with(db, update)
    assert result is prefs


def test_apply_preference_update_callback_propagates_exception() -> None:
    ns = _make_namespace(
        apply_preference_update=MagicMock(side_effect=ValueError("bad update"))
    )
    callback = apply_preference_update_callback(ns)
    with pytest.raises(ValueError, match="bad update"):
        callback(MagicMock(), MagicMock())


# ---------------------------------------------------------------------------
# memory_explorer_callback
# ---------------------------------------------------------------------------


def test_memory_explorer_callback_returns_callable() -> None:
    ns = _make_namespace(_open_db=MagicMock())
    # Need to patch the underlying impl to avoid real DB calls
    callback = memory_explorer_callback(ns)
    assert callable(callback)


def test_memory_explorer_callback_delegates_with_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {"runs": []}
    mock_impl = MagicMock(return_value=payload)
    monkeypatch.setattr(
        "agentic_trader.cli_modules.app_callbacks._memory_explorer_payload_impl",
        mock_impl,
    )
    open_db = MagicMock()
    ns = _make_namespace(_open_db=open_db)
    settings = MagicMock()

    callback = memory_explorer_callback(ns)
    result = callback(settings)

    mock_impl.assert_called_once_with(
        settings,
        open_db=open_db,
        symbol=None,
        interval=None,
        lookback="180d",
        limit=5,
        use_latest_run=False,
    )
    assert result is payload


def test_memory_explorer_callback_passes_symbol_and_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    mock_impl = MagicMock(return_value={})
    monkeypatch.setattr(
        "agentic_trader.cli_modules.app_callbacks._memory_explorer_payload_impl",
        mock_impl,
    )
    ns = _make_namespace(_open_db=MagicMock())
    settings = MagicMock()

    callback = memory_explorer_callback(ns)
    callback(settings, symbol="AAPL", interval="1h", lookback="30d", limit=10, use_latest_run=True)

    _, kwargs = mock_impl.call_args
    assert kwargs["symbol"] == "AAPL"
    assert kwargs["interval"] == "1h"
    assert kwargs["lookback"] == "30d"
    assert kwargs["limit"] == 10
    assert kwargs["use_latest_run"] is True


# ---------------------------------------------------------------------------
# retrieval_inspection_callback
# ---------------------------------------------------------------------------


def test_retrieval_inspection_callback_returns_callable() -> None:
    ns = _make_namespace(_open_db=MagicMock())
    callback = retrieval_inspection_callback(ns)
    assert callable(callback)


def test_retrieval_inspection_callback_delegates(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {"stages": []}
    mock_impl = MagicMock(return_value=payload)
    mock_run_record_impl = MagicMock(return_value={})
    monkeypatch.setattr(
        "agentic_trader.cli_modules.app_callbacks._retrieval_inspection_payload_impl",
        mock_impl,
    )
    monkeypatch.setattr(
        "agentic_trader.cli_modules.app_callbacks._run_record_payload_impl",
        mock_run_record_impl,
    )
    ns = _make_namespace(_open_db=MagicMock())
    settings = MagicMock()

    callback = retrieval_inspection_callback(ns)
    result = callback(settings)

    mock_impl.assert_called_once()
    assert result is payload


def test_retrieval_inspection_callback_with_run_id(monkeypatch: pytest.MonkeyPatch) -> None:
    mock_impl = MagicMock(return_value={})
    mock_run_record_impl = MagicMock(return_value={})
    monkeypatch.setattr(
        "agentic_trader.cli_modules.app_callbacks._retrieval_inspection_payload_impl",
        mock_impl,
    )
    monkeypatch.setattr(
        "agentic_trader.cli_modules.app_callbacks._run_record_payload_impl",
        mock_run_record_impl,
    )
    ns = _make_namespace(_open_db=MagicMock())
    callback = retrieval_inspection_callback(ns)
    callback(MagicMock(), run_id="run-42")

    mock_impl.assert_called_once()
    _, kwargs = mock_impl.call_args
    assert kwargs.get("run_id") == "run-42"


# ---------------------------------------------------------------------------
# run_comparison_callback
# ---------------------------------------------------------------------------


def test_run_comparison_callback_returns_callable() -> None:
    ns = _make_namespace(run_backtest_comparison=MagicMock())
    callback = run_comparison_callback(ns)
    assert callable(callback)


def test_run_comparison_callback_delegates_to_namespace() -> None:
    report = MagicMock()
    ns = _make_namespace(run_backtest_comparison=MagicMock(return_value=report))
    settings = MagicMock()

    callback = run_comparison_callback(ns)
    result = callback(
        settings=settings,
        symbol="BTC/USD",
        interval="1h",
        lookback="90d",
    )

    ns.run_backtest_comparison.assert_called_once_with(
        settings=settings,
        symbol="BTC/USD",
        interval="1h",
        lookback="90d",
        warmup_bars=120,
        allow_fallback=False,
        frame=None,
    )
    assert result is report


def test_run_comparison_callback_allows_custom_warmup_and_fallback() -> None:
    ns = _make_namespace(run_backtest_comparison=MagicMock(return_value=None))
    callback = run_comparison_callback(ns)
    callback(
        settings=MagicMock(),
        symbol="ETH/USD",
        interval="4h",
        lookback="30d",
        warmup_bars=60,
        allow_fallback=True,
    )
    _, kwargs = ns.run_backtest_comparison.call_args
    assert kwargs["warmup_bars"] == 60
    assert kwargs["allow_fallback"] is True


# ---------------------------------------------------------------------------
# run_ablation_callback
# ---------------------------------------------------------------------------


def test_run_ablation_callback_returns_callable() -> None:
    ns = _make_namespace(run_memory_ablation_backtest=MagicMock())
    callback = run_ablation_callback(ns)
    assert callable(callback)


def test_run_ablation_callback_delegates_to_namespace() -> None:
    report = MagicMock()
    ns = _make_namespace(run_memory_ablation_backtest=MagicMock(return_value=report))
    settings = MagicMock()

    callback = run_ablation_callback(ns)
    result = callback(
        settings=settings,
        symbol="AAPL",
        interval="1d",
        lookback="60d",
    )

    ns.run_memory_ablation_backtest.assert_called_once_with(
        settings=settings,
        symbol="AAPL",
        interval="1d",
        lookback="60d",
        warmup_bars=120,
        allow_fallback=False,
        frame=None,
    )
    assert result is report


def test_run_ablation_callback_passes_frame() -> None:
    import pandas as pd

    frame = pd.DataFrame()
    ns = _make_namespace(run_memory_ablation_backtest=MagicMock(return_value=None))
    callback = run_ablation_callback(ns)
    callback(
        settings=MagicMock(),
        symbol="MSFT",
        interval="1h",
        lookback="30d",
        frame=frame,
    )
    _, kwargs = ns.run_memory_ablation_backtest.call_args
    assert kwargs["frame"] is frame


# ---------------------------------------------------------------------------
# run_walk_forward_callback
# ---------------------------------------------------------------------------


def test_run_walk_forward_callback_returns_callable() -> None:
    ns = _make_namespace(run_walk_forward_backtest=MagicMock())
    callback = run_walk_forward_callback(ns)
    assert callable(callback)


def test_run_walk_forward_callback_delegates_to_namespace() -> None:
    report = MagicMock()
    ns = _make_namespace(run_walk_forward_backtest=MagicMock(return_value=report))
    settings = MagicMock()

    callback = run_walk_forward_callback(ns)
    result = callback(
        settings=settings,
        symbol="NVDA",
        interval="1h",
        lookback="180d",
    )

    ns.run_walk_forward_backtest.assert_called_once_with(
        settings=settings,
        symbol="NVDA",
        interval="1h",
        lookback="180d",
        warmup_bars=120,
        allow_fallback=False,
        memory_enabled=True,
        frame=None,
    )
    assert result is report


def test_run_walk_forward_callback_memory_disabled() -> None:
    ns = _make_namespace(run_walk_forward_backtest=MagicMock(return_value=None))
    callback = run_walk_forward_callback(ns)
    callback(
        settings=MagicMock(),
        symbol="TSLA",
        interval="1d",
        lookback="90d",
        memory_enabled=False,
    )
    _, kwargs = ns.run_walk_forward_backtest.call_args
    assert kwargs["memory_enabled"] is False


# ---------------------------------------------------------------------------
# run_service_callback
# ---------------------------------------------------------------------------


def test_run_service_callback_returns_callable() -> None:
    ns = _make_namespace(run_service=MagicMock())
    callback = run_service_callback(ns)
    assert callable(callback)


def test_run_service_callback_delegates_to_namespace() -> None:
    sentinel = object()
    ns = _make_namespace(run_service=MagicMock(return_value=sentinel))
    settings = MagicMock()

    callback = run_service_callback(ns)
    result = callback(
        settings=settings,
        symbols=["AAPL", "MSFT"],
        interval="1h",
        lookback="30d",
        poll_seconds=60,
        continuous=True,
        max_cycles=None,
    )

    ns.run_service.assert_called_once_with(
        settings=settings,
        symbols=["AAPL", "MSFT"],
        interval="1h",
        lookback="30d",
        poll_seconds=60,
        continuous=True,
        max_cycles=None,
    )
    assert result is sentinel


def test_run_service_callback_max_cycles_bounded() -> None:
    ns = _make_namespace(run_service=MagicMock(return_value=None))
    callback = run_service_callback(ns)
    callback(
        settings=MagicMock(),
        symbols=["BTC/USD"],
        interval="4h",
        lookback="7d",
        poll_seconds=300,
        continuous=False,
        max_cycles=5,
    )
    _, kwargs = ns.run_service.call_args
    assert kwargs["max_cycles"] == 5
    assert kwargs["continuous"] is False


# ---------------------------------------------------------------------------
# run_replay_payload (public function, not a factory)
# ---------------------------------------------------------------------------


def test_run_replay_payload_delegates(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {"replay": "data"}
    mock_impl = MagicMock(return_value=payload)
    mock_run_record_impl = MagicMock(return_value={})
    monkeypatch.setattr(
        "agentic_trader.cli_modules.app_callbacks._run_replay_payload_impl",
        mock_impl,
    )
    monkeypatch.setattr(
        "agentic_trader.cli_modules.app_callbacks._run_record_payload_impl",
        mock_run_record_impl,
    )
    ns = _make_namespace(_open_db=MagicMock())
    settings = MagicMock()

    result = run_replay_payload(ns, settings)

    mock_impl.assert_called_once()
    assert result is payload


def test_run_replay_payload_with_run_id(monkeypatch: pytest.MonkeyPatch) -> None:
    mock_impl = MagicMock(return_value={})
    mock_run_record_impl = MagicMock(return_value={})
    monkeypatch.setattr(
        "agentic_trader.cli_modules.app_callbacks._run_replay_payload_impl",
        mock_impl,
    )
    monkeypatch.setattr(
        "agentic_trader.cli_modules.app_callbacks._run_record_payload_impl",
        mock_run_record_impl,
    )
    ns = _make_namespace(_open_db=MagicMock())
    run_replay_payload(ns, MagicMock(), run_id="run-123")

    mock_impl.assert_called_once()
    _, kwargs = mock_impl.call_args
    assert kwargs.get("run_id") == "run-123"


# ---------------------------------------------------------------------------
# Namespace isolation: each callback closure captures its own namespace
# ---------------------------------------------------------------------------


def test_callback_closures_are_independent() -> None:
    """Callbacks created from different namespaces should not share state."""
    ns_a = _make_namespace(run_service=MagicMock(return_value="a"))
    ns_b = _make_namespace(run_service=MagicMock(return_value="b"))

    cb_a = run_service_callback(ns_a)
    cb_b = run_service_callback(ns_b)

    kwargs = dict(
        settings=MagicMock(),
        symbols=["X"],
        interval="1h",
        lookback="1d",
        poll_seconds=10,
        continuous=False,
        max_cycles=1,
    )

    assert cb_a(**kwargs) == "a"
    assert cb_b(**kwargs) == "b"
    ns_a.run_service.assert_called_once()
    ns_b.run_service.assert_called_once()