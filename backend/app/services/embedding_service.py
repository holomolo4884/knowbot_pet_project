from sentence_transformers import SentenceTransformer
from typing import List
from loguru import logger

class EmbeddingService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(EmbeddingService, cls).__new__(cls)
            # Загружаем модель один раз при инициализации
            logger.info("Loading embedding model: intfloat/multilingual-e5-large")
            cls._instance.model = SentenceTransformer("intfloat/multilingual-e5-large")
            logger.info("Embedding model loaded successfully")
        return cls._instance

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        Генерирует эмбеддинги для списка текстов (батчинг).
        """
        if not texts:
            return []
        
        logger.info(f"Generating embeddings for {len(texts)} chunks...")
        # model.encode автоматически делает батчинг
        embeddings = self.model.encode(
            texts, 
            batch_size=32, 
            show_progress_bar=False,
            convert_to_numpy=True
        )
        return embeddings.tolist()

# Синглтон для удобства импорта
embedding_service = EmbeddingService()