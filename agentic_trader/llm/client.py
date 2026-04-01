import json
import logging
from textwrap import dedent
from typing import Any, TypeVar, cast

import httpx
from pydantic import BaseModel, ValidationError

from agentic_trader.config import Settings
from agentic_trader.schemas import LLMHealthStatus

T = TypeVar("T", bound=BaseModel)

logger = logging.getLogger(__name__)


class LocalLLM:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.base_url = settings.base_url.removesuffix("/v1").rstrip("/")
        self.client = httpx.Client(
            timeout=settings.request_timeout_seconds,
        )

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
            model_available = self.settings.model_name in available
            message = (
                "Ollama is reachable and the configured model is available."
                if model_available
                else "Ollama is reachable, but the configured model is not listed."
            )
            return LLMHealthStatus(
                provider="ollama",
                base_url=self.settings.base_url,
                model_name=self.settings.model_name,
                service_reachable=True,
                model_available=model_available,
                message=message,
            )
        except Exception as exc:
            return LLMHealthStatus(
                provider="ollama",
                base_url=self.settings.base_url,
                model_name=self.settings.model_name,
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

        last_error = None
        for attempt in range(self.settings.max_retries + 1):
            response = self.client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.settings.model_name,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": self.settings.temperature,
                        "num_predict": self.settings.max_output_tokens,
                    },
                },
            )
            response.raise_for_status()
            payload = response.json()
            content = payload.get("response", "")

            logger.debug(
                f"LLM response (attempt {attempt + 1}): "
                f"status={response.status_code}, "
                f"content_length={len(content)}, "
                f"content_preview={content[:100] if content else '(empty)'}"
            )

            # Check for empty response
            if not content or not content.strip():
                raise RuntimeError(f"LLM returned empty response. Payload: {payload}")

            try:
                parsed = schema.model_validate_json(content)
                if hasattr(parsed, "source"):
                    parsed = parsed.model_copy(
                        update={"source": "llm", "fallback_reason": None}
                    )
                return parsed
            except ValidationError as exc:
                last_error = exc
                logger.warning(
                    f"LLM response validation failed (attempt {attempt + 1}): {exc}"
                )
                prompt = dedent(
                    f"""
                    {prompt}

                    Your previous response did not validate:
                    {content}

                    Return corrected JSON only.
                    """
                ).strip()
            except httpx.HTTPStatusError as exc:
                # Don't retry on 5xx errors - let them trigger fallback
                logger.error(
                    f"LLM HTTP error: status={exc.response.status_code}, "
                    f"response={exc.response.text[:200]}"
                )
                raise RuntimeError(
                    f"LLM service error (HTTP {exc.response.status_code}): {exc.response.text}"
                ) from exc
            except Exception as exc:
                logger.error(f"LLM request error (attempt {attempt + 1}): {exc}")
                raise

        raise RuntimeError(f"LLM structured output validation failed: {last_error}")

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

        try:
            response = self.client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.settings.model_name,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": self.settings.temperature,
                        "num_predict": self.settings.max_output_tokens,
                    },
                },
            )
            response.raise_for_status()
            payload = cast(dict[str, Any], response.json())
            content = payload.get("response", "")

            logger.debug(
                f"LLM text response: "
                f"status={response.status_code}, "
                f"content_length={len(content)}"
            )

            return str(content).strip()
        except httpx.HTTPStatusError as exc:
            logger.error(
                f"LLM HTTP error: status={exc.response.status_code}, "
                f"response={exc.response.text[:200]}"
            )
            raise RuntimeError(
                f"LLM service error (HTTP {exc.response.status_code})"
            ) from exc
