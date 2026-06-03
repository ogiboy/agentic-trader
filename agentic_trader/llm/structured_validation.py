"""Validation and retry-prompt helpers for structured LLM output."""

import json
import logging
from textwrap import dedent
from typing import Any

from pydantic import BaseModel, ValidationError

from agentic_trader.llm.structured_aliases import normalize_structured_payload
from agentic_trader.llm.structured_coercion import (
    SANITIZE_RULES,
    coerce_numeric_strings,
    get_by_loc,
    set_by_loc,
)

logger = logging.getLogger(__name__)


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
        except Exception as exc_info:
            logger.debug("Could not sanitize %s: %s", field_name, exc_info)

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
