FROM python:3.11-slim

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

ENV UV_LINK_MODE=copy \
    UV_PYTHON=/usr/local/bin/python3 \
    UV_PYTHON_DOWNLOADS=never \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

# ── Слой 1: только зависимости ─────────────────────────────
# Копируем ТОЛЬКО манифесты. Код сюда не попадает,
# поэтому правка .py не инвалидирует тяжёлый слой с torch.
COPY pyproject.toml uv.lock README.md ./

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --all-extras --no-dev --no-install-project --frozen

# ── Слой 2: код проекта ────────────────────────────────────
COPY . .

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --all-extras --no-dev --frozen

# uvicorn берётся из /app/.venv/bin (PATH выше).
# Никакого `uv run` — окружение уже готово на этапе сборки.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]