from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import engine, get_db
from app.retrieval.retriever import Retriever
from app.retrieval.schemas import SearchRequest, SearchResponse
from app.services.embedding_service import embedding_service
from app.core.config import settings
from app.services.rag_schemas import ChatRequest, ChatResponse
from app.services.rag_service import RAGService


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.validate_llm()
    # Прогреваем модель на старте, чтобы первый запрос не тормозил
    logger.info("Warming up embedding model...")
    embedding_service.embed_query("warmup")
    logger.info("KnowBot API ready")
    yield
    await engine.dispose()


app = FastAPI(
    title="KnowBot API",
    description="RAG-система для поиска по базе знаний компании",
    version="0.3.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health(db: AsyncSession = Depends(get_db)):
    result = await db.execute(text("SELECT count(*) FROM chunks"))
    return {"status": "ok", "chunks_indexed": result.scalar()}


@app.post("/search", response_model=SearchResponse)
async def search(payload: SearchRequest, db: AsyncSession = Depends(get_db)):
    retriever = Retriever(db)
    results, took_ms = await retriever.search(
        query=payload.query,
        top_k=payload.top_k,
        doc_id=payload.doc_id,
        file_type=payload.file_type,
    )
    return SearchResponse(query=payload.query, took_ms=took_ms, results=results)


@app.post("/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest, db: AsyncSession = Depends(get_db)):
    """Отвечает на вопрос по базе знаний с цитатами на источники."""
    return await RAGService(db).answer(payload)