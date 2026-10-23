"""Document and DocumentVersion ORM models."""
from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.core.database import Base

class Document(Base):
    __tablename__ = "documents"
    
    id = Column(String(50), primary_key=True)  # e.g. "ct200_manual"
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    versions = relationship("DocumentVersion", back_populates="document", cascade="all, delete-orphan")

class DocumentVersion(Base):
    __tablename__ = "document_versions"
    
    version_id = Column(String(50), primary_key=True)  # e.g. "v1", "v2"
    document_id = Column(String(50), ForeignKey("documents.id"), nullable=False)
    filename = Column(String(255), nullable=False)
    file_hash = Column(String(64), nullable=False)  # SHA-256 of file
    page_count = Column(Integer, nullable=False)
    ingested_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    extraction_metadata = Column(Text, nullable=True)  # JSON metadata
    
    document = relationship("Document", back_populates="versions")
    nodes = relationship("SectionNode", back_populates="version", cascade="all, delete-orphan")
    selections = relationship("Selection", back_populates="version", cascade="all, delete-orphan")
