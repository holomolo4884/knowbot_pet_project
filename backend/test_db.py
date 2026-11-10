import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def main():
    engine = create_async_engine(
        "postgresql+asyncpg://knowbot:knowbot@localhost:5432/knowbot",
        echo=True,
    )
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT version()"))
        print("Postgres:", result.scalar()[:50])

        result = await conn.execute(text("SELECT extname FROM pg_extension WHERE extname = 'vector'"))
        print("pgvector:", result.scalar())

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())