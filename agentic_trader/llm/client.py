import json
import logging
import re
from collections.abc import Callable
from textwrap import dedent
from typing import Any, TypeVar, cast

import httpx
from pydantic import BaseModel, ValidationError

from agentic_trader.config import Settings
from agentic_trader.schemas import AgentRole, LLMHealthStatus

T = TypeVar("T", bound=BaseModel)

logger = logging.getLogger(__name__)


def _coerce_numeric_strings(obj: Any) -> Any:
    """Convert numeric-like strings to int/float for safer validation."""
    if isinstance(obj, dict):
        return {k: _coerce_numeric_strings(v) for k, v in cast(dict[Any, Any], obj).items()}
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
    """Navigate one level in nested dict/list."""
    if isinstance(obj, dict) and isinstance(key, str):
        if key not in cast(dict[str, Any], obj):
            cast(dict[str, Any], obj)[key] = {}
        return cast(dict[str, Any], obj)[key]
    if isinstance(obj, list) and isinstance(key, int) and 0 <= key < len(cast(list[Any], obj)):
        return cast(list[Any], obj)[key]
    return None


# Safe coercion for common numeric fields that LLMs often emit as zeros/invalid.
_SANITIZE_RULES: dict[str, Callable[[Any], float | int]] = {
    "position_size_pct": lambda v: min(max(float(v) if v is not None else 0.01, 0.01), 1.0),
    "size_multiplier": lambda v: min(max(float(v) if v is not None else 0.01, 0.01), 1.0),
    "max_holding_bars": lambda v: max(int(v) if v is not None else 1, 1),
    "stop_loss": lambda v: max(float(v) if v is not None else 1e-6, 1e-6),
    "take_profit": lambda v: max(float(v) if v is not None else 1e-6, 1e-6),
    "risk_reward_ratio": lambda v: max(float(v) if v is not None else 1e-6, 1e-6),
}


def _extract_field_name_from_path(path: tuple[str | int, ...]) -> str | None:
    """Extract field name (last string component) from error path."""
    for component in reversed(path):
        if isinstance(component, str):
            return component
    return None


def _attempt_sanitize_and_validate(
    data: Any, exc: ValidationError, schema: type[T]
) -> T | None:
    """Try to fix common numeric field violations and retry validation."""
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
        logger.warning("Sanitization retry failed: %s", retry_exc)
        return None


class LocalLLM:
    def __init__(self, settings: Settings, *, model_name: str | None = None):
        self.settings = settings
        self.base_url = settings.base_url.removesuffix("/v1").rstrip("/")
        self.model_name = model_name or settings.model_name
        self.client = httpx.Client(
            timeout=settings.request_timeout_seconds,
        )

    def for_role(self, role: AgentRole) -> "LocalLLM":
        routed_model = self.settings.model_for_role(role)
        if routed_model == self.model_name:
            return self
        return LocalLLM(self.settings, model_name=routed_model)

    @staticmethod
    def _payload_preview(payload: Any) -> str:
        try:
            rendered = json.dumps(payload, ensure_ascii=True)
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

    def _generate_once(self, prompt: str) -> dict[str, Any]:
        response = self.client.post(
            f"{self.base_url}/api/generate",
            json={
                "model": self.model_name,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": self.settings.temperature,
                    "num_predict": self.settings.max_output_tokens,
                },
            },
        )
        response.raise_for_status()
        return self._parse_generate_payload(response.json())

    def health_check(self) -> LLMHealthStatus:
        try:
            response = self.client.get(f"{self.base_url}/api/tags")
            response.raise_for_status()
            payload = cast(dict[str, Any], response.json())
            models_obj: Any = payload.get("models", [])
            models: list[dict[str, Any]] = []
            if isinstance(models_obj, list):
                for raw_item in cast(list[Any], models_obj):
                    if isinstance(raw_item, dict):
                        models.append(cast(dict[str, Any], raw_item))
            available: set[str] = set()
            for item in models:
                name: Any = item.get("name")
                if isinstance(name, str):
                    available.add(name)
            model_available = self.model_name in available
            message = (
                "Ollama is reachable and the configured model is available."
                if model_available
                else "Ollama is reachable, but the configured model is not listed."
            )
            return LLMHealthStatus(
                provider="ollama",
                base_url=self.settings.base_url,
                model_name=self.model_name,
                service_reachable=True,
                model_available=model_available,
                message=message,
            )
        except Exception as exc:
            return LLMHealthStatus(
                provider="ollama",
                base_url=self.settings.base_url,
                model_name=self.model_name,
                service_reachable=False,
                model_available=False,
                message=f"Unable to reach Ollama: {exc}",
            )

    def complete_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        schema: type[T],
    ) -> T:
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
                payload = self._generate_once(prompt)
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
                # Try to parse JSON so we can coerce/sanitize common numeric issues
                try:
                    data_obj = json.loads(content)
                except json.JSONDecodeError:
                    # Fall back to pydantic's JSON parsing (more permissive)
                    parsed = schema.model_validate_json(content)
                    if hasattr(parsed, "source"):
                        parsed = parsed.model_copy(
                            update={"source": "llm", "fallback_reason": None}
                        )
                    return parsed

                # Convert numeric-like strings into numeric types for validation
                data_obj = _coerce_numeric_strings(data_obj)

                try:
                    parsed = schema.model_validate(data_obj)
                    if hasattr(parsed, "source"):
                        parsed = parsed.model_copy(
                            update={"source": "llm", "fallback_reason": None}
                        )
                    return parsed
                except ValidationError as exc:
                    # Attempt automatic sanitization for a few known numeric fields
                    sanitized = _attempt_sanitize_and_validate(data_obj, exc, schema)
                    if sanitized is not None:
                        if hasattr(sanitized, "source"):
                            sanitized = sanitized.model_copy(
                                update={"source": "llm", "fallback_reason": None}
                            )
                        return sanitized
                    # Let outer ValidationError handler request corrected JSON
                    raise
            except ValidationError as exc:
                last_error = exc
                logger.warning(
                    "LLM structured validation failed on attempt %s: %s",
                    attempt + 1,
                    exc,
                )
                prompt = dedent(
                    f"""
                    {prompt}

                    Your previous response did not validate:
                    {content}

                    Return corrected JSON only.
                    """
                ).strip()
                continue
            except (
                httpx.HTTPError,
                RuntimeError,
                ValueError,
            ) as exc:
                last_error = exc
                logger.warning(
                    "LLM structured request issue on attempt %s: %s",
                    attempt + 1,
                    exc,
                )
                prompt = dedent(
                    f"""
                    {prompt}

                    Your previous response was empty, malformed, or otherwise invalid.
                    Return a complete JSON object only.
                    """
                ).strip()
                continue

        raise RuntimeError(
            f"LLM structured output validation failed: {last_error}"
        ) from last_error

    def complete_text(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
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
                logger.warning(
                    "LLM text request issue on attempt %s: %s",
                    attempt + 1,
                    exc,
                )
                continue

        raise RuntimeError(f"LLM text output failed: {last_error}") from last_error
