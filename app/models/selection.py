"""Selection and SelectionNode ORM models."""
from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import uuid
from app.core.database import Base

class Selection(Base):
    __tablename__ = "selections"
    
    id = Column(String(64), primary_key=True, default=lambda: f"sel_{uuid.uuid4().hex[:12]}")
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    document_version = Column(String(50), ForeignKey("document_versions.version_id"), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    version = relationship("DocumentVersion", back_populates="selections")
    selection_nodes = relationship("SelectionNode", back_populates="selection", cascade="all, delete-orphan", order_by="SelectionNode.order_index")
    qa_artifacts = relationship("QAArtifact", back_populates="selection", cascade="all, delete-orphan")

class SelectionNode(Base):
    __tablename__ = "selection_nodes"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    selection_id = Column(String(64), ForeignKey("selections.id"), nullable=False)
    node_id = Column(String(64), ForeignKey("nodes.id"), nullable=False)
    order_index = Column(Integer, nullable=False, default=0)
    
    selection = relationship("Selection", back_populates="selection_nodes")
    node = relationship("SectionNode")
    
    __table_args__ = (
        UniqueConstraint("selection_id", "node_id", name="uq_selection_node"),
    )
