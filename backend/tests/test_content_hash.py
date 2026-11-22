from app.services.content_hash import compute_content_hash


def test_identical_content_same_hash():
    h1 = compute_content_hash(".md", b"hello world")
    h2 = compute_content_hash(".md", b"hello world")
    assert h1 == h2


def test_different_content_different_hash():
    h1 = compute_content_hash(".md", b"hello")
    h2 = compute_content_hash(".md", b"world")
    assert h1 != h2


def test_same_content_different_type_different_hash():
    h1 = compute_content_hash(".md", b"same")
    h2 = compute_content_hash(".txt", b"same")
    assert h1 != h2


def test_hash_is_hex_sha256():
    h = compute_content_hash(".md", b"x")
    assert len(h) == 64
    assert all(c in "0123456789abcdef" for c in h)