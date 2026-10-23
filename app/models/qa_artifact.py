"""QAArtifact ORM model for storing generated test ideas and source provenance."""
from sqlalchemy import Column, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import uuid
from app.core.database import Base

class QAArtifact(Base):
    __tablename__ = "qa_artifacts"
    
    id = Column(String(64), primary_key=True, default=lambda: f"qa_{uuid.uuid4().hex[:12]}")
    selection_id = Column(String(64), ForeignKey("selections.id"), nullable=False)
    document_version = Column(String(50), nullable=False)
    
    source_node_ids_json = Column(Text, nullable=False)     # list[str] of node IDs
    source_snapshots_json = Column(Text, nullable=False)    # dict[str, str]: node_id -> text
    source_hashes_json = Column(Text, nullable=False)       # dict[str, str]: node_id -> hash
    
    test_cases_json = Column(Text, nullable=False)          # list[dict]: 3-5 QA test cases
    validation_status = Column(String(50), nullable=False, default="VALID")
    provider_info_json = Column(Text, nullable=True)        # dict: provider, model, etc.
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    selection = relationship("Selection", back_populates="qa_artifacts")
    staleness_checks = relationship("StalenessCheck", back_populates="artifact", cascade="all, delete-orphan")
