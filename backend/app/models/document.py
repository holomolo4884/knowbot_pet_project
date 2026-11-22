import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector

from app.core.database import Base


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (
        Index("ix_documents_content_hash", "content_hash", unique=True),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String, nullable=False)
    source_path = Column(String, nullable=True)
    file_type = Column(String, nullable=True)
    content_hash = Column(String(64), nullable=False, unique=True)
    file_size = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    chunks = relationship(
        "Chunk",
        back_populates="document",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class Chunk(Base):
    __tablename__ = "chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    text = Column(Text, nullable=False)
    embedding = Column(Vector(1024), nullable=True)
    metadata_ = Column("metadata", JSONB, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)

    document = relationship("Document", back_populates="chunks")