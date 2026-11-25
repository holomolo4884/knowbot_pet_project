from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://knowbot:knowbot@localhost:5433/knowbot"
    UPLOAD_DIR: str = "../data/uploads"
    DOCS_DIR: str = "../data/docs"        

    # LLM — OpenAI gpt-4o-mini
    LLM_BASE_URL: str = "https://api.openai.com/v1"
    LLM_API_KEY: str = Field(
        default="",
        validation_alias=AliasChoices("LLM_API_KEY", "OPENAI_API_KEY"),
    )
    LLM_MODEL: str = "gpt-4o-mini"
    LLM_TEMPERATURE: float = 0.1
    LLM_MAX_TOKENS: int = 800
    LLM_TIMEOUT: float = 60.0
    LLM_SEED: int | None = 42  # воспроизводимость генерации для eval

    # Retrieval
    RETRIEVAL_TOP_K: int = 5
    MIN_RELEVANCE_SCORE: float = 0.75

    # App
    ENV: str = "development"
    LOG_LEVEL: str = "INFO"

    # Совместимость с прокси: не все поддерживают эти параметры
    LLM_JSON_MODE: bool = True
    LLM_SUPPORTS_SEED: bool = False

    def validate_llm(self) -> None:
        """Падаем на старте с понятной ошибкой, а не 401 на первом запросе."""
        if not self.LLM_API_KEY:
            raise RuntimeError(
                "Не задан API-ключ. Добавь OPENAI_API_KEY в backend/.env "
                "или в переменные окружения."
            )
        if not self.LLM_MODEL:
            raise RuntimeError("Не задан LLM_MODEL.")


settings = Settings()