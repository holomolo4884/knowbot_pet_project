import json
import re
from collections.abc import AsyncIterator
from typing import Any

from loguru import logger
from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AsyncOpenAI,
    RateLimitError,
)
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from app.core.config import settings


def _is_retryable(exc: BaseException) -> bool:
    """Ретраим только то, что может пройти со второй попытки.

    401/403/404 — permanent: неверный ключ, нет доступа, нет модели.
    429 и 5xx — временные: лимиты и сбои провайдера.
    Невалидный JSON — модель может выдать корректный при повторе.
    """
    if isinstance(exc, (APIConnectionError, APITimeoutError, RateLimitError)):
        return True
    if isinstance(exc, APIStatusError):
        return exc.status_code >= 500
    if isinstance(exc, json.JSONDecodeError):
        return True
    return False


class LLMService:
    """Обёртка над OpenAI-совместимым API (OpenAI / LiteAI / OpenRouter / Ollama).

    Адаптируется к прокси: запоминает неподдерживаемые параметры
    и больше их не отправляет.
    """

    def __init__(self) -> None:
        self._client = AsyncOpenAI(
            base_url=settings.LLM_BASE_URL,
            api_key=settings.LLM_API_KEY or "not-set",
            timeout=settings.LLM_TIMEOUT,
        )
        self.model = settings.LLM_MODEL
        self._unsupported: set[str] = set()
        self._max_tokens_key = "max_tokens"

    def _build_params(
        self,
        system: str,
        user: str,
        *,
        json_mode: bool,
        stream: bool = False,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "model": self.model,
            "temperature": settings.LLM_TEMPERATURE,
            self._max_tokens_key: settings.LLM_MAX_TOKENS,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        if json_mode and settings.LLM_JSON_MODE:
            params["response_format"] = {"type": "json_object"}
        if settings.LLM_SUPPORTS_SEED and settings.LLM_SEED is not None:
            params["seed"] = settings.LLM_SEED
        if stream:
            params["stream"] = True

        for key in self._unsupported:
            params.pop(key, None)
        return params

    async def _create(self, params: dict[str, Any]) -> Any:
        """Вызов API с авто-адаптацией под ограничения прокси.

        Возвращает ChatCompletion либо AsyncStream — зависит от params['stream'].
        """
        try:
            return await self._client.chat.completions.create(**params)
        except APIStatusError as e:
            if e.status_code != 400:
                raise

            msg = (e.message or "").lower()
            changed = False

            # Новые модели требуют max_completion_tokens вместо max_tokens
            if "max_completion_tokens" in msg and "max_tokens" in params:
                params["max_completion_tokens"] = params.pop("max_tokens")
                self._max_tokens_key = "max_completion_tokens"
                logger.warning("Провайдер требует max_completion_tokens — переключаюсь")
                changed = True

            dropped = [
                k
                for k in ("response_format", "seed", "temperature")
                if k in msg and k in params
            ]
            for k in dropped:
                params.pop(k)
                self._unsupported.add(k)
            if dropped:
                logger.warning(f"Провайдер не поддерживает {dropped} — отключены навсегда")
                changed = True

            if not changed:
                raise
            return await self._client.chat.completions.create(**params)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        retry=retry_if_exception(_is_retryable),
        reraise=True,
    )
    async def complete_json(self, system: str, user: str) -> dict:
        logger.debug(f"LLM request -> {self.model}")
        params = self._build_params(system, user, json_mode=True)

        resp = await self._create(params)
        raw = resp.choices[0].message.content or "{}"

        if resp.usage:
            logger.debug(
                f"tokens: {resp.usage.prompt_tokens} in / {resp.usage.completion_tokens} out"
            )

        return self._parse_json(raw)

    async def stream_text(self, system: str, user: str) -> AsyncIterator[str]:
        logger.debug(f"LLM stream -> {self.model}")
        params = self._build_params(system, user, json_mode=False, stream=True)
        stream = await self._create(params)

        async for chunk in stream:
            # Прокси присылают финальный чанк с usage и пустым choices
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta

    @staticmethod
    def _parse_json(raw: str) -> dict:
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if match:
                return json.loads(match.group(0))
            logger.error(f"LLM returned non-JSON: {raw[:200]}")
            raise


llm_service = LLMService()