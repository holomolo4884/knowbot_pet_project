# 📋 План проекта KnowBot: RAG-система по базе знаний

## 🗺️ Дорожная карта (6 недель)

| Неделя | Фокус | Результат |
|--------|-------|-----------|
| 1 | Ядро: парсинг + pgvector + базовый RAG | Рабочий MVP локально |
| 2 | Качество: citations + guardrails + eval-набор | Измеримое качество |
| 3 | Retrieval: hybrid search + reranker | +15–25% к метрикам |
| 4 | Продвинутый RAG: HyDE + multi-query + Langfuse | Observability |
| 5 | Production: auth + incremental indexing | Готово к демо |
| 6 | Упаковка: CI/CD + README + видео | Портфолио-готово |

---

## 🎯 Этап 0: Подготовка и окружение

### Что изучить
- [ ] Docker и Docker Compose (официальный tutorial, 2–3 часа)
- [ ] Основы PostgreSQL (SELECT, JOIN, индексы — если не знаешь)
- [ ] Git flow: ветки, PR, .gitignore
- [ ] Python virtual environments (`venv` или `uv`)

### Что сделать
- [ ] Создать репозиторий на GitHub: `knowbot`
- [ ] Структура проекта:
  ```
  knowbot/
  ├── backend/          # FastAPI
  ├── frontend/         # Streamlit или Next.js
  ├── data/             # документы для тестов
  ├── eval/             # тестовые Q&A пары
  ├── docker-compose.yml
  ├── Dockerfile.backend
  ├── Dockerfile.frontend
  └── README.md
  ```
- [ ] Настроить `docker-compose.yml` с сервисами: `postgres` (с pgvector), `backend`, `frontend`
- [ ] Подключить `.env` для секретов (API-ключи OpenAI и т.п.)
- [ ] Настроить pre-commit hooks (optional: `ruff`, `black`, `mypy`)

### Критерий готовности
Проект клонируется, `docker compose up` поднимает пустой Postgres с pgvector.

---

## 📄 Этап 1: Парсинг документов

### Что изучить
- [ ] Форматы: PDF, DOCX, Markdown — как устроены внутри
- [ ] Библиотеки: `PyMuPDF` (быстрый PDF), `python-docx`, `markdown-it-py`
- [ ] Концепция **document structure**: заголовки → секции → параграфы
- [ ] Альтернатива: `unstructured.io` (если хочется production-grade парсер)

### Что сделать
- [ ] Собрать 3–5 тестовых документов (PDF-регламенты, политики компании)
  - Публичные источники: GDPR, ISO 27001, политики крупных компаний
  - Или сгенерировать синтетику через LLM
- [ ] Написать парсер, который:
  - Извлекает текст **с сохранением иерархии заголовков**
  - Для каждого фрагмента сохраняет: `doc_id`, `title`, `section_path`, `page_number`
  - Возвращает структурированный JSON
- [ ] Добавить CLI-команду `python -m knowbot.ingest ./data/` для загрузки
- [ ] Написать unit-тесты на парсинг (хотя бы 3 кейса)

### Критерий готовности
Парсер превращает PDF в список чанков с метаданными. Заголовки не теряются.

---

## 🧩 Этап 2: Chunking стратегия

### Что изучить
- [ ] Почему naive chunking (`RecursiveCharacterTextSplitter`) плох: рвёт смысл
- [ ] Стратегии: **semantic chunking**, **hierarchical chunking**, **parent-child retrieval**
- [ ] Размер чанка: 512 vs 1024 vs 2048 токенов — trade-offs
- [ ] Overlap между чанками (обычно 10–20%)
- [ ] **Markdown-aware chunking** (через заголовки) — то, что нам нужно

### Что сделать
- [ ] Реализовать chunking по секциям документа (на основе заголовков из Этапа 1)
- [ ] Каждый чанк = `{text, metadata: {doc_id, section_path, page, chunk_id}}`
- [ ] Добавить fallback: если секция > 1500 токенов — разбить по параграфам с overlap
- [ ] Сохранять **parent chunk** (большой) и **child chunks** (маленькие) — для parent-child retrieval
- [ ] Посчитать статистику: сколько чанков, средний размер, распределение

### Критерий готовности
Чанки осмысленные (не обрывают предложение), метаданные полные.

---

## 🗄️ Этап 3: Векторная БД (pgvector)

### Что изучить
- [ ] pgvector: установка, типы данных (`vector`, `halfvec`)
- [ ] Индексы: `ivfflat` vs `hnsw` (hnsw быстрее для поиска)
- [ ] Метрики расстояния: L2, cosine, inner product — что выбрать (cosine для embeddings)
- [ ] SQL-фильтры по метаданным — **главное преимущество pgvector перед Chroma**
- [ ] Миграции: `alembic` или `sqlalchemy` + `pgvector` extension

### Что сделать
- [ ] Поднять Postgres 16 + pgvector в docker-compose
- [ ] Создать схему БД:
  ```sql
  CREATE TABLE documents (
      id UUID PRIMARY KEY,
      title TEXT,
      source_path TEXT,
      created_at TIMESTAMP
  );

  CREATE TABLE chunks (
      id UUID PRIMARY KEY,
      document_id UUID REFERENCES documents(id),
      text TEXT,
      embedding vector(1024),  -- под размер модели
      metadata JSONB,          -- section_path, page, chunk_id
      created_at TIMESTAMP
  );

  CREATE INDEX ON chunks USING hnsw (embedding vector_cosine_ops);
  CREATE INDEX ON chunks USING gin (metadata);
  ```
- [ ] Написать DAO-слой: `insert_chunks()`, `search(query_embedding, top_k, filters)`
- [ ] Реализовать **фильтрацию по метаданным** через SQL (`WHERE metadata @> '{"doc_id": "..."}'`)
- [ ] Написать тесты на вставку и поиск

### Критерий готовности
Чанки сохраняются, поиск по вектору + фильтрация по метаданным работают.

---

## 🔢 Этап 4: Embeddings модель

### Что изучить
- [ ] Как работают embeddings (conceptual: 3Blue1Brown видео, 30 мин)
- [ ] Модели: OpenAI `text-embedding-3-small` vs `intfloat/multilingual-e5-large` vs `BAAI/bge-m3`
- [ ] Локальные модели: `sentence-transformers`, `transformers` library
- [ ] Dimensionality: 1024 vs 1536 vs 3072 — trade-off качество/скорость/стоимость
- [ ] **Batching** embeddings — чтобы не дёргать API на каждый чанк

### Что сделать
- [ ] Выбрать модель (рекомендую `multilingual-e5-large` локально — бесплатно, хорошо для RU/EN)
- [ ] Обернуть в класс `EmbeddingService` с интерфейсом `embed(texts: list[str]) -> list[list[float]]`
- [ ] Добавить batching (по 32–64 текста за запрос)
- [ ] Добавить кэширование (по хешу текста) — чтобы не пересчитывать
- [ ] Интегрировать в ingestion pipeline: парсинг → chunking → embedding → pgvector

### Критерий готовности
`python -m knowbot.ingest ./data/` полностью работает: от PDF до записи в pgvector.

---

## 🔍 Этап 5: Retrieval pipeline (базовый)

### Что изучить
- [ ] Cosine similarity vs dot product (когда что использовать)
- [ ] Top-K retrieval: сколько чанков брать (обычно 5–10)
- [ ] Query preprocessing: нормализация, удаление стоп-слов (осторожно — не всегда помогает)
- [ ] Проблема: "query-document mismatch" — пользователь и LLM формулируют по-разному

### Что сделать
- [ ] Реализовать `Retriever.search(query: str, top_k: int, filters: dict) -> list[Chunk]`
- [ ] Внутренний пайплайн:
  1. Заэмбеддить query
  2. Выполнить векторный поиск в pgvector
  3. Применить фильтры по метаданным (если есть)
  4. Вернуть top-K чанков с метаданными
- [ ] Добавить **query logging**: каждый запрос пишется в отдельную таблицу для анализа
- [ ] Написать тесты с известными Q&A парами

### Критерий готовности
На 20 тестовых вопросах retriever находит релевантные чанки (проверить руками).

---

## 🤖 Этап 6: LLM генерация + Prompt Engineering

### Что изучить
- [ ] Prompt engineering: role, context, instruction, output format
- [ ] Temperature, top_p, max_tokens — что на что влияет
- [ ] Модели: GPT-4o-mini (дешево/быстро), GPT-4o (качество), Qwen3 (локально/альтернатива)
- [ ] **Structured output** (JSON mode) — для парсинга ответа
- [ ] Streaming ответов (SSE) — UX-плюс

### Что сделать
- [ ] Написать системный промпт:
  ```
  Ты — ассистент по внутренней базе знаний компании.
  Отвечай ТОЛЬКО на основе предоставленного контекста.
  Если ответа нет в контексте — честно скажи "Не знаю".
  Используй цитаты [1], [2] со ссылками на источники.
  ```
- [ ] Реализовать `LLMService.generate(query, context_chunks) -> Answer`
- [ ] Формат ответа: `{answer: str, citations: list[{chunk_id, doc_id, section, page}]}`
- [ ] Добавить streaming через SSE (FastAPI `StreamingResponse`)
- [ ] Добавить retry logic + fallback на другую модель при ошибке

### Критерий готовности
На тестовых вопросах LLM даёт ответы со ссылками на источники.

---

## 🛡️ Этап 7: Citations и Guardrails

### Что изучить
- [ ] Grounded generation — как заставить LLM цитировать
- [ ] Hallucination detection: LLM-as-judge, NLI-модели
- [ ] Faithfulness — метрика из RAGAS
- [ ] Prompt injection — как защищаться (хотя бы базово)

### Что сделать
- [ ] В промпте явно требовать цитаты `[1]`, `[2]` с номерами чанков
- [ ] Пост-обработка: парсить ответ, извлекать цитаты, валидировать что chunk_id существует
- [ ] **Guardrail "I don't know"**: отдельный запрос к LLM — "Основан ли этот ответ на контексте?" (или проще — проверка, что все цитаты валидны)
- [ ] Добавить в UI отображение цитат: клик → раскрыть исходный фрагмент
- [ ] Добавить защиту от prompt injection (базовая: фильтр на системные инструкции в user query)

### Критерий готовности
На 20 вопросах: 0 галлюцинаций (проверяется вручную или через RAGAS faithfulness).

---

## 📊 Этап 8: Evaluation (RAGAS) — **КРИТИЧНО**

### Что изучить
- [ ] **RAGAS** — фреймворк для оценки RAG (документация, 2–3 часа)
- [ ] Метрики:
  - `faithfulness` — ответ основан на контексте?
  - `answer_relevancy` — ответ отвечает на вопрос?
  - `context_precision` — релевантные чанки в топе?
  - `context_recall` — все нужные чанки найдены?
- [ ] Как собрать eval-набор: 30–50 Q&A пар с ожидаемыми ответами и источниками
- [ ] Regression testing для LLM-систем

### Что сделать
- [ ] Собрать eval-набор: `eval/dataset.jsonl`
  ```json
  {
    "question": "Какой лимит отпуска?",
    "ground_truth": "28 рабочих дней...",
    "ground_truth_context": ["chunk_id_1", "chunk_id_2"],
    "metadata": {"doc_id": "hr_policy"}
  }
  ```
- [ ] Написать скрипт `python -m knowbot.eval.run`:
  1. Прогоняет все вопросы через RAG pipeline
  2. Считает RAGAS-метрики
  3. Сохраняет отчёт в `eval/reports/YYYY-MM-DD.json`
- [ ] Добавить скрипт сравнения двух прогонов (до/после изменения)
- [ ] Настроить CI: если метрики упали >5% — фейлить пайплайн

### Критерий готовности
Есть baseline-метрики. Можно измерять влияние каждой новой фичи.

---

## 🎨 Этап 9: UI (Streamlit)

### Что изучить
- [ ] Streamlit basics (официальный tutorial, 2 часа)
- [ ] Компоненты: `st.chat_message`, `st.chat_input`, `st.expander`
- [ ] Streaming в Streamlit (`st.write_stream`)
- [ ] Альтернатива: Chainlit (специально для чат-ботов)

### Что сделать
- [ ] Простой чат-интерфейс:
  - Поле ввода вопроса
  - Отображение ответа с цитатами
  - Раскрывающиеся блоки с источниками
- [ ] Sidebar:
  - Выбор документа / фильтрация по разделу
  - Настройки: температура, top-K
  - История чатов
- [ ] Страница `/admin`:
  - Загрузка новых документов
  - Просмотр чанков
  - Просмотр eval-метрик
- [ ] Обработка ошибок и loading-состояний

### Критерий готовности
Не-технический пользователь может задать вопрос и получить ответ с источниками.

---

## 🔀 Этап 10: Hybrid Search + Reranking — **Game Changer**

### Что изучить
- [ ] **BM25** — классический текстовый поиск (TF-IDF на стероидах)
- [ ] **Hybrid search**: комбинация vector + BM25 через RRF (Reciprocal Rank Fusion)
- [ ] **Reranking**: cross-encoder модели (`BAAI/bge-reranker-v2-m3`)
- [ ] Почему reranker даёт +15–25% к качеству (это **самый сильный single-импрувмент**)
- [ ] pgvector + `pg_search` или отдельный BM25-индекс

### Что сделать
- [ ] Добавить BM25-индекс в Postgres (через расширение `pg_search` или в памяти через `rank_bm25`)
- [ ] Реализовать hybrid retrieval:
  1. Vector search → top-20
  2. BM25 search → top-20
  3. RRF-объединение → top-10
- [ ] Добавить reranker:
  - Загрузить `bge-reranker-v2-m3` локально
  - Скорить пары (query, chunk) → пересортировать → top-5
- [ ] **Замерить RAGAS до и после** — это будет в README
- [ ] A/B-тест: старый retrieval vs новый

### Критерий готовности
Метрики RAGAS выросли минимум на 10%. В README — график сравнения.

---

## 🧠 Этап 11: Продвинутый Retrieval (HyDE + Multi-Query)

### Что изучить
- [ ] **HyDE** (Hypothetical Document Embeddings): LLM генерирует "гипотетический ответ", потом ищем по нему
- [ ] **Multi-Query Retriever**: LLM переформулирует вопрос в 3–5 вариантов, ищем по каждому
- [ ] **Parent-Child Retrieval**: ищем по маленьким чанкам, возвращаем большие (контекст)
- [ ] Когда что применять (HyDE — для неточных вопросов, Multi-Query — для сложных)

### Что сделать
- [ ] Реализовать HyDE:
  ```python
  hypothetical_answer = llm.generate(f"Ответь на вопрос: {query}")
  results = retriever.search(hypothetical_answer)
  ```
- [ ] Реализовать Multi-Query:
  ```python
  variants = llm.generate(f"Переформулируй вопрос 3 способами: {query}")
  results = merge_and_dedupe([retriever.search(v) for v in variants])
  ```
- [ ] Добавить переключатель в UI / настройках
- [ ] Замерить метрики на разных типах вопросов (фактологические, сравнительные, "как")

### Критерий готовности
Есть 3 режима retrieval, можно переключать. Метрики задокументированы.

---

## 👁️ Этап 12: Observability (Langfuse)

### Что изучить
- [ ] **Langfuse** — open-source LLM observability (документация, 2 часа)
- [ ] Что трейсить: latency, tokens, cost, retrieval quality, user feedback
- [ ] Альтернативы: Arize Phoenix, LangSmith (платный)

### Что сделать
- [ ] Поднять Langfuse self-hosted в docker-compose
- [ ] Обернуть каждый вызов LLM / retriever в трейс:
  ```python
  @observe
  def retrieve(query): ...

  @observe
  def generate(query, context): ...
  ```
- [ ] Добавить user feedback: 👍/👎 в UI → пишется в Langfuse
- [ ] Настроить алерты: если latency > 10s или error rate > 5%
- [ ] Раз в неделю смотреть дашборд: какие вопросы не answered, какие чанки не используются

### Критерий готовности
В Langfuse видны все запросы, можно найти проблемные кейсы.

---

## 🔐 Этап 13: Auth + Multi-tenancy

### Что изучить
- [ ] JWT-аутентификация в FastAPI
- [ ] RBAC (Role-Based Access Control)
- [ ] Multi-tenancy: как изолировать данные пользователей
- [ ] Row-Level Security (RLS) в PostgreSQL — элегантно для pgvector

### Что сделать
- [ ] Добавить эндпоинты `/auth/register`, `/auth/login`
- [ ] Реализовать роли: `admin`, `user`, `viewer`
- [ ] В таблице `chunks` добавить поле `tenant_id` / `allowed_roles`
- [ ] Retriever применяет фильтр: `WHERE tenant_id = current_user.tenant_id`
- [ ] Админ может загружать документы, пользователь — только спрашивать
- [ ] Написать тесты на изоляцию данных

### Критерий готовности
Два пользователя с разными ролями видят разные документы.

---

## 🔄 Этап 14: Incremental Indexing

### Что изучить
- [ ] Хеш-функции: SHA-256 для детекции изменений
- [ ] Инкрементальные обновления vs полная переиндексация
- [ ] Soft delete + tombstones в векторных БД

### Что сделать
- [ ] При ingestion считать хеш каждого чанка
- [ ] Перед вставкой: сравнить с существующими
  - Новый хеш → INSERT
  - Изменился → UPDATE
  - Исчез → soft DELETE (или физический)
- [ ] Добавить CLI: `python -m knowbot.ingest --incremental ./data/`
- [ ] Логировать: сколько чанков добавлено/обновлено/удалено

### Критерий готовности
Повторный запуск ingestion не дублирует чанки.

---

## 🚀 Этап 15: CI/CD и Деплой

### Что изучить
- [ ] GitHub Actions: workflows, secrets, caching
- [ ] Docker multi-stage builds (для уменьшения размера образа)
- [ ] Деплой-платформы: Railway, Render, Fly.io, или свой VPS
- [ ] Health checks и graceful shutdown

### Что сделать
- [ ] Настроить GitHub Actions:
  ```yaml
  on: [push, pull_request]
  jobs:
    test:
      - install deps
      - run pytest
      - run eval (на маленьком наборе)
      - fail if metrics dropped
    build:
      - docker build
      - docker push
  ```
- [ ] Написать `Makefile` с командами: `make dev`, `make test`, `make eval`, `make deploy`
- [ ] Задеплоить на Railway/Render (бесплатный tier)
- [ ] Настроить health check: `/health` возвращает `{status: "ok", db: "connected"}`

### Критерий готовности
`git push` → автотесты → деплой. Публичный URL работает.

---

## 📦 Этап 16: Упаковка (README + Демо)

### Что изучить
- [ ] Как писать хорошие README (шаблоны: `awesome-readme`, `readme-so`)
- [ ] Запись демо-видео (Loom, OBS)
- [ ] GIF-ки из видео (через `gifski` или онлайн-сервисы)

### Что сделать
- [ ] README со структурой:
  - 🎯 Какую проблему решает (1 абзац)
  - 🎥 GIF-дема (30 секунд)
  - 🏗️ Архитектурная схема (draw.io или Excalidraw)
  - 📊 Метрики RAGAS (таблица: до/после каждой фичи)
  - 🚀 Quick start (`docker compose up`)
  - 🧪 Как запустить eval
  - 📝 Known limitations
  - 🔮 Future work
- [ ] Записать демо-видео (2–3 минуты):
  - Загрузка документа
  - Вопрос → ответ с цитатами
  - Сравнение retrieval-режимов
  - Дашборд Langfuse
- [ ] Залить на GitHub, добавить в LinkedIn / резюме

### Критерий готовности
README можно показать на собеседовании. Видео — приложить к отклику.

---

## 📚 Сводный список ресурсов для изучения

### Обязательно (по приоритету)
1. **RAG-техники**: [LLM Bootcamp 2024 — RAG lecture](https://llmbootcamp.com/) (YouTube, 1 час)
2. **pgvector**: [официальный репо](https://github.com/pgvector/pgvector) + [статья на Habr](https://habr.com/ru/articles/763452/)
3. **RAGAS**: [документация](https://docs.ragas.io/) + примеры
4. **Reranking**: [статья про cross-encoders](https://www.sbert.net/examples/applications/cross-encoder/README.html)
5. **Langfuse**: [документация](https://langfuse.com/docs)
6. **FastAPI**: [официальный tutorial](https://fastapi.tiangolo.com/tutorial/)

### Дополнительно (если есть время)
- Курс [DeepLearning.AI — Building and Evaluating Advanced RAG](https://www.deeplearning.ai/short-courses/) (3 часа)
- Книга "Retrieval-Augmented Generation" — если найдёшь
- Блог [Lilian Weng](https://lilianweng.github.io/) — статьи про RAG

---

## ✅ Чек-лист "Проект готов"

- [ ] README с метриками и демо
- [ ] Docker compose up → всё работает
- [ ] Eval-набор из 30+ вопросов, метрики задокументированы
- [ ] Hybrid search + reranker дают +10% к baseline
- [ ] Langfuse показывает трейсы
- [ ] CI/CD работает
- [ ] Задеплоено на публичный URL
- [ ] Записано демо-видео

---

## 💡 Советы напоследок

1. **Не пытайся сделать всё сразу.** MVP за 2 недели → потом итерации.
2. **Метрики — это главное.** Без RAGAS ты слеп. Замеряй до/после каждой фичи.
3. **Reranker — это магия.** Если сделаешь только одно улучшение — делай reranker.
4. **Citations обязательны.** Без них RAG = чёрный ящик, никто не доверит.
5. **Документация > код.** Хороший README продаёт проект лучше, чем идеальная архитектура.
6. **Показывай прогресс.** Посты в LinkedIn/Twitter "неделя 3: добавил reranker, метрики выросли на 18%" — это работает.

---

Хочешь, я детально распишу **любой конкретный этап**? Например:
- 📐 Точную схему БД с SQL-миграциями
- 🧪 Структуру eval-набора и скрипт RAGAS
- 🔄 Код hybrid search + reranker
- 🏗️ Архитектурную схему в draw.io-формате

Что развить дальше?