from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional, List, Dict, Any

class QATestIdea(BaseModel):
    test_id: str = Field(description="Unique identifier for the test idea, e.g. TC-01")
    test_objective: str = Field(min_length=5, description="Clear, verifiable test objective")
    preconditions: List[str] = Field(min_length=1, description="Prerequisite conditions or equipment state")
    steps: List[str] = Field(min_length=1, description="Sequential actionable steps to execute the test")
    expected_result: str = Field(min_length=5, description="Specific, observable expected outcome")
    source_references: List[str] = Field(min_length=1, description="Grounding reference section numbers or node IDs")

class QAGenerationPayload(BaseModel):
    test_cases: List[QATestIdea] = Field(
        min_length=3,
        max_length=5,
        description="Exactly 3 to 5 grounded QA test ideas"
    )

class QAGenerateRequest(BaseModel):
    force_regenerate: bool = Field(
        default=False,
        description="If false, returns existing artifact if selection was already generated"
    )
    custom_instructions: Optional[str] = Field(
        default=None,
        description="Optional additional test design criteria (e.g. boundary testing, safety priority)"
    )

class QAArtifactResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    selection_id: str
    document_version: str
    source_node_ids: List[str]
    source_snapshots: Dict[str, str]
    source_hashes: Dict[str, str]
    test_cases: List[QATestIdea]
    validation_status: str
    provider_info: Optional[Dict[str, Any]] = None
    created_at: datetime
    is_stale: Optional[bool] = None
    staleness_reason: Optional[str] = None

class QAArtifactSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    selection_id: str
    document_version: str
    test_count: int
    validation_status: str
    created_at: datetime
