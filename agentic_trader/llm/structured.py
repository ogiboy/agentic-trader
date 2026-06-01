import json
import logging
import re
from collections.abc import Callable
from textwrap import dedent
from typing import Any, cast

from pydantic import BaseModel, ValidationError

from agentic_trader.json_utils import object_dict_or_none as _object_mapping

logger = logging.getLogger(__name__)
_SENSITIVE_PAYLOAD_KEYS = {"thinking", "thought", "thoughts", "reasoning"}
_NO_TRADE_PHRASE = "no trade"


def coerce_numeric_strings(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {
            k: coerce_numeric_strings(v) for k, v in cast(dict[Any, Any], obj).items()
        }
    if isinstance(obj, list):
        return [coerce_numeric_strings(item) for item in cast(list[Any], obj)]
    if isinstance(obj, str):
        s = obj.strip()
        if re.fullmatch(r"-?\d+(?:\.\d+)?", s):
            try:
                return int(s) if s.isdigit() else float(s)
            except (ValueError, TypeError):
                return obj
    return obj


def get_by_loc(obj: Any, path: tuple[str | int, ...]) -> Any:
    current: object = obj
    for part in path:
        current_mapping = _object_mapping(current)
        if current_mapping is not None and isinstance(part, str):
            current = current_mapping.get(part)
        elif isinstance(current, list) and isinstance(part, int):
            current_list = cast(list[object], current)
            if 0 <= part < len(current_list):
                current = current_list[part]
            else:
                return None
        else:
            return None
    return current


def set_by_loc(obj: Any, path: tuple[str | int, ...], value: Any) -> bool:
    if not path:
        return False
    current = obj
    for part in path[:-1]:
        next_item = navigate_one(current, part)
        if next_item is None:
            return False
        current = next_item
    last_part = path[-1]
    if isinstance(current, dict) and isinstance(last_part, str):
        current[last_part] = value
        return True
    if isinstance(current, list) and isinstance(last_part, int):
        current_list = cast(list[object], current)
        if 0 <= last_part < len(current_list):
            current_list[last_part] = value
            return True
    return False


def navigate_one(obj: Any, key: str | int) -> Any:
    if isinstance(obj, dict) and isinstance(key, str):
        if key not in cast(dict[str, Any], obj):
            cast(dict[str, Any], obj)[key] = {}
        return cast(dict[str, Any], obj)[key]
    if (
        isinstance(obj, list)
        and isinstance(key, int)
        and 0 <= key < len(cast(list[Any], obj))
    ):
        return cast(list[Any], obj)[key]
    return None


def coerce_confidence(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, str):
        normalized = value.strip().lower()
        qualitative = {
            "none": 0.0,
            "unknown": 0.0,
            "very low": 0.1,
            "low": 0.25,
            "medium": 0.5,
            "moderate": 0.5,
            "high": 0.75,
            "very high": 0.9,
        }
        if normalized in qualitative:
            return qualitative[normalized]
        if normalized.endswith("%"):
            return min(max(float(normalized[:-1]) / 100.0, 0.0), 1.0)
    return min(max(float(value), 0.0), 1.0)


SANITIZE_RULES: dict[str, Callable[[Any], float | int]] = {
    "confidence": coerce_confidence,
    "confidence_cap": coerce_confidence,
    "position_size_pct": lambda v: min(
        max(float(v) if v is not None else 0.01, 0.01), 1.0
    ),
    "size_multiplier": lambda v: min(
        max(float(v) if v is not None else 0.01, 0.01), 1.0
    ),
    "max_holding_bars": lambda v: max(int(v) if v is not None else 1, 1),
    "stop_loss": lambda v: max(float(v) if v is not None else 1e-6, 1e-6),
    "take_profit": lambda v: max(float(v) if v is not None else 1e-6, 1e-6),
    "risk_reward_ratio": lambda v: max(float(v) if v is not None else 1e-6, 1e-6),
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


def redact_payload(value: Any) -> Any:
    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for key, item in cast(dict[Any, Any], value).items():
            key_text = str(key)
            if key_text.lower() in _SENSITIVE_PAYLOAD_KEYS:
                redacted[key_text] = "<redacted>"
            else:
                redacted[key_text] = redact_payload(item)
        return redacted
    if isinstance(value, list):
        return [redact_payload(item) for item in cast(list[Any], value)]
    return value


def extract_field_name_from_path(path: tuple[str | int, ...]) -> str | None:
    for component in reversed(path):
        if isinstance(component, str):
            return component
    return None


def attempt_sanitize_and_validate[T: BaseModel](
    data: Any, exc: ValidationError, schema: type[T]
) -> T | None:
    if not isinstance(data, dict):
        return None

    try:
        errors = exc.errors()
    except Exception:
        return None

    if not errors:
        return None

    changes_made = False
    for error in errors:
        error_path: tuple[str | int, ...] = tuple(error.get("loc", ()))
        if not error_path:
            continue

        field_name = extract_field_name_from_path(error_path)
        if not field_name or field_name not in SANITIZE_RULES:
            continue

        current_value = get_by_loc(data, error_path)
        try:
            sanitized_value = SANITIZE_RULES[field_name](current_value)
            set_by_loc(data, error_path, sanitized_value)
            changes_made = True
            logger.info(
                "Sanitized field '%s': %s -> %s",
                field_name,
                current_value,
                sanitized_value,
            )
        except Exception as e:
            logger.debug("Could not sanitize %s: %s", field_name, e)

    if not changes_made:
        return None

    data = coerce_numeric_strings(data)
    try:
        return schema.model_validate(data)
    except ValidationError as retry_exc:
        logger.debug("Sanitization retry failed: %s", retry_exc)
        return None


def mark_llm_source[T: BaseModel](parsed: T) -> T:
    if hasattr(parsed, "source"):
        return parsed.model_copy(update={"source": "llm", "fallback_reason": None})
    return parsed


def validate_structured_content[T: BaseModel](content: str, schema: type[T]) -> T:
    try:
        data_obj = json.loads(content)
    except json.JSONDecodeError:
        return mark_llm_source(schema.model_validate_json(content))

    data_obj = normalize_structured_payload(data_obj, schema)
    data_obj = coerce_numeric_strings(data_obj)
    try:
        return mark_llm_source(schema.model_validate(data_obj))
    except ValidationError as exc:
        sanitized = attempt_sanitize_and_validate(data_obj, exc, schema)
        if sanitized is not None:
            return mark_llm_source(sanitized)
        raise


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


def schema_field_instruction(schema: type[BaseModel]) -> str:
    required = schema.model_json_schema().get("required", [])
    field_names = list(schema.model_fields)
    required_text = ", ".join(str(item) for item in required) or "none"
    allowed_text = ", ".join(field_names)
    return (
        f"Required top-level keys: {required_text}.\n"
        f"Allowed top-level keys: {allowed_text}."
    )


def validation_error_summary(exc: ValidationError) -> str:
    try:
        errors = exc.errors()
    except Exception:
        return "schema validation failed"

    missing_fields: list[str] = []
    invalid_fields: list[str] = []
    for error in errors:
        loc = error.get("loc", ())
        field = ".".join(str(part) for part in loc) if loc else "(root)"
        if error.get("type") == "missing":
            missing_fields.append(field)
        else:
            invalid_fields.append(field)

    parts: list[str] = []
    if missing_fields:
        parts.append(f"missing required fields: {', '.join(missing_fields)}")
    if invalid_fields:
        parts.append(f"invalid fields: {', '.join(invalid_fields)}")
    return "; ".join(parts) if parts else "schema validation failed"


def validation_retry_prompt(prompt: str, content: str) -> str:
    return dedent(f"""
        {prompt}

        Your previous response did not validate:
        {content}

        Return corrected JSON only.
        """).strip()


def request_issue_retry_prompt(prompt: str) -> str:
    return dedent(f"""
        {prompt}

        Your previous response was empty, malformed, or otherwise invalid.
        Return a complete JSON object only.
        """).strip()
