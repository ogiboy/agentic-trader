from __future__ import annotations

import json
from typing import Any

import pandas as pd

from agentic_trader.market.features import build_snapshot
from scripts.qa.smoke_qa_modules.common import artifact_path, write_artifact
from scripts.qa.smoke_qa_modules.models import CheckResult, SmokeContext


def run_market_context_edge_case_check(context: SmokeContext) -> CheckResult:
    name = "market_context_edge_cases"
    artifact = artifact_path(context, name)
    issues, observations = _market_context_edge_case_results()

    write_artifact(
        artifact,
        json.dumps(
            {
                "issues": issues,
                "observations": observations,
            },
            indent=2,
            default=str,
        ),
    )
    return CheckResult(
        name=name,
        passed=not issues,
        details="context_edge_cases_ok" if not issues else "; ".join(issues),
        artifact=str(artifact),
    )


def _market_context_edge_case_results() -> tuple[list[str], dict[str, object]]:
    issues: list[str] = []
    observations: dict[str, object] = {}
    try:
        _check_partial_daily_window(issues, observations)
        intraday_frame = _intraday_edge_case_frame()
        _check_intraday_fail_closed(intraday_frame, issues, observations)
        _check_training_replay_undercoverage(intraday_frame, issues, observations)
        _check_higher_timeframe_fallbacks(issues, observations)
    except Exception as exc:
        issues.append(f"exception={exc}")
    return issues, observations


def _qa_ohlcv_frame(periods: int, *, index: Any | None = None) -> Any:
    return pd.DataFrame(
        {
            "open": [100 + i for i in range(periods)],
            "high": [101 + i for i in range(periods)],
            "low": [99 + i for i in range(periods)],
            "close": [100 + i for i in range(periods)],
            "volume": [1_000 + (i * 10) for i in range(periods)],
        },
        index=index,
    )


def _intraday_edge_case_frame() -> Any:
    return _qa_ohlcv_frame(
        120, index=pd.date_range("2025-01-01 09:30", periods=120, freq="h")
    )


def _pack_payload(pack: Any | None) -> object:
    return pack.model_dump(mode="json") if pack is not None else None


def _require_context_flag(
    pack: Any | None,
    flag: str,
    issues: list[str],
    *,
    missing_pack: str,
    missing_flag: str,
) -> None:
    if pack is None:
        issues.append(missing_pack)
    elif flag not in pack.data_quality_flags:
        issues.append(missing_flag)


def _check_partial_daily_window(
    issues: list[str], observations: dict[str, object]
) -> None:
    partial_frame = _qa_ohlcv_frame(
        80, index=pd.date_range("2025-01-01", periods=80, freq="B")
    )
    partial_snapshot = build_snapshot(
        partial_frame, symbol="PARTIAL", interval="1d", lookback="180d"
    )
    partial_pack = partial_snapshot.context_pack
    observations["partial_daily"] = _pack_payload(partial_pack)
    _require_context_flag(
        partial_pack,
        "partial_lookback_coverage",
        issues,
        missing_pack="partial daily context pack missing",
        missing_flag="partial daily window did not mark partial_lookback_coverage",
    )


def _check_intraday_fail_closed(
    intraday_frame: Any, issues: list[str], observations: dict[str, object]
) -> None:
    try:
        build_snapshot(
            intraday_frame, symbol="INTRADAY", interval="1h", lookback="180d"
        )
    except ValueError as exc:
        observations["intraday_operation_block"] = str(exc)
        if "coverage is too thin" not in str(exc):
            issues.append("intraday operation block did not explain thin coverage")
        return
    issues.append("intraday provider-limit window did not fail closed")


def _check_training_replay_undercoverage(
    intraday_frame: Any, issues: list[str], observations: dict[str, object]
) -> None:
    replay_snapshot = build_snapshot(
        intraday_frame,
        symbol="TRAIN",
        interval="1h",
        lookback="180d",
        enforce_lookback_coverage=False,
    )
    replay_pack = replay_snapshot.context_pack
    observations["intraday_training"] = _pack_payload(replay_pack)
    _require_context_flag(
        replay_pack,
        "low_lookback_coverage",
        issues,
        missing_pack="training replay context pack missing",
        missing_flag="training replay did not preserve low_lookback_coverage",
    )


def _check_higher_timeframe_fallbacks(
    issues: list[str], observations: dict[str, object]
) -> None:
    range_pack = build_snapshot(
        _qa_ohlcv_frame(80), symbol="RANGE", interval="1d", lookback="90d"
    ).context_pack
    observations["non_datetime_index"] = _pack_payload(range_pack)
    _require_context_flag(
        range_pack,
        "higher_timeframe_fallback",
        issues,
        missing_pack="non-datetime context pack missing",
        missing_flag="non-datetime index did not mark higher_timeframe_fallback",
    )

    short_htf_pack = build_snapshot(
        _qa_ohlcv_frame(80, index=pd.date_range("2025-01-01", periods=80, freq="B")),
        symbol="SHORTHTF",
        interval="1d",
        lookback="90d",
    ).context_pack
    observations["short_higher_timeframe"] = _pack_payload(short_htf_pack)
    _require_context_flag(
        short_htf_pack,
        "higher_timeframe_fallback",
        issues,
        missing_pack="short higher-timeframe context pack missing",
        missing_flag="short higher-timeframe window did not mark higher_timeframe_fallback",
    )
