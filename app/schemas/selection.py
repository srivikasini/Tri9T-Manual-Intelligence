from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional, List, Dict, Any

class SelectionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255, description="Name for the selection")
    document_version: str = Field(min_length=1, max_length=50, description="Version of the manual (e.g. 'v1')")
    node_ids: List[str] = Field(min_length=1, description="List of node IDs in desired order")
    description: Optional[str] = Field(default=None, max_length=1000)

class SelectedNodeContent(BaseModel):
    node_id: str
    logical_id: str
    title: str
    section_number: Optional[str] = None
    full_text: str
    content_hash: str
    page_start: int
    page_end: int
    tables: List[Dict[str, Any]] = []

class SelectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: Optional[str] = None
    document_version: str
    node_count: int
    created_at: datetime

class SelectionDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: Optional[str] = None
    document_version: str
    node_count: int
    created_at: datetime
    selected_nodes: List[SelectedNodeContent]
    aggregated_text: str
    aggregated_hash: str
