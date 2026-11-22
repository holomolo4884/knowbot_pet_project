import hashlib


def compute_content_hash(file_type: str, content: bytes) -> str:
    """SHA256(file_type + ':' + content).

    Идентичные файлы (даже с разными именами) дают одинаковый хеш.
    Добавление типа в префикс защищает от коллизий между .md и .txt
    с одинаковым контентом.
    """
    h = hashlib.sha256()
    h.update(file_type.encode("utf-8"))
    h.update(b":")
    h.update(content)
    return h.hexdigest()