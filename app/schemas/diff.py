"""Version comparison and diff Pydantic schemas."""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum

class ChangeType(str, Enum):
    UNCHANGED = "UNCHANGED"
    MODIFIED = "MODIFIED"
    ADDED = "ADDED"
    REMOVED = "REMOVED"
    MOVED = "MOVED"

class NodeComparison(BaseModel):
    logical_id: str
    change_type: ChangeType
    matching_confidence: float = Field(ge=0.0, le=1.0)
    is_ambiguous: bool = False
    
    # Base node (e.g. v1)
    base_node_id: Optional[str] = None
    base_title: Optional[str] = None
    base_section_number: Optional[str] = None
    base_hash: Optional[str] = None
    base_parent_id: Optional[str] = None
    
    # Target node (e.g. v2)
    target_node_id: Optional[str] = None
    target_title: Optional[str] = None
    target_section_number: Optional[str] = None
    target_hash: Optional[str] = None
    target_parent_id: Optional[str] = None
    
    # Unified diff if modified
    unified_diff: Optional[str] = None
    diff_summary: Optional[Dict[str, int]] = None  # {"added_lines": x, "deleted_lines": y}
    explanation: Optional[str] = None

class VersionComparisonResponse(BaseModel):
    base_version: str
    target_version: str
    total_base_nodes: int
    total_target_nodes: int
    summary: Dict[str, int]  # counts of UNCHANGED, MODIFIED, ADDED, REMOVED, MOVED
    comparisons: List[NodeComparison]
