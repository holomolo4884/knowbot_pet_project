import asyncio

from loguru import logger
from openai import APIStatusError

from app.core.config import settings
from app.services.llm_service import llm_service

HINTS = {
    401: "Неверный ключ или не тот Base URL. Для LiteAI: https://api.liteai.tech/v1",
    403: "Ключ валиден, но нет доступа к модели.",
    404: "Модель не найдена. У LiteAI нет gpt-4o-mini, попробуй gpt-5.6-sol.",
    429: "Лимит или исчерпан баланс токенов. Проверь в боте LiteAI.",
}


async def main() -> None:
    print(">>> llm_check запущен", flush=True)

    settings.validate_llm()

    key = settings.LLM_API_KEY
    print(f">>> base_url = {settings.LLM_BASE_URL}", flush=True)
    print(f">>> model    = {settings.LLM_MODEL}", flush=True)
    print(f">>> key      = len={len(key)} prefix={key[:6]} suffix={key[-4:]}", flush=True)
    print(">>> отправляю запрос...", flush=True)

    try:
        result = await llm_service.complete_json(
            system="Отвечай строго в JSON.",
            user='Верни объект {"status": "ok", "model": "название модели"}',
        )
        logger.success(f"LLM ответил: {result}")
    except APIStatusError as e:
        logger.error(f"HTTP {e.status_code}: {e.message}")
        logger.error(HINTS.get(e.status_code, "Смотри текст ошибки выше."))
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())