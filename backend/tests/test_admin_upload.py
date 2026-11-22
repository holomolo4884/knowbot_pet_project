import asyncio
from io import BytesIO
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.core.database import get_db
from app.main import app


@pytest.fixture
def client():
    # NullPool: соединение живёт только внутри одного запроса,
    # иначе пул переиспользует connection из закрытого loop TestClient
    test_engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
    session_factory = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def cleanup_test_docs():
    yield

    async def _clean():
        eng = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
        async with eng.begin() as conn:
            await conn.execute(
                text("DELETE FROM documents WHERE source_path LIKE '/tmp/knowbot_uploads/%'")
            )
        await eng.dispose()

    asyncio.run(_clean())


def test_upload_md(client):
    # Уникальный контент: тест всегда создаёт новый документ,
    # а не возвращает осадок от предыдущих прогонов
    uniq = uuid4().hex[:8]
    content = f"# Тест {uniq}\n\nЭто тестовый документ для проверки загрузки."
    files = {"file": ("test_upload.md", BytesIO(content.encode()), "text/markdown")}
    r = client.post("/admin/documents/upload", files=files)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["was_created"] is True
    assert data["chunks"] >= 1
    assert data["file_type"] == "md"
    assert data["title"] == "test_upload"


def test_upload_unsupported(client):
    files = {"file": ("image.jpg", BytesIO(b"fake"), "image/jpeg")}
    r = client.post("/admin/documents/upload", files=files)
    assert r.status_code == 400
    assert "Неподдерживаемый формат" in r.json()["detail"]


def test_upload_idempotent(client):
    uniq = uuid4().hex[:8]
    content = f"# Идемпотентность {uniq}\n\nПовторная загрузка не создаёт дубликат."
    files = {"file": ("idem.md", BytesIO(content.encode()), "text/markdown")}

    r1 = client.post("/admin/documents/upload", files=files)
    assert r1.status_code == 200, r1.text
    first = r1.json()
    assert first["was_created"] is True

    r2 = client.post("/admin/documents/upload", files=files)
    assert r2.status_code == 200, r2.text
    second = r2.json()
    assert second["doc_id"] == first["doc_id"]
    assert second["was_created"] is False