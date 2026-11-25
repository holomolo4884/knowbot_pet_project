import asyncio
import re
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
def created_docs() -> list[str]:
    """Реестр doc_id, созданных именно этим тестом."""
    return []


@pytest.fixture
def client():
    # NullPool: соединение живёт внутри одного запроса,
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
def cleanup_test_docs(created_docs):
    """Удаляем ТОЛЬКО документы, созданные этим тестом.

    НИКОГДА не удаляем по маске source_path: под неё попадают все
    документы, загруженные через UI, включая реальные пользовательские.
    """
    yield
    if not created_docs:
        return

    async def _clean():
        eng = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
        async with eng.begin() as conn:
            for doc_id in created_docs:
                await conn.execute(
                    text("DELETE FROM documents WHERE id = CAST(:i AS uuid)"),
                    {"i": doc_id},
                )
        await eng.dispose()

    asyncio.run(_clean())


def _doc_id_from_sse(body: str) -> str | None:
    match = re.search(r'"doc_id":\s*"([^"]+)"', body)
    return match.group(1) if match else None


def test_upload_md(client, created_docs):
    uniq = uuid4().hex[:8]
    content = f"# Тест {uniq}\n\nЭто тестовый документ для проверки загрузки."
    files = {"file": ("test_upload.md", BytesIO(content.encode()), "text/markdown")}
    r = client.post("/admin/documents/upload", files=files)
    assert r.status_code == 200, r.text
    data = r.json()
    created_docs.append(data["doc_id"])
    assert data["was_created"] is True
    assert data["chunks"] >= 1
    assert data["file_type"] == "md"
    assert data["title"] == f"Тест {uniq}"


def test_upload_title_falls_back_to_filename(client, created_docs):
    uniq = uuid4().hex[:8]
    content = f"Просто текст без заголовков {uniq}."
    files = {
        "file": (f"no_heading_{uniq}.md", BytesIO(content.encode()), "text/markdown")
    }
    r = client.post("/admin/documents/upload", files=files)
    assert r.status_code == 200, r.text
    data = r.json()
    created_docs.append(data["doc_id"])
    assert data["title"] == f"no_heading_{uniq}"


def test_upload_unsupported(client):
    files = {"file": ("image.jpg", BytesIO(b"fake"), "image/jpeg")}
    r = client.post("/admin/documents/upload", files=files)
    assert r.status_code == 400
    assert "Неподдерживаемый формат" in r.json()["detail"]


def test_upload_idempotent(client, created_docs):
    uniq = uuid4().hex[:8]
    content = f"# Идемпотентность {uniq}\n\nПовторная загрузка не создаёт дубликат."
    files = {"file": ("idem.md", BytesIO(content.encode()), "text/markdown")}

    r1 = client.post("/admin/documents/upload", files=files)
    assert r1.status_code == 200, r1.text
    first = r1.json()
    created_docs.append(first["doc_id"])
    assert first["was_created"] is True

    r2 = client.post("/admin/documents/upload", files=files)
    assert r2.status_code == 200, r2.text
    second = r2.json()
    assert second["doc_id"] == first["doc_id"]
    assert second["was_created"] is False


def test_upload_stream_events(client, created_docs):
    uniq = uuid4().hex[:8]
    content = f"# Стрим {uniq}\n\nПроверка прогресса индексации."
    files = {"file": ("stream.md", BytesIO(content.encode()), "text/markdown")}

    r = client.post("/admin/documents/upload/stream", files=files)
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("text/event-stream")

    doc_id = _doc_id_from_sse(r.text)
    assert doc_id
    created_docs.append(doc_id)

    text_body = r.text
    assert '"phase": "received"' in text_body
    assert '"phase": "parsing"' in text_body
    assert '"phase": "embedding"' in text_body
    assert '"phase": "saving"' in text_body
    assert "event: done" in text_body
    assert '"was_created": true' in text_body


def test_upload_stream_duplicate(client, created_docs):
    uniq = uuid4().hex[:8]
    content = f"# Дубль {uniq}\n\nВторой проход должен быть мгновенным."
    files = {"file": ("dup.md", BytesIO(content.encode()), "text/markdown")}

    r1 = client.post("/admin/documents/upload/stream", files=files)
    assert r1.status_code == 200
    doc_id = _doc_id_from_sse(r1.text)
    assert doc_id
    created_docs.append(doc_id)
    assert '"was_created": true' in r1.text

    r2 = client.post("/admin/documents/upload/stream", files=files)
    assert r2.status_code == 200
    assert '"phase": "duplicate"' in r2.text
    assert '"was_created": false' in r2.text


def test_upload_stream_unsupported(client):
    files = {"file": ("bad.jpg", BytesIO(b"fake"), "image/jpeg")}
    r = client.post("/admin/documents/upload/stream", files=files)
    assert r.status_code == 200
    assert "event: error" in r.text
    assert "Неподдерживаемый формат" in r.text


def test_list_documents(client, created_docs):
    uniq = uuid4().hex[:8]
    content = f"# Список {uniq}\n\nДокумент для проверки листинга."
    files = {"file": ("list.md", BytesIO(content.encode()), "text/markdown")}
    r = client.post("/admin/documents/upload", files=files)
    doc_id = r.json()["doc_id"]
    created_docs.append(doc_id)

    listing = client.get("/admin/documents")
    assert listing.status_code == 200
    item = next(d for d in listing.json() if d["doc_id"] == doc_id)
    assert item["chunks"] >= 1
    assert item["stored"] is True
    assert item["title"] == f"Список {uniq}"


def test_rename_document(client, created_docs):
    uniq = uuid4().hex[:8]
    content = f"Текст без заголовка {uniq}."
    files = {"file": (f"raw_{uniq}.md", BytesIO(content.encode()), "text/markdown")}
    doc_id = client.post("/admin/documents/upload", files=files).json()["doc_id"]
    created_docs.append(doc_id)

    r = client.patch(f"/admin/documents/{doc_id}", json={"title": "План обучения JS"})
    assert r.status_code == 200
    assert r.json()["title"] == "План обучения JS"


def test_custom_title_on_upload(client, created_docs):
    uniq = uuid4().hex[:8]
    content = f"# Заголовок из файла {uniq}\n\nТекст."
    files = {"file": ("t.md", BytesIO(content.encode()), "text/markdown")}
    r = client.post(
        "/admin/documents/upload", files=files, data={"title": "Моё название"}
    )
    assert r.status_code == 200
    created_docs.append(r.json()["doc_id"])
    assert r.json()["title"] == "Моё название"


def test_reindex_preserves_identity_and_title(client, created_docs):
    uniq = uuid4().hex[:8]
    content = f"# Реиндекс {uniq}\n\nТекст для пересборки чанков."
    files = {"file": ("re.md", BytesIO(content.encode()), "text/markdown")}
    first = client.post("/admin/documents/upload", files=files).json()
    doc_id = first["doc_id"]
    created_docs.append(doc_id)

    client.patch(f"/admin/documents/{doc_id}", json={"title": "Переименованный"})
    r = client.post(f"/admin/documents/{doc_id}/reindex")
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["doc_id"] == doc_id
    assert data["title"] == "Переименованный"
    assert data["chunks"] == first["chunks"]


def test_delete_document(client, created_docs):
    uniq = uuid4().hex[:8]
    content = f"# Удаление {uniq}\n\nВременный документ."
    files = {"file": ("del.md", BytesIO(content.encode()), "text/markdown")}
    doc_id = client.post("/admin/documents/upload", files=files).json()["doc_id"]

    r = client.delete(f"/admin/documents/{doc_id}")
    assert r.status_code == 204

    listing = client.get("/admin/documents").json()
    assert all(d["doc_id"] != doc_id for d in listing)
    created_docs.append(doc_id)  # повторное удаление идемпотентно


def test_delete_missing_returns_404(client):
    r = client.delete(f"/admin/documents/{uuid4()}")
    assert r.status_code == 404