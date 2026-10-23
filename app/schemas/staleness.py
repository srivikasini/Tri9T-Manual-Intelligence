"""Staleness and Impact Analysis Pydantic schemas."""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum

class StalenessSeverity(str, Enum):
    NONE = "NONE"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"

class DriftType(str, Enum):
    HASH_DRIFT = "HASH_DRIFT"              # Content changed
    NODE_REMOVED = "NODE_REMOVED"          # Node not found in target version
    NODE_MOVED = "NODE_MOVED"              # Node location/parent changed
    AMBIGUOUS_MATCH = "AMBIGUOUS_MATCH"    # Uncertain matching confidence

class StalenessReasonItem(BaseModel):
    node_id: str
    logical_id: str
    drift_type: DriftType
    severity: StalenessSeverity
    description: str
    stored_hash: str
    current_hash: Optional[str] = None
    text_diff: Optional[str] = None

class StalenessCheckResponse(BaseModel):
    artifact_id: str
    selection_id: str
    base_version: str
    target_version: str
    is_stale: bool
    overall_severity: StalenessSeverity
    total_source_nodes: int
    affected_nodes_count: int
    reasons: List[StalenessReasonItem]
    recommendation: str
    checked_at: datetime

class BatchStalenessResponse(BaseModel):
    target_version: str
    total_artifacts_evaluated: int
    stale_artifacts_count: int
    results: List[StalenessCheckResponse]
