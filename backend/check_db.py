import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings


async def main():
    print(f"DATABASE_URL: {settings.DATABASE_URL}")
    engine = create_async_engine(settings.DATABASE_URL)
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT count(*) FROM chunks"))
            print(f"✅ Connection successful, chunks: {result.scalar()}")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await engine.dispose()


asyncio.run(main())