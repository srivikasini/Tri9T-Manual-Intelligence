"""Document and DocumentVersion Pydantic schemas."""
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional, List, Dict, Any

class DocumentVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    version_id: str
    document_id: str
    filename: str
    file_hash: str
    page_count: int
    ingested_at: datetime
    extraction_metadata: Optional[Dict[str, Any]] = None

class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    description: Optional[str] = None
    created_at: datetime
    versions: List[DocumentVersionResponse] = []

class IngestResponse(BaseModel):
    document_id: str
    version_id: str
    filename: str
    file_hash: str
    page_count: int
    total_nodes_extracted: int
    top_level_sections_count: int
    warnings: List[str] = []
