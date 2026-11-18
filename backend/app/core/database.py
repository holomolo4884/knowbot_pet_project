from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://knowbot:knowbot@localhost:5432/knowbot"
    
    class Config:
        env_file = ".env"

settings = Settings()

# Создаем асинхронный движок
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,  # Поставь True, если хочешь видеть SQL-запросы в консоли
    pool_pre_ping=True,
)

# Фабрика сессий
async_session_maker = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

Base = declarative_base()

async def get_db() -> AsyncSession:
    """Dependency для FastAPI (понадобится позже)"""
    async with async_session_maker() as session:
        yield session