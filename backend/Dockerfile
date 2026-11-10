FROM python:3.11-slim

WORKDIR /app

# Копируем исполняемый файл uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Указываем uv использовать индекс с CPU-версиями PyTorch
ENV UV_EXTRA_INDEX_URL=https://download.pytorch.org/whl/cpu

# Добавляем bin-папку виртуального окружения в PATH
ENV PATH="/app/.venv/bin:$PATH"

# Копируем файлы, необходимые hatchling для сборки пакета и установки зависимостей
COPY pyproject.toml uv.lock* README.md ./
COPY app ./app

# Устанавливаем зависимости
RUN uv sync --all-extras --no-dev --python /usr/local/bin/python3

# Копируем остальной код (тесты, скрипты, конфиги и т.д.)
COPY . .

# Запускаем сервер
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]