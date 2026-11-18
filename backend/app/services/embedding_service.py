from typing import Literal

from loguru import logger
from sentence_transformers import SentenceTransformer

ModelKind = Literal["query", "passage"]


class EmbeddingService:
    """Обёртка над multilingual-e5.

    ВАЖНО: e5-модели требуют префиксов:
      - "query: " для поисковых запросов
      - "passage: " для индексируемых документов
    Без них retrieval деградирует.
    """

    MODEL_NAME = "intfloat/multilingual-e5-large"
    DIMENSIONS = 1024

    _instance: "EmbeddingService | None" = None
    _model: SentenceTransformer | None = None

    def __new__(cls) -> "EmbeddingService":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @property
    def model(self) -> SentenceTransformer:
        """Ленивая загрузка — модель тянется только при первом обращении."""
        if self._model is None:
            logger.info(f"Loading embedding model: {self.MODEL_NAME}")
            type(self)._model = SentenceTransformer(self.MODEL_NAME)
            logger.info("Embedding model loaded")
        return self._model

    def embed(self, texts: list[str], kind: ModelKind) -> list[list[float]]:
        if not texts:
            return []

        prefixed = [f"{kind}: {t}" for t in texts]
        logger.debug(f"Embedding {len(texts)} texts as '{kind}'")

        vectors = self.model.encode(
            prefixed,
            batch_size=32,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        return vectors.tolist()

    def embed_query(self, query: str) -> list[float]:
        return self.embed([query], kind="query")[0]

    def embed_passages(self, texts: list[str]) -> list[list[float]]:
        return self.embed(texts, kind="passage")


embedding_service = EmbeddingService()