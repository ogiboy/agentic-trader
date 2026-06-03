from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from agentic_trader.finance.ideas import IdeaPresetName

StrategyStatus = Literal["implemented", "research_candidate", "v2_deferred"]
StrategyFamily = Literal[
    "momentum",
    "reversion",
    "breakout",
    "volatility",
    "confluence",
    "pairs",
    "regime",
]
ReadinessState = Literal["needs_evidence", "watch_only"]


@dataclass(frozen=True)
class StrategyProfile:
    """Operator-facing profile for a strategy family or candidate."""

    name: str
    family: StrategyFamily
    status: StrategyStatus
    summary: str
    idea_presets: tuple[IdeaPresetName, ...] = ()
    required_inputs: tuple[str, ...] = ()
    evidence_requirements: tuple[str, ...] = ()
    risk_controls: tuple[str, ...] = ()
    validation_checks: tuple[str, ...] = ()
    proposal_policy: str = (
        "research_only_until_manual_proposal_review_and_risk_gate_pass"
    )
    v1_path: str = "research_only"


@dataclass(frozen=True)
class FinanceLedgerCategory:
    """Read-only finance/accounting category expected in broker evidence."""

    name: str
    purpose: str
    v1_source: str
    expected_fields: tuple[str, ...] = field(default_factory=tuple)
    v2_extension: str | None = None


STRATEGY_PROFILES: tuple[StrategyProfile, ...] = (
    StrategyProfile(
        name="momentum-volume",
        family="momentum",
        status="implemented",
        summary="Relative-volume and trend-confirmed momentum scan for US equity watchlists.",
        idea_presets=("momentum",),
        required_inputs=(
            "last_price",
            "volume",
            "change_pct",
            "relative_volume",
            "rsi",
            "ema_9",
        ),
        evidence_requirements=(
            "fresh_news_or_disclosure_catalyst",
            "liquidity_and_spread_check",
            "provider_source_attribution",
        ),
        risk_controls=(
            "max_position_pct",
            "daily_loss_limit",
            "wide_spread_warning",
            "manual_proposal_approval",
        ),
        validation_checks=(
            "next_open_fill_assumption",
            "no_single_source_catalyst",
            "score_threshold_review",
        ),
        proposal_policy="buy/sell score can only become a pending proposal after evidence enrichment",
        v1_path="idea_scanner_to_manual_proposal",
    ),
    StrategyProfile(
        name="gap-reversion",
        family="reversion",
        status="implemented",
        summary="Gap-up and gap-down triage for reversal or short-bias watch decisions.",
        idea_presets=("gap-up", "gap-down"),
        required_inputs=(
            "last_price",
            "gap_pct",
            "change_pct",
            "relative_volume",
            "rsi",
            "sma_20",
        ),
        evidence_requirements=(
            "opening_catalyst",
            "fresh_primary_source",
            "spread_and_liquidity_check",
        ),
        risk_controls=(
            "stop_loss_required_for_proposal",
            "gap_continuation_warning",
            "manual_proposal_approval",
        ),
        validation_checks=(
            "session_open_timestamp",
            "no_stale_archive_source_for_event_trade",
            "intraday_slippage_assumption",
        ),
        proposal_policy="gap scans are watch/proposal candidates, never direct execution",
        v1_path="idea_scanner_to_manual_proposal",
    ),
    StrategyProfile(
        name="mean-reversion-rsi",
        family="reversion",
        status="implemented",
        summary="Oversold mean-reversion scan using RSI and moving-average distance.",
        idea_presets=("mean-reversion",),
        required_inputs=(
            "last_price",
            "volume",
            "relative_volume",
            "rsi",
            "sma_20",
            "sma_50",
        ),
        evidence_requirements=(
            "news_risk_absence_or_positive_resolution",
            "support_level_context",
            "liquidity_and_spread_check",
        ),
        risk_controls=(
            "invalidating_news_check",
            "support_break_stop",
            "manual_proposal_approval",
        ),
        validation_checks=(
            "falling_knife_review",
            "drawdown_stress_check",
            "lookback_coverage_check",
        ),
        proposal_policy="oversold score needs catalyst/risk review before any proposal",
        v1_path="idea_scanner_to_manual_proposal",
    ),
    StrategyProfile(
        name="vwap-breakout",
        family="breakout",
        status="implemented",
        summary="VWAP/EMA reclaim and breakout scan with volume confirmation.",
        idea_presets=("breakout",),
        required_inputs=("last_price", "relative_volume", "vwap", "ema_9", "sma_20"),
        evidence_requirements=(
            "fresh_catalyst_or_sector_strength",
            "volume_confirmation",
            "spread_and_slippage_assumption",
        ),
        risk_controls=(
            "failed_reclaim_stop",
            "position_size_cap",
            "manual_proposal_approval",
        ),
        validation_checks=(
            "no_precomputed_lookahead",
            "next_bar_fill_assumption",
            "false_breakout_review",
        ),
        proposal_policy="breakout score must be enriched before entering the queue",
        v1_path="idea_scanner_to_manual_proposal",
    ),
    StrategyProfile(
        name="volatile-watch",
        family="volatility",
        status="implemented",
        summary="High range and relative-volume triage for operator watchlists.",
        idea_presets=("volatile",),
        required_inputs=(
            "last_price",
            "range_pct",
            "change_pct",
            "relative_volume",
            "rsi",
        ),
        evidence_requirements=(
            "material_event_classification",
            "staleness_and_source_tier",
            "spread_and_liquidity_check",
        ),
        risk_controls=(
            "watch_only_default",
            "manual_thesis_required",
            "wide_spread_warning",
        ),
        validation_checks=("event_recency_check", "volatility_regime_review"),
        proposal_policy="volatility scans default to watch-only unless an operator writes a proposal thesis",
        v1_path="watchlist_only_by_default",
    ),
    StrategyProfile(
        name="opening-range-breakout",
        family="breakout",
        status="research_candidate",
        summary="Opening range breakout with volume confirmation and time-based exits.",
        required_inputs=("intraday_ohlcv", "regular_session_clock", "volume_average"),
        evidence_requirements=(
            "session_open_data_quality",
            "same_day_news_catalyst",
            "market_session_status",
        ),
        risk_controls=(
            "max_hold_bars",
            "close_by_time",
            "gap_and_spread_penalty",
        ),
        validation_checks=(
            "vectorized_precompute",
            "no_lookahead_assertion",
            "intraday_fill_policy_review",
        ),
        proposal_policy="research candidate until intraday QA and no-lookahead tests exist",
        v1_path="backtest_then_proposal_capability_review",
    ),
    StrategyProfile(
        name="vwap-reclaim-reversion",
        family="reversion",
        status="research_candidate",
        summary="VWAP reclaim/reversion family for intraday continuation or fade hypotheses.",
        required_inputs=("intraday_ohlcv", "vwap", "session_volume", "time_of_day"),
        evidence_requirements=(
            "catalyst_direction",
            "market_session_status",
            "spread_and_adv_check",
        ),
        risk_controls=("vwap_fail_stop", "close_by_time", "liquidity_penalty"),
        validation_checks=(
            "per_session_vwap_no_lookahead",
            "next_bar_fill_assumption",
            "slippage_stress",
        ),
        proposal_policy="research candidate until intraday provider and QA are stable",
        v1_path="backtest_then_proposal_capability_review",
    ),
    StrategyProfile(
        name="keltner-bollinger-macd",
        family="confluence",
        status="research_candidate",
        summary="Channel/oscillator confluence ideas such as Keltner, Bollinger, MACD, and RSI.",
        required_inputs=("ohlcv", "rolling_indicators", "indicator_warmup_window"),
        evidence_requirements=(
            "feature_bundle_alignment",
            "fundamental_or_news_conflict_check",
            "source_attributed_market_data",
        ),
        risk_controls=("indicator_disagreement_warning", "sizing_confidence_scale"),
        validation_checks=(
            "vectorized_precompute",
            "parameter_sweep_manifest",
            "probabilistic_sharpe_review",
        ),
        proposal_policy="research candidate until sweep/confidence review passes",
        v1_path="backtest_then_proposal_capability_review",
    ),
    StrategyProfile(
        name="regime-adaptive-ensemble",
        family="regime",
        status="research_candidate",
        summary="Regime-aware and ensemble voting layer that changes bias by trend, mean-reversion, or volatility regime.",
        required_inputs=("regime_features", "multi_strategy_scores", "market_breadth"),
        evidence_requirements=(
            "regime_label_explainability",
            "strategy_disagreement_trace",
            "macro_context_check",
        ),
        risk_controls=("manager_conflict_visibility", "correlation_cluster_warning"),
        validation_checks=(
            "walk_forward_split",
            "memory_ablation_comparison",
            "bootstrap_confidence_interval",
        ),
        proposal_policy="research candidate until manager/risk trace explains votes",
        v1_path="agent_trace_and_backtest_review",
    ),
    StrategyProfile(
        name="pairs-zscore",
        family="pairs",
        status="v2_deferred",
        summary="Pairs/statistical-arbitrage candidate deferred until multi-leg, shorting, borrow, and correlation risk are first-class.",
        required_inputs=(
            "paired_symbol_history",
            "spread_model",
            "borrow_and_shorting_policy",
        ),
        evidence_requirements=(
            "correlation_stability",
            "borrow_availability",
            "multi_leg_execution_audit",
        ),
        risk_controls=("legged_execution_risk", "net_vs_gross_exposure"),
        validation_checks=("cointegration_review", "slippage_and_borrow_stress"),
        proposal_policy="not V1 proposal-capable",
        v1_path="defer_to_v2",
    ),
)


LEDGER_CATEGORIES: tuple[FinanceLedgerCategory, ...] = (
    FinanceLedgerCategory(
        name="trades",
        purpose="Executed order/fill evidence for realized PnL and audit trails.",
        v1_source="paper broker executions and execution_records",
        expected_fields=(
            "order_id",
            "symbol",
            "side",
            "quantity",
            "price",
            "timestamp",
        ),
        v2_extension="external broker statement/flex-style order confirmations",
    ),
    FinanceLedgerCategory(
        name="cash",
        purpose="Cash deposits, withdrawals, and starting capital changes.",
        v1_source="paper account snapshot and explicit settings",
        expected_fields=("amount", "currency", "timestamp", "source"),
        v2_extension="external broker cash transactions",
    ),
    FinanceLedgerCategory(
        name="fees_taxes",
        purpose="Commissions, exchange fees, regulatory fees, and tax placeholders.",
        v1_source="cost model assumptions and broker rejection/outcome evidence",
        expected_fields=("amount", "currency", "fee_type", "source"),
        v2_extension="broker statement fee/tax rows",
    ),
    FinanceLedgerCategory(
        name="dividends",
        purpose="Dividend accrual/payment evidence that can affect paper-vs-broker PnL.",
        v1_source="missing unless provider/broker evidence is configured",
        expected_fields=("symbol", "amount", "currency", "ex_date", "pay_date"),
        v2_extension="external broker dividend accrual reports",
    ),
    FinanceLedgerCategory(
        name="interest",
        purpose="Cash interest, borrow cost, and margin-interest evidence.",
        v1_source="missing in simple paper mode",
        expected_fields=("amount", "currency", "rate", "period", "source"),
        v2_extension="broker interest and borrow reports",
    ),
    FinanceLedgerCategory(
        name="corporate_actions",
        purpose="Splits, mergers, symbol changes, and adjustments that can invalidate raw PnL.",
        v1_source="missing unless official/provider evidence is configured",
        expected_fields=(
            "symbol",
            "action_type",
            "ratio_or_amount",
            "effective_date",
            "source",
        ),
        v2_extension="broker and official corporate-action feeds",
    ),
)
