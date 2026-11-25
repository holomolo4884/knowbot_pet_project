# KnowBot — grounded RAG-ассистент по внутренней базе знаний

Чат-бот, который отвечает **только по загруженным документам**, со ссылками на конкретные фрагменты, и **отказывается отвечать**, когда в базе нет информации. Полный цикл: парсинг MD/DOCX/PDF → чанкинг → эмбеддинги → векторный поиск → генерация с цитатами → стриминг в UI → админ-панель с управлением документами → измеренное качество на eval-наборе из 40 вопросов.

---

## Возможности

- **Grounded-генерация**: каждый факт в ответе помечен маркером `[N]`, кликабельным в UI и ведущим к исходному фрагменту
- **Двухслойная защита от галлюцинаций**: порог релевантности + grounding-промпт; система умеет сказать «не знаю»
- **SSE-стриминг** с индикатором фаз (поиск → чтение фрагментов → генерация) и метриками прямо под ответом
- **Идемпотентная загрузка**: SHA256-хеш контента — повторная загрузка того же файла не создаёт дубликат (18 мс вместо полной переиндексации)
- **Админ-панель**: drag-and-drop загрузка с прогрессом по фазам, список документов, inline-переименование, переиндексация текущим парсером, каскадное удаление
- **Измеренное качество**: eval-набор из 40 вопросов, 5 категорий, 4 метрики, отчёт в Markdown

---

## Архитектура

```mermaid
flowchart LR
    U[Пользователь] -->|вопрос| FE[Frontend<br/>Next.js 16]
    FE -->|POST /chat/stream<br/>SSE| BE[Backend<br/>FastAPI]
    BE -->|эмбеддинг запроса| EM[multilingual-e5-large<br/>1024 dim]
    BE -->|cosine search| PG[(PostgreSQL 16<br/>+ pgvector, HNSW)]
    BE -->|контекст + промпт| LLM[LiteAI proxy<br/>gemini-3.8-flash]
    LLM -->|поток токенов| BE
    BE -->|SSE: delta / citations / meta| FE
    AD[Админ UI] -->|upload, SSE-прогресс| BE
    BE -->|парсинг + эмбеддинги| PG
    BE -->|исходники| FS[data/uploads/<br/>по content_hash]
```

### Стек

| Слой | Технологии |
|---|---|
| Backend | Python 3.11, FastAPI, SQLAlchemy 2.0 (async), asyncpg, pgvector, loguru, uv |
| Парсинг | PyMuPDF (PDF), python-docx (DOCX), собственный Markdown-парсер |
| Embeddings | `intfloat/multilingual-e5-large` (1024 dim), sentence-transformers |
| LLM | `gemini-3.8-flash` через OpenAI-совместимый прокси LiteAI (выбран по замеру TTFT) |
| Frontend | Next.js 16 (Turbopack), TypeScript, Tailwind, react-markdown, собственный SSE-клиент |
| Инфраструктура | Docker Compose, PostgreSQL 16 + pgvector, Node 22 |

---

## Быстрый старт

```bash
# 1. Поднять инфраструктуру
docker compose up -d --build

# 2. Залить стартовые документы (MD/DOCX/PDF из data/docs)
cd backend
uv run python -m app.ingestion ingest ../data/docs --db

# 3. Открыть UI
#    Чат:        http://localhost:3000
#    Загрузка:   http://localhost:3000/admin/upload
#    Документы:  http://localhost:3000/admin/documents
```

Переменные окружения (`backend/.env` + `environment` в compose):

```bash
DATABASE_URL=postgresql+asyncpg://knowbot:knowbot@localhost:5433/knowbot
OPENAI_API_KEY=<ключ LiteAI>
LLM_MODEL=gemini-3.8-flash
MIN_RELEVANCE_SCORE=0.78
UPLOAD_DIR=/app/data/uploads      # в контейнере
DOCS_DIR=/app/data/docs           # в контейнере
HF_HUB_OFFLINE=1                  # модель из кэша: cold start 2.6 с
```

---

## Структура проекта

```
knowbot_pet_project/
├── backend/
│   ├── app/
│   │   ├── admin/            # CRUD документов: router + schemas
│   │   ├── core/             # config, database
│   │   ├── ingestion/        # парсеры md/docx/pdf, CLI ingest
│   │   ├── models/           # SQLAlchemy: Document, Chunk
│   │   ├── repositories/     # DocumentRepository (upsert по хешу)
│   │   ├── retrieval/        # retriever, context_filter, calibrate, eval
│   │   └── services/         # llm, embedding, rag, prompt, citations, stream
│   ├── tests/                # 65 тестов
│   └── migrations/           # SQL-миграции
├── frontend/
│   ├── app/                  # /, /admin/upload, /admin/documents
│   ├── components/           # chat/, admin/
│   ├── hooks/                # use-chat-stream, use-upload
│   └── lib/                  # sse-parser (generic), chat-api, upload-api, types
├── data/
│   ├── docs/                 # исходные документы
│   └── uploads/              # постоянное хранилище: {content_hash}{ext}
├── docker/init.sql           # схема + расширение vector (идемпотентно)
├── eval/
│   ├── eval_set.json         # 40 вопросов, 5 категорий
│   ├── eval_report.md        # сгенерированный отчёт
│   └── eval_raw.json         # сырые результаты прогонов
└── docker-compose.yml
```

---

## API

### Чат

| Метод | Путь | Описание |
|---|---|---|
| POST | `/chat` | Синхронный ответ с цитатами |
| POST | `/chat/stream` | SSE-стрим: retrieval → delta* → citations → meta → done |
| GET | `/health` | Статус + число проиндексированных чанков |

### SSE-протокол чата

| Событие | Payload | Когда |
|---|---|---|
| `retrieval` | `hits`, `context_hits`, `best_score`, `took_ms` | сразу после поиска (~100–300 мс) |
| `delta` | `text` | фрагмент ответа; маркеры `[N]` приходят целыми |
| `citations` | `items[]` с title, section_path, page_number, score | после генерации |
| `meta` | `grounded`, `abstained`, `invalid_citation_markers`, `retrieval_ms`, `ttft_ms`, `generation_ms`, `model` | финал |
| `error` / `done` | — | завершение потока |

### Админка

| Метод | Путь | Описание |
|---|---|---|
| GET | `/admin/documents` | список: чанки, размер, дата, флаг `stored` |
| POST | `/admin/documents/upload` | multipart; `force`, `title` |
| POST | `/admin/documents/upload/stream` | то же с SSE-прогрессом по фазам |
| PATCH | `/admin/documents/{id}` | переименование |
| DELETE | `/admin/documents/{id}` | каскадно чанки + файл из хранилища |
| POST | `/admin/documents/{id}/reindex` | пересборка текущим парсером; `doc_id` и титул сохраняются |

---

## Guardrails: двухслойная защита от галлюцинаций

**Слой 1 — порог релевантности** (`MIN_RELEVANCE_SCORE=0.78`). Если лучший score ниже, LLM не вызывается вовсе.

**Слой 2 — grounding-промпт**. Если контекст не содержит ответа, модель обязана вернуть каноническую фразу отказа. Маркеры `[N]` сверх числа фрагментов в контексте вырезаются потоковым фильтром.

Два пути отказа различимы в `meta` — это осознанный дизайн:

| Путь | Триггер | Подпись в meta |
|---|---|---|
| Порог | `best_score < 0.78` | `model: none`, `generation_ms: 0` |
| Grounding-промпт | ответа нет в контексте | `model: gemini-3.8-flash`, `generation_ms > 0`, `abstained: true` |

### Почему порог не один

Замер на реальном корпусе показал: у `multilingual-e5-large` диапазон cosine similarity сжат — на агрегационном запросе разница между релевантным и мусорным чанком составила **0.003**, а топ-1 прошёл порог с зазором **0.0005**. Один глобальный порог в таких условиях либо режет валидные вопросы, либо пропускает шум.

Поэтому решения разделены:
- **абсолютный floor** — «отвечать ли вообще» (отсекает off-topic);
- **`select_context`** — относительный разрыв в score внутри топ-K решает, какие фрагменты дать модели. Плотный кластер отдаётся целиком, чистый разрыв режется точно.

---

## Retrieval: чанкинг и ранжирование

- **Markdown-парсер**: иерархия заголовков ведётся стеком уровней (соседи одного уровня замещают, а не вкладываются); строки целиком из `**bold**` трактуются как псевдо-заголовки; секции длиннее 1200 символов режутся с перекрытием 150.
- **DOCX**: заголовок из стиля Title, иерархия из Heading 1–3.
- **PDF**: посстраничные чанки с `page_number` в метаданных.
- **Индекс**: pgvector, HNSW, cosine distance.

Эффект гранулярности, измеренный на реальном документе: 4 чанка по ~3000 символов давали score 0.78–0.80 на целевые вопросы; 28 чанков по 143–601 символ — 0.83–0.84. **Разбавленный вектор — главная причина ложных отказов.**

---

## Evaluation

Набор: `eval/eval_set.json`, 40 вопросов, 5 категорий. Запуск: `uv run python -m app.retrieval.eval_full`. Отчёт: `eval/eval_report.md`.

| Категория | Кол-во | Что проверяет |
|---|---|---|
| fact | 10 | базовый retrieval: нужный чанк найден |
| aggregate | 8 | multi-hop: данные из 2+ источников |
| paraphrase | 8 | семантика без лексического совпадения |
| trap | 6 | вопрос есть в базе, ответа нет → отказ от LLM |
| off-topic | 8 | вне базы → отказ от порога |

**Результаты последнего прогона:**

| Метрика | Значение | Цель |
|---|---|---|
| retrieval_hit | **88.5%** (23/26) | ≥ 85% |
| false_abstention | **0.0%** (0/26) | ≤ 5% |
| grounding_accuracy | **100%** (14/14) | ≥ 95% |
| citation_validity | **100%** (24/24) | ≥ 95% |

Калибровка порога: `uv run python -m app.retrieval.calibrate` — 17 вопросов, расчёт зазора между классами и метрика false abstention.

---

## Performance: всё измерено

### Выбор LLM по замеру TTFT (идентичный контекст, 5 чанков)

| Модель | TTFT | Total | Стрим |
|---|---|---|---|
| **gemini-3.8-flash** | 4 092 мс | 4 249 мс | 157 мс |
| gpt-5.6-sol | 9 214 мс | 9 464 мс | 250 мс |
| claude-haiku-4-5 | 21 722 мс | 21 971 мс | 249 мс |
| qwen3.7-flash | пустой стрим | — | — |

Выводы:
- **97% латентности — ожидание первого токена**; стриминг занимает 150–250 мс независимо от модели. Оптимизировать поиск бессмысленно (retrieval 90–300 мс, ~1.6% общего времени).
- Название категории не гарантирует скорость: «haiku» в поколении 4.5 оказался reasoning-моделью с TTFT 21.7 с.
- Прокси буферизует ответ целиком, поэтому UI проектировался с фазовыми индикаторами, а не с расчётом на постепенную печать.

### Инфраструктурные цифры

| Показатель | Было | Стало |
|---|---|---|
| Сборка backend-образа | 5 243 с | **54 с** (cache mount + слой зависимостей) |
| Cold start API | ~40 с | **2.6 с** (`HF_HUB_OFFLINE`, прогрев в lifespan) |
| Повторная загрузка того же файла | полная переиндексация | **18 мс** (content_hash) |

---

## Тесты

```bash
cd backend
uv run pytest tests/ -v        # 65 тестов
```

Покрытие: парсеры (иерархия, псевдо-заголовки, разбиение), content_hash, citation-валидатор, потоковый фильтр цитат (16 кейсов разрыва маркера), context_filter на реальных профилях score, guardrails, идемпотентность загрузки, CRUD админки.

---

## Lessons learned

1. **Модель выбирают замером, не названием.** Бенчмарк TTFT на идентичном контексте дал ускорение в 2.25× и выявил reasoning-модель под маркой «fast».
2. **Порог, откалиброванный на одном корпусе, не переносится на другой.** Зазор on/off-topic схлопнулся с 0.049 до 0.004 после добавления реального документа.
3. **Гранулярность чанков определяет score.** Недельные блоки по 3000 символов усредняли десятки тем в одном векторе и резали валидные вопросы.
4. **Тесты не удаляют данные по широкому предикату.** Cleanup-фикстура с маской `source_path LIKE '/tmp/%'` уничтожила 4 пользовательских документа. Правильный паттерн — реестр созданных id; приёмка — неизменность `count(*)` до и после прогона.
5. **Метки eval-набора зависят от корпуса.** «Как настроить Kubernetes» был off-topic для HR-документов и стал релевантным после загрузки технического резюме.
6. **Docker: зависимости в образе, код в volume.** После любого `uv add` образ пересобирается, иначе контейнер падает с `ModuleNotFoundError` при живом локальном окружении.
7. **`POSTGRES_USER` заменяет суперпользователя.** Роль `postgres` в таком контейнере не существует — диагностика начинается с `env | grep POSTGRES_USER`.
8. **Async-тесты и пул соединений несовместимы с TestClient.** Каждый запрос создаёт новый event loop; глобальный пул подсовывает соединение из закрытого loop. Решение — `NullPool` через `dependency_overrides`.

---

## Known limitations

- **Агрегация через весь документ** («сколько часов в неделю») требует multi-hop retrieval: топ-5 чанков не собирает данные из 7+ источников (eval-вопрос 17).
- **Парафразы с низким лексическим совпадением** могут не пройти порог (eval-вопрос 23).
- **Нет аутентификации** — админка открыта (этап 7 в роадмапе).
- **Провайдер буферизует стрим** — выигрыш стриминга в perceived latency отсутствует, компенсируется фазовыми индикаторами.

## Roadmap

- **Этап 10**: BM25 + cross-encoder reranker (hybrid search, RRF-fusion) — eval-базлайн Этапа 8 позволит измерить прирост, а не предполагать его.
- **Этап 7**: аутентификация и изоляция документов по пользователям.
- История диалогов и сессии.

---

## Troubleshooting

| Симптом | Причина и решение |
|---|---|
| `role "postgres" does not exist` | Суперпользователь — значение `POSTGRES_USER`; подключаться под ним |
| `Form data requires "python-multipart"` | Зависимость добавлена после сборки образа → `docker compose build backend` |
| `Not an executable object: 'SELECT 1'` | SQLAlchemy 2.0: обернуть строку в `text()` |
| `Future attached to a different loop` | Пул соединений переживает event loop → `NullPool` в тестах |
| `role "knowbot" does not exist` при ingest | Локальный Postgres на 5432 перехватывает подключение; Docker проброшен на 5433 |

---

## Автор

Владислав Гончаров — pet-проект для портфолио: RAG полного цикла с измеренным качеством.