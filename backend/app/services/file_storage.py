from pathlib import Path

from loguru import logger

from app.core.config import settings


def upload_dir() -> Path:
    path = Path(settings.UPLOAD_DIR)
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_upload(content_hash: str, ext: str, content: bytes) -> Path:
    """Сохраняет файл под именем контент-хеша. Идемпотентно."""
    path = upload_dir() / f"{content_hash}{ext}"
    path.write_bytes(content)
    logger.debug(f"Stored upload: {path.name} ({len(content)} bytes)")
    return path


def is_managed(path: str | None) -> bool:
    """True, если файл лежит в нашем хранилище.

    Нужно, чтобы удаление документа не тронуло исходники пользователя
    в data/docs, загруженные через CLI.
    """
    if not path:
        return False
    try:
        return Path(path).resolve().is_relative_to(upload_dir().resolve())
    except (ValueError, OSError):
        return False


def delete_upload(path: str | None) -> bool:
    if not is_managed(path):
        return False
    target = Path(path)
    target.unlink(missing_ok=True)
    logger.info(f"Deleted upload: {target.name}")
    return True


def docs_dir() -> Path:
    return Path(settings.DOCS_DIR)


def resolve_source(source_path: str | None) -> Path | None:
    """Находит файл независимо от того, в каком окружении сохранён путь.

    Порядок: сохранённый путь -> наше хранилище по имени -> каталог docs по имени.
    Решает проблему разных CWD у контейнера (/app) и хоста (backend/).
    """
    if not source_path:
        return None
    original = Path(source_path)
    if original.exists():
        return original
    for candidate in (upload_dir() / original.name, docs_dir() / original.name):
        if candidate.exists():
            return candidate
    return None