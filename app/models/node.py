"""SectionNode ORM model representing hierarchical document units."""
from sqlalchemy import Column, String, Integer, Text, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.core.database import Base

class SectionNode(Base):
    __tablename__ = "nodes"
    
    id = Column(String(64), primary_key=True)  # Version-specific unique ID e.g. "v1_sec_1_0"
    document_version = Column(String(50), ForeignKey("document_versions.version_id"), nullable=False)
    logical_id = Column(String(100), nullable=False, index=True)  # Cross-version stable key
    parent_id = Column(String(64), ForeignKey("nodes.id"), nullable=True)
    
    title = Column(String(255), nullable=False)
    section_number = Column(String(50), nullable=True)  # e.g. "1.1", "2.1.1.1"
    full_text = Column(Text, nullable=False)
    node_type = Column(String(50), default="section")  # "document", "section", "subsection"
    
    page_start = Column(Integer, nullable=False)
    page_end = Column(Integer, nullable=False)
    
    bbox_json = Column(Text, nullable=True)  # JSON bounding boxes
    tables_json = Column(Text, nullable=True)  # JSON extracted tables
    content_hash = Column(String(64), nullable=False, index=True)  # SHA-256
    extraction_warnings_json = Column(Text, nullable=True)  # JSON warnings
    metadata_json = Column(Text, nullable=True)  # JSON extra metadata
    order_index = Column(Integer, nullable=False, default=0)
    
    version = relationship("DocumentVersion", back_populates="nodes")
    parent = relationship("SectionNode", remote_side=[id], backref="children")

    __table_args__ = (
        Index("idx_version_logical", "document_version", "logical_id"),
        Index("idx_version_parent", "document_version", "parent_id"),
    )
