import json
import logging
from textwrap import dedent
from typing import Any, cast

import httpx
from pydantic import BaseModel, ValidationError

from agentic_trader.config import Settings
from agentic_trader.llm.providers import LLMProvider, build_provider
from agentic_trader.llm.structured import (
    redact_payload,
    request_issue_retry_prompt,
    schema_field_instruction,
    validate_structured_content,
    validation_error_summary,
    validation_retry_prompt,
)
from agentic_trader.schemas import AgentRole, LLMHealthStatus

logger = logging.getLogger(__name__)


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
            rendered = json.dumps(redact_payload(payload), ensure_ascii=True)
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

    def _generate_once(
        self,
        prompt: str,
        *,
        json_mode: bool = False,
        json_schema: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self._parse_generate_payload(
            self.provider.generate(
                prompt=prompt,
                json_mode=json_mode,
                json_schema=json_schema,
            )
        )

    def health_check(self, *, include_generation: bool = False) -> LLMHealthStatus:
        return self.provider.health_check(include_generation=include_generation)

    def complete_structured[T: BaseModel](
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
        field_instruction = schema_field_instruction(schema)

        prompt = dedent(f"""
            {system_prompt}

            You must respond with valid JSON only.
            Do not wrap the JSON in markdown fences.
            Keep string fields concise and practical.
            Return the requested schema object itself, not a status report, not a runtime summary, and not an analysis wrapper.
            If the correct decision is no-trade or hold, still return the full requested schema object.
            Never return an error object.
            {field_instruction}

            The JSON must validate against this schema:
            {schema_json}

            User request:
            {user_prompt}
            """).strip()

        last_error: Exception | None = None
        for attempt in range(self.settings.max_retries + 1):
            content = ""
            try:
                payload = self._generate_once(
                    prompt,
                    json_mode=True,
                    json_schema=schema.model_json_schema(),
                )
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
                return validate_structured_content(content, schema)
            except ValidationError as exc:
                last_error = exc
                logger.debug(
                    "LLM structured validation failed on attempt %s: %s",
                    attempt + 1,
                    exc,
                )
                prompt = validation_retry_prompt(prompt, content)
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
                prompt = request_issue_retry_prompt(prompt)
                continue

        if isinstance(last_error, ValidationError):
            raise RuntimeError(
                f"LLM structured output validation failed for {schema.__name__}: "
                f"{validation_error_summary(last_error)}"
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
        prompt = dedent(f"""
            {system_prompt}

            User request:
            {user_prompt}
            """).strip()

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
