import json
import logging
from textwrap import dedent
from typing import Any, TypeVar, cast

import httpx
from pydantic import BaseModel, ValidationError

from agentic_trader.config import Settings
from agentic_trader.schemas import AgentRole, LLMHealthStatus

T = TypeVar("T", bound=BaseModel)

logger = logging.getLogger(__name__)


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
            raise RuntimeError(f"LLM returned a non-object payload: {self._payload_preview(payload)}")
        return cast(dict[str, Any], payload)

    def _extract_response_text(self, payload: dict[str, Any]) -> str:
        error_obj = payload.get("error")
        if isinstance(error_obj, str) and error_obj.strip():
            raise RuntimeError(f"LLM service returned an error payload: {error_obj.strip()}")
        if isinstance(error_obj, dict):
            message = error_obj.get("message")
            if isinstance(message, str) and message.strip():
                raise RuntimeError(f"LLM service returned an error payload: {message.strip()}")

        response_obj = payload.get("response", "")
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
                parsed = schema.model_validate_json(content)
                if hasattr(parsed, "source"):
                    parsed = parsed.model_copy(
                        update={"source": "llm", "fallback_reason": None}
                    )
                return parsed
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
            except (httpx.HTTPError, json.JSONDecodeError, RuntimeError, ValueError) as exc:
                last_error = exc if isinstance(exc, Exception) else RuntimeError(str(exc))
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

        raise RuntimeError(f"LLM structured output validation failed: {last_error}") from last_error

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
            except (httpx.HTTPError, json.JSONDecodeError, RuntimeError, ValueError) as exc:
                last_error = exc if isinstance(exc, Exception) else RuntimeError(str(exc))
                logger.warning(
                    "LLM text request issue on attempt %s: %s",
                    attempt + 1,
                    exc,
                )
                continue

        raise RuntimeError(f"LLM text output failed: {last_error}") from last_error
