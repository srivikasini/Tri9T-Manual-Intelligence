from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any

class ProvenanceInfo(BaseModel):
    page_start: int
    page_end: int
    bbox: Optional[List[float]] = None
    order_index: int = 0

class TableData(BaseModel):
    headers: List[str] = []
    rows: List[List[str]] = []
    page: int = 1

class NodeSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    document_version: str
    logical_id: str
    parent_id: Optional[str] = None
    title: str
    section_number: Optional[str] = None
    node_type: str
    page_start: int
    page_end: int
    content_hash: str
    child_count: int = 0

class NodeDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    document_version: str
    logical_id: str
    parent_id: Optional[str] = None
    title: str
    section_number: Optional[str] = None
    full_text: str
    node_type: str
    page_start: int
    page_end: int
    bbox: Optional[List[float]] = None
    tables: List[TableData] = []
    content_hash: str
    extraction_warnings: List[str] = []
    metadata: Optional[Dict[str, Any]] = None
    order_index: int
    children: List["NodeDetailResponse"] = []

class NodeTreeResponse(BaseModel):
    id: str
    document_version: str
    logical_id: str
    title: str
    section_number: Optional[str] = None
    node_type: str
    page_start: int
    page_end: int
    content_hash: str
    children: List["NodeTreeResponse"] = []

class SearchMatchResponse(BaseModel):
    node_id: str
    document_version: str
    logical_id: str
    title: str
    section_number: Optional[str] = None
    matched_snippet: str
    page: int
    score: float

class SearchResultResponse(BaseModel):
    query: str
    document_version: str
    total_matches: int
    results: List[SearchMatchResponse]
