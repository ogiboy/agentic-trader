import json
import logging
import re
from collections.abc import Callable
from textwrap import dedent
from typing import Any, TypeVar, cast

import httpx
from pydantic import BaseModel, ValidationError

from agentic_trader.config import Settings
from agentic_trader.llm.providers import LLMProvider, build_provider
from agentic_trader.schemas import AgentRole, LLMHealthStatus

T = TypeVar("T", bound=BaseModel)

logger = logging.getLogger(__name__)
_SENSITIVE_PAYLOAD_KEYS = {"thinking", "thought", "thoughts", "reasoning"}


def _coerce_numeric_strings(obj: Any) -> Any:
    """
    Recursively convert strings that represent whole numbers or decimals into int or float values.
    
    Recurses into dicts and lists; for string values, trims whitespace and if the entire string matches the numeric pattern "-?\\d+(?:\\.\\d+)?" it returns an `int` when the string contains only digits (no sign/decimal) and a `float` otherwise. If parsing fails or the value is not a numeric string, the original value is returned unchanged.
    
    Parameters:
        obj (Any): The value (or nested structure) to coerce.
    
    Returns:
        Any: The input with numeric-like strings converted to `int` or `float` where applicable; other values are returned as-is.
    """
    if isinstance(obj, dict):
        return {
            k: _coerce_numeric_strings(v) for k, v in cast(dict[Any, Any], obj).items()
        }
    if isinstance(obj, list):
        return [_coerce_numeric_strings(item) for item in cast(list[Any], obj)]
    if isinstance(obj, str):
        s = obj.strip()
        if re.fullmatch(r"-?\d+(?:\.\d+)?", s):
            try:
                return int(s) if s.isdigit() else float(s)
            except (ValueError, TypeError):
                return obj
    return obj


def _get_by_loc(obj: Any, path: tuple[str | int, ...]) -> Any:
    """Navigate nested dict/list by path tuple."""
    current = obj
    for part in path:
        if isinstance(current, dict) and isinstance(part, str):
            current = current.get(part)
        elif isinstance(current, list) and isinstance(part, int):
            if 0 <= part < len(current):
                current = current[part]
            else:
                return None
        else:
            return None
    return current


def _set_by_loc(obj: Any, path: tuple[str | int, ...], value: Any) -> bool:
    """Set value in nested dict/list at path tuple."""
    if not path:
        return False
    current = obj
    # Navigate to parent
    for part in path[:-1]:
        next_item = _navigate_one(current, part)
        if next_item is None:
            return False
        current = next_item
    # Set final value
    last_part = path[-1]
    if isinstance(current, dict) and isinstance(last_part, str):
        current[last_part] = value
        return True
    if isinstance(current, list) and isinstance(last_part, int):
        if 0 <= last_part < len(current):
            current[last_part] = value
            return True
    return False


def _navigate_one(obj: Any, key: str | int) -> Any:
    """
    Retrieve the nested value one level down for a dict or list key, creating a missing dict key as an empty dict.
    
    Parameters:
        obj (Any): The container to navigate; expected to be a dict or list.
        key (str | int): For dicts, a string key (will be created as an empty dict if missing). For lists, an integer index (must be within bounds).
    
    Returns:
        Any: The value at the next level for the given key/index, or `None` if navigation is not possible.
    """
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


# Safe coercion for common numeric fields that LLMs often emit as zeros/invalid.
_SANITIZE_RULES: dict[str, Callable[[Any], float | int]] = {
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
_WRAPPER_KEYS = (
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
_SCHEMA_ALIAS_MAP: dict[str, dict[str, str]] = {
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
        "rationale": "reasoning",
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


def _redact_payload(value: Any) -> Any:
    """Remove provider reasoning fields before payload previews reach logs or UI."""
    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for key, item in cast(dict[Any, Any], value).items():
            key_text = str(key)
            if key_text.lower() in _SENSITIVE_PAYLOAD_KEYS:
                redacted[key_text] = "<redacted>"
            else:
                redacted[key_text] = _redact_payload(item)
        return redacted
    if isinstance(value, list):
        return [_redact_payload(item) for item in cast(list[Any], value)]
    return value


def _extract_field_name_from_path(path: tuple[str | int, ...]) -> str | None:
    """Extract field name (last string component) from error path."""
    for component in reversed(path):
        if isinstance(component, str):
            return component
    return None


def _attempt_sanitize_and_validate(
    data: Any, exc: ValidationError, schema: type[T]
) -> T | None:
    """
    Attempt to coerce and clamp common numeric fields in a dict and retry Pydantic validation.
    
    Examines the errors from a Pydantic ValidationError and, for any error path whose final string key matches a known sanitize rule, applies that rule to mutate `data`. After applying any changes, it coerces numeric-like strings to numbers and attempts to validate into `schema`. If no applicable sanitizations are found or re-validation fails, returns None.
    
    Parameters:
        data (Any): The parsed object to inspect and potentially mutate; function only operates when this is a dict.
        exc (ValidationError): The original Pydantic ValidationError containing `.errors()` to determine failing locations.
        schema (type[T]): The Pydantic model class to validate against after sanitization.
    
    Returns:
        T | None: The validated model instance if sanitization and re-validation succeed, otherwise `None`.
    """
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

        field_name = _extract_field_name_from_path(error_path)
        if not field_name or field_name not in _SANITIZE_RULES:
            continue

        current_value = _get_by_loc(data, error_path)
        try:
            sanitized_value = _SANITIZE_RULES[field_name](current_value)
            _set_by_loc(data, error_path, sanitized_value)
            changes_made = True
            logger.info(
                "Sanitized field '%s': %s → %s",
                field_name,
                current_value,
                sanitized_value,
            )
        except Exception as e:
            logger.debug("Could not sanitize %s: %s", field_name, e)

    if not changes_made:
        return None

    data = _coerce_numeric_strings(data)
    try:
        return schema.model_validate(data)
    except ValidationError as retry_exc:
        logger.debug("Sanitization retry failed: %s", retry_exc)
        return None


def _mark_llm_source(parsed: T) -> T:
    """
    Mark a Pydantic model's source as "llm" and clear its fallback reason when present.
    
    If the provided object exposes a `source` attribute, return a copy with `source` set to `"llm"` and `fallback_reason` set to `None`. Otherwise return the original object unchanged.
    
    Parameters:
        parsed: A model or object; typically a Pydantic model instance that may have `source` and `fallback_reason` attributes.
    
    Returns:
        The updated model with `source="llm"` and `fallback_reason=None` if applicable, otherwise the original `parsed`.
    """
    if hasattr(parsed, "source"):
        return cast(
            T,
            parsed.model_copy(update={"source": "llm", "fallback_reason": None}),
        )
    return parsed


def _validate_structured_content(content: str, schema: type[T]) -> T:
    """
    Validate a JSON-formatted string and return a validated Pydantic model instance, applying numeric coercion and targeted sanitization when necessary.
    
    Attempts to parse `content` as JSON. If parsing fails, delegates to `schema.model_validate_json(content)` and marks the result as coming from the LLM. If parsing succeeds, coerces numeric-looking strings to numbers, then validates via `schema.model_validate`. On ValidationError, attempts targeted sanitization and re-validation; if sanitization produces a valid model that is returned, otherwise the original ValidationError is re-raised.
    
    Parameters:
        content (str): The raw JSON text returned by the LLM.
        schema (type[T]): The Pydantic model class to validate against.
    
    Returns:
        T: An instance of `schema` validated and possibly sanitized.
    
    Raises:
        pydantic.ValidationError: If validation fails and sanitization does not produce a valid model.
    """
    try:
        data_obj = json.loads(content)
    except json.JSONDecodeError:
        return _mark_llm_source(schema.model_validate_json(content))

    data_obj = _normalize_structured_payload(data_obj, schema)
    data_obj = _coerce_numeric_strings(data_obj)
    try:
        return _mark_llm_source(schema.model_validate(data_obj))
    except ValidationError as exc:
        sanitized = _attempt_sanitize_and_validate(data_obj, exc, schema)
        if sanitized is not None:
            return _mark_llm_source(sanitized)
        raise


def _normalize_structured_payload(data: Any, schema: type[BaseModel]) -> Any:
    """Unwrap harmless LLM JSON wrappers and alias field names before validation."""
    if not isinstance(data, dict):
        return data

    normalized = dict(cast(dict[str, Any], data))
    field_names = set(schema.model_fields)
    if field_names.isdisjoint(normalized):
        for key in _WRAPPER_KEYS:
            candidate = normalized.get(key)
            if isinstance(candidate, dict):
                normalized = dict(cast(dict[str, Any], candidate))
                break

    aliases = _SCHEMA_ALIAS_MAP.get(schema.__name__, {})
    for source_key, target_key in aliases.items():
        if source_key in normalized and target_key not in normalized:
            normalized[target_key] = normalized[source_key]

    return normalized


def _validation_error_summary(exc: ValidationError) -> str:
    """Return a concise operator-facing summary for a Pydantic validation error."""
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


def _validation_retry_prompt(prompt: str, content: str) -> str:
    """
    Builds a retry instruction telling the LLM its previous JSON response failed validation and requesting corrected JSON only.
    
    Parameters:
        prompt (str): The original prompt sent to the LLM.
        content (str): The previous LLM response that failed validation.
    
    Returns:
        str: A dedented prompt string that includes the original prompt, a note that the previous response did not validate (including that response), and a directive to "Return corrected JSON only."
    """
    return dedent(
        f"""
        {prompt}

        Your previous response did not validate:
        {content}

        Return corrected JSON only.
        """
    ).strip()


def _request_issue_retry_prompt(prompt: str) -> str:
    """
    Constructs a retry prompt instructing the model to return a complete JSON object when the previous response was empty or invalid.
    
    Parameters:
        prompt (str): The original prompt to include at the start of the retry message.
    
    Returns:
        str: A dedented string containing the original prompt followed by a short instruction that the previous response was empty, malformed, or invalid and that the model should return a complete JSON object only.
    """
    return dedent(
        f"""
        {prompt}

        Your previous response was empty, malformed, or otherwise invalid.
        Return a complete JSON object only.
        """
    ).strip()


class LocalLLM:
    def __init__(self, settings: Settings, *, model_name: str | None = None):
        """
        Initialize the LocalLLM with application settings and an optional model override.
        
        Parameters:
            settings (Settings): Configuration and feature flags used to build the underlying LLM provider.
            model_name (str | None): Optional model identifier to use instead of the default routing from settings; when None, the provider's default model is used.
        """
        self.settings = settings
        self.provider: LLMProvider = build_provider(settings, model_name=model_name)
        self.base_url = self.provider.base_url
        self.model_name = self.provider.model_name
        self.client = self.provider.client

    def for_role(self, role: AgentRole) -> "LocalLLM":
        routed_model = self.settings.model_for_role(role)
        if routed_model == self.model_name:
            return self
        return LocalLLM(self.settings, model_name=routed_model)

    @staticmethod
    def _payload_preview(payload: Any) -> str:
        try:
            rendered = json.dumps(_redact_payload(payload), ensure_ascii=True)
        except Exception:
            rendered = str(payload)
        return rendered[:400]

    def _parse_generate_payload(self, payload: Any) -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise RuntimeError(
                f"LLM returned a non-object payload: {self._payload_preview(payload)}"
            )
        return cast(dict[str, Any], payload)

    def _extract_response_text(self, payload: dict[str, Any]) -> str:
        error_obj: Any = payload.get("error")
        if isinstance(error_obj, str) and error_obj.strip():
            raise RuntimeError(
                f"LLM service returned an error payload: {error_obj.strip()}"
            )
        if isinstance(error_obj, dict):
            message: Any = cast(dict[str, Any], error_obj).get("message")
            if isinstance(message, str) and message.strip():
                raise RuntimeError(
                    f"LLM service returned an error payload: {message.strip()}"
                )

        response_obj: Any = payload.get("response", "")
        if isinstance(response_obj, str):
            return response_obj.strip()
        if response_obj is None:
            return ""
        if isinstance(response_obj, (dict, list)):
            return json.dumps(response_obj, ensure_ascii=False).strip()
        return str(response_obj).strip()

    def _generate_once(self, prompt: str, *, json_mode: bool = False) -> dict[str, Any]:
        return self._parse_generate_payload(
            self.provider.generate(prompt=prompt, json_mode=json_mode)
        )

    def health_check(self) -> LLMHealthStatus:
        return self.provider.health_check()

    def complete_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        schema: type[T],
    ) -> T:
        """
        Request a structured JSON completion from the LLM and validate it against the provided Pydantic schema.
        
        Parameters:
            system_prompt (str): The system-level instructions to include at the start of the prompt.
            user_prompt (str): The user-level request to include in the prompt.
            schema (type[T]): A Pydantic model class used to validate and coerce the returned JSON into an instance of `T`.
        
        Returns:
            T: An instance of the provided Pydantic model populated from the validated LLM JSON response.
        
        Raises:
            RuntimeError: If the LLM repeatedly returns empty, malformed, or non-validating responses and all retry attempts are exhausted; the last underlying exception is chained.
        """
        schema_json = json.dumps(schema.model_json_schema(), indent=2)

        prompt = dedent(
            f"""
            {system_prompt}

            You must respond with valid JSON only.
            Do not wrap the JSON in markdown fences.
            Keep string fields concise and practical.

            The JSON must validate against this schema:
            {schema_json}

            User request:
            {user_prompt}
            """
        ).strip()

        last_error: Exception | None = None
        for attempt in range(self.settings.max_retries + 1):
            content = ""
            try:
                payload = self._generate_once(prompt, json_mode=True)
                content = self._extract_response_text(payload)
                logger.debug(
                    "LLM structured response attempt %s: content_length=%s content_preview=%s",
                    attempt + 1,
                    len(content),
                    content[:100] if content else "(empty)",
                )
                if not content:
                    raise RuntimeError(
                        f"LLM returned an empty response body. Payload preview: {self._payload_preview(payload)}"
                    )
                return _validate_structured_content(content, schema)
            except ValidationError as exc:
                last_error = exc
                logger.debug(
                    "LLM structured validation failed on attempt %s: %s",
                    attempt + 1,
                    exc,
                )
                prompt = _validation_retry_prompt(prompt, content)
                continue
            except (
                httpx.HTTPError,
                RuntimeError,
                ValueError,
            ) as exc:
                last_error = exc
                logger.debug(
                    "LLM structured request issue on attempt %s: %s",
                    attempt + 1,
                    exc,
                )
                prompt = _request_issue_retry_prompt(prompt)
                continue

        if isinstance(last_error, ValidationError):
            raise RuntimeError(
                f"LLM structured output validation failed for {schema.__name__}: "
                f"{_validation_error_summary(last_error)}"
            ) from last_error
        raise RuntimeError(f"LLM request failed: {last_error}") from last_error

    def complete_text(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        """
        Send the combined system and user prompts to the configured LLM provider and return the provider's textual response.
        
        The call is retried on transient request or provider errors up to `self.settings.max_retries`. If the provider returns an empty response or all attempts fail, a RuntimeError is raised.
        
        Parameters:
            system_prompt (str): The system-level instructions to include in the prompt.
            user_prompt (str): The user's request to include in the prompt.
        
        Returns:
            str: The LLM's textual response.
        
        Raises:
            RuntimeError: If the LLM returns an empty response or all retry attempts fail.
        """
        prompt = dedent(
            f"""
            {system_prompt}

            User request:
            {user_prompt}
            """
        ).strip()

        last_error: Exception | None = None
        for attempt in range(self.settings.max_retries + 1):
            try:
                payload = self._generate_once(prompt)
                content = self._extract_response_text(payload)
                logger.debug(
                    "LLM text response attempt %s: content_length=%s",
                    attempt + 1,
                    len(content),
                )
                if not content:
                    raise RuntimeError(
                        f"LLM returned an empty text response. Payload preview: {self._payload_preview(payload)}"
                    )
                return content
            except (
                httpx.HTTPError,
                RuntimeError,
                ValueError,
            ) as exc:
                last_error = exc
                logger.debug(
                    "LLM text request issue on attempt %s: %s",
                    attempt + 1,
                    exc,
                )
                continue

        raise RuntimeError(f"LLM text output failed: {last_error}") from last_error
