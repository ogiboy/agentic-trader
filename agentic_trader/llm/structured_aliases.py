"""Schema alias maps and normalization helpers for structured LLM payloads."""

from typing import Any, cast

from pydantic import BaseModel

_NO_TRADE_PHRASE = "no trade"

WRAPPER_KEYS = (
    "coordinator",
    "brief",
    "regime",
    "assessment",
    "strategy",
    "plan",
    "risk",
    "manager",
    "decision",
    "result",
    "output",
)

SCHEMA_ALIAS_MAP: dict[str, dict[str, str]] = {
    "ResearchCoordinatorBrief": {
        "focus": "market_focus",
        "priorities": "priority_signals",
        "priority": "priority_signals",
        "cautions": "caution_flags",
        "warnings": "caution_flags",
    },
    "RegimeAssessment": {
        "bias": "direction_bias",
        "direction": "direction_bias",
        "directional_bias": "direction_bias",
        "rationale": "reasoning",
        "summary": "reasoning",
        "message": "reasoning",
        "notes": "reasoning",
        "fallback_reason": "reasoning",
        "risks": "key_risks",
    },
    "StrategyPlan": {
        "family": "strategy_family",
        "strategy": "strategy_family",
        "entry": "entry_logic",
        "entry_rules": "entry_logic",
        "invalidation": "invalidation_logic",
        "exit": "invalidation_logic",
        "rationale": "entry_logic",
        "reasons": "reason_codes",
    },
    "RiskPlan": {
        "size": "position_size_pct",
        "position_size": "position_size_pct",
        "stop": "stop_loss",
        "target": "take_profit",
        "take": "take_profit",
        "rr": "risk_reward_ratio",
        "holding_bars": "max_holding_bars",
        "holding_period": "max_holding_bars",
        "rationale": "notes",
    },
    "ManagerDecision": {
        "action": "action_bias",
        "bias": "action_bias",
        "confidence": "confidence_cap",
        "size": "size_multiplier",
        "notes": "rationale",
    },
}

SCHEMA_VALUE_ALIAS_MAP: dict[str, dict[str, dict[str, Any]]] = {
    "ResearchCoordinatorBrief": {
        "market_focus": {
            "trend": "trend_following",
            "trending": "trend_following",
            "breakout_watch": "breakout",
            "defensive": "capital_preservation",
            "capital preservation": "capital_preservation",
            "wait": "no_trade",
            "none": "no_trade",
        }
    },
    "RegimeAssessment": {
        "regime": {
            "bullish": "trend_up",
            "uptrend": "trend_up",
            "up_trend": "trend_up",
            "trend up": "trend_up",
            "bearish": "trend_down",
            "downtrend": "trend_down",
            "down_trend": "trend_down",
            "trend down": "trend_down",
            "sideways": "range",
            "ranging": "range",
            "mixed": "range",
            "choppy": "range",
            "consolidation": "range",
            "consolidating": "range",
            "neutral": "range",
            "volatile": "high_volatility",
            "high volatility": "high_volatility",
            "breakout": "breakout_candidate",
            "cautious": "no_trade",
            "wait": "no_trade",
            _NO_TRADE_PHRASE: "no_trade",
        },
        "direction_bias": {
            "bullish": "long",
            "buy": "long",
            "up": "long",
            "positive": "long",
            "bearish": "short",
            "sell": "short",
            "down": "short",
            "negative": "short",
            "neutral": "flat",
            "sideways": "flat",
            "none": "flat",
            "no_trade": "flat",
        },
    },
    "StrategyPlan": {
        "strategy_family": {
            "trend": "trend_following",
            "momentum": "trend_following",
            "breakout_candidate": "breakout",
            "range": "mean_reversion",
            "sideways": "mean_reversion",
            "hold": "no_trade",
            "none": "no_trade",
        },
        "action": {
            "long": "buy",
            "short": "sell",
            "flat": "hold",
            "none": "hold",
            "no_trade": "hold",
        },
    },
    "ManagerDecision": {
        "action_bias": {
            "long": "buy",
            "short": "sell",
            "flat": "hold",
            "none": "hold",
            "no_trade": "hold",
        }
    },
}


def contains_any(value: str, tokens: tuple[str, ...]) -> bool:
    return any(token in value for token in tokens)


def regime_alias(value: str) -> str | None:
    if "no" in value and "trade" in value:
        return "no_trade"
    if contains_any(value, ("range", "sideways", "mixed", "chop", "consolidat")):
        return "range"
    if "volatil" in value:
        return "high_volatility"
    if "break" in value:
        return "breakout_candidate"
    if contains_any(value, ("bull", "up")):
        return "trend_up"
    if contains_any(value, ("bear", "down")):
        return "trend_down"
    return None


def direction_bias_alias(value: str) -> str | None:
    if contains_any(
        value,
        (
            "flat",
            "neutral",
            "mixed",
            "sideways",
            "none",
            _NO_TRADE_PHRASE,
        ),
    ):
        return "flat"
    if contains_any(value, ("long", "buy", "bull", "up", "positive")):
        return "long"
    if contains_any(value, ("short", "sell", "bear", "down", "negative")):
        return "short"
    return None


def action_alias(value: str) -> str | None:
    if contains_any(value, ("hold", "flat", "neutral", "none", _NO_TRADE_PHRASE)):
        return "hold"
    if contains_any(value, ("long", "buy", "bull", "up")):
        return "buy"
    if contains_any(value, ("short", "sell", "bear", "down")):
        return "sell"
    return None


def semantic_value_alias(schema_name: str, field_name: str, value: str) -> Any:
    normalized = value.strip().lower().replace("-", "_")
    normalized = " ".join(normalized.split())
    compact = normalized.replace("_", " ")
    if schema_name == "RegimeAssessment" and field_name == "regime":
        return regime_alias(compact) or value
    if schema_name == "RegimeAssessment" and field_name == "direction_bias":
        return direction_bias_alias(compact) or value
    if schema_name in {"StrategyPlan", "ManagerDecision"} and field_name in {
        "action",
        "action_bias",
    }:
        return action_alias(compact) or value
    return value


def normalize_structured_payload(data: Any, schema: type[BaseModel]) -> Any:
    if not isinstance(data, dict):
        return data

    normalized = dict(cast(dict[str, Any], data))
    field_names = set(schema.model_fields)
    if field_names.isdisjoint(normalized):
        for key in WRAPPER_KEYS:
            candidate = normalized.get(key)
            if isinstance(candidate, dict):
                normalized = dict(cast(dict[str, Any], candidate))
                break

    aliases = SCHEMA_ALIAS_MAP.get(schema.__name__, {})
    for source_key, target_key in aliases.items():
        if source_key in normalized and target_key not in normalized:
            normalized[target_key] = normalized[source_key]

    value_aliases = SCHEMA_VALUE_ALIAS_MAP.get(schema.__name__, {})
    for field_name, replacements in value_aliases.items():
        value = normalized.get(field_name)
        if isinstance(value, str):
            normalized_value = value.strip().lower().replace("-", "_")
            normalized_value = " ".join(normalized_value.split())
            normalized[field_name] = replacements.get(
                normalized_value,
                semantic_value_alias(schema.__name__, field_name, value),
            )

    return normalized
