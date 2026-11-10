.PHONY: help sync up down logs db-shell test lint format dev frontend install-frontend

help:  ## Показать справку
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

sync:  ## Синхронизировать backend зависимости
	cd backend && uv sync --all-extras

install-frontend:  ## Установить frontend зависимости
	cd frontend && npm install

up:  ## Поднять все сервисы
	docker compose up -d

down:  ## Остановить все сервисы
	docker compose down

logs:  ## Логи всех сервисов
	docker compose logs -f

db-shell:  ## Зайти в psql
	docker compose exec postgres psql -U knowbot -d knowbot

test:  ## Запустить тесты backend
	cd backend && uv run pytest tests/ -v

lint:  ## Проверить код
	cd backend && uv run ruff check app/
	cd frontend && npm run lint

format:  ## Форматировать код
	cd backend && uv run ruff format app/
	cd frontend && npm run format

dev:  ## Запустить backend в dev-режиме (локально)
	cd backend && uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

frontend:  ## Запустить frontend в dev-режиме (локально)
	cd frontend && npm run dev

dev-all:  ## Запустить backend и frontend локально (в разных терминалах)
	@echo "Запусти в двух терминалах:"
	@echo "  Терминал 1: make dev"
	@echo "  Терминал 2: make frontend"