"""StalenessCheck ORM model for recording impact and staleness analyses."""
from sqlalchemy import Column, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import uuid
from app.core.database import Base

class StalenessCheck(Base):
    __tablename__ = "staleness_checks"
    
    id = Column(String(64), primary_key=True, default=lambda: f"stale_{uuid.uuid4().hex[:12]}")
    artifact_id = Column(String(64), ForeignKey("qa_artifacts.id"), nullable=False)
    target_version = Column(String(50), nullable=False)
    
    is_stale = Column(Boolean, nullable=False, default=False)
    severity = Column(String(20), nullable=False, default="NONE")  # NONE, LOW, MEDIUM, HIGH
    reasons_json = Column(Text, nullable=False)                    # list[dict]: detected drift reasons
    impact_analysis_json = Column(Text, nullable=True)             # structured impact analysis
    checked_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    artifact = relationship("QAArtifact", back_populates="staleness_checks")
