"""QA Artifact generation and retrieval API route handlers."""
import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.selection import Selection
from app.models.node import SectionNode
from app.models.qa_artifact import QAArtifact
from app.schemas.qa import (
    QATestIdea,
    QAGenerateRequest,
    QAArtifactResponse,
    QAArtifactSummaryResponse
)
from app.llm import get_llm_provider, QAOutputValidator, QAValidationError
from app.core.logging import logger

router = APIRouter(tags=["QA Artifacts"])

@router.post("/selections/{selection_id}/generate-qa", response_model=QAArtifactResponse, status_code=status.HTTP_201_CREATED)
def generate_qa_test_ideas(
    selection_id: str,
    payload: QAGenerateRequest = QAGenerateRequest(),
    db: Session = Depends(get_db)
):
    """Capability 7: Generating 3–5 QA test ideas from a selection."""
    selection = db.query(Selection).filter(Selection.id == selection_id).first()
    if not selection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Selection '{selection_id}' not found"
        )

    # Duplicate selection handling: deterministic behavior
    existing_artifact = (
        db.query(QAArtifact)
        .filter(QAArtifact.selection_id == selection_id)
        .order_by(QAArtifact.created_at.desc())
        .first()
    )
    if existing_artifact and not payload.force_regenerate:
        logger.info(f"Returning existing QA artifact {existing_artifact.id} for selection {selection_id}")
        return QAArtifactResponse(
            id=existing_artifact.id,
            selection_id=existing_artifact.selection_id,
            document_version=existing_artifact.document_version,
            source_node_ids=json.loads(existing_artifact.source_node_ids_json),
            source_snapshots=json.loads(existing_artifact.source_snapshots_json),
            source_hashes=json.loads(existing_artifact.source_hashes_json),
            test_cases=[QATestIdea(**tc) for tc in json.loads(existing_artifact.test_cases_json)],
            validation_status=existing_artifact.validation_status,
            provider_info=json.loads(existing_artifact.provider_info_json) if existing_artifact.provider_info_json else None,
            created_at=existing_artifact.created_at
        )

    # Gather selected source nodes and text snapshots
    source_node_ids = []
    source_snapshots = {}
    source_hashes = {}
    aggregated_text_blocks = []

    for link in selection.selection_nodes:
        n = link.node
        if n:
            source_node_ids.append(n.id)
            source_snapshots[n.id] = n.full_text
            source_hashes[n.id] = n.content_hash
            aggregated_text_blocks.append(f"### Section {n.section_number or ''}: {n.title}\n{n.full_text}")

    if not source_node_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Selection '{selection_id}' has no associated nodes"
        )

    full_context = "\n\n".join(aggregated_text_blocks)

    # Obtain LLM provider and execute validated generation
    provider = get_llm_provider()
    try:
        validated_payload, validation_status, provider_info = QAOutputValidator.generate_and_validate(
            provider=provider,
            context_text=full_context,
            custom_instructions=payload.custom_instructions
        )
    except QAValidationError as qve:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "message": "QA test generation failed strict schema validation after retries.",
                "validation_errors": qve.errors,
                "raw_output": qve.raw_output
            }
        )
    except TimeoutError as te:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=f"LLM generation timed out: {str(te)}"
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error during QA test generation: {str(exc)}"
        )

    # Persist QA Artifact
    artifact = QAArtifact(
        selection_id=selection_id,
        document_version=selection.document_version,
        source_node_ids_json=json.dumps(source_node_ids),
        source_snapshots_json=json.dumps(source_snapshots),
        source_hashes_json=json.dumps(source_hashes),
        test_cases_json=json.dumps([tc.model_dump() for tc in validated_payload.test_cases]),
        validation_status=validation_status,
        provider_info_json=json.dumps(provider_info)
    )
    db.add(artifact)
    db.commit()
    db.refresh(artifact)

    return QAArtifactResponse(
        id=artifact.id,
        selection_id=artifact.selection_id,
        document_version=artifact.document_version,
        source_node_ids=source_node_ids,
        source_snapshots=source_snapshots,
        source_hashes=source_hashes,
        test_cases=validated_payload.test_cases,
        validation_status=artifact.validation_status,
        provider_info=provider_info,
        created_at=artifact.created_at
    )

@router.get("/qa-artifacts", response_model=List[QAArtifactSummaryResponse])
def list_qa_artifacts(
    selection_id: Optional[str] = Query(default=None, description="Filter by selection ID"),
    node_id: Optional[str] = Query(default=None, description="Filter by contained node ID"),
    db: Session = Depends(get_db)
):
    """Capability 8: Retrieving generated QA artifacts by selection or node."""
    query = db.query(QAArtifact)
    if selection_id:
        query = query.filter(QAArtifact.selection_id == selection_id)
    if node_id:
        query = query.filter(QAArtifact.source_node_ids_json.contains(f'"{node_id}"'))

    artifacts = query.order_by(QAArtifact.created_at.desc()).all()
    summaries = []
    for art in artifacts:
        cases = json.loads(art.test_cases_json)
        summaries.append(QAArtifactSummaryResponse(
            id=art.id,
            selection_id=art.selection_id,
            document_version=art.document_version,
            test_count=len(cases),
            validation_status=art.validation_status,
            created_at=art.created_at
        ))
    return summaries

@router.get("/qa-artifacts/{artifact_id}", response_model=QAArtifactResponse)
def get_qa_artifact_by_id(artifact_id: str, db: Session = Depends(get_db)):
    """Retrieve full details of a specific QA artifact."""
    artifact = db.query(QAArtifact).filter(QAArtifact.id == artifact_id).first()
    if not artifact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"QA artifact '{artifact_id}' not found"
        )

    test_cases_data = json.loads(artifact.test_cases_json)
    test_cases = [QATestIdea(**tc) for tc in test_cases_data]

    return QAArtifactResponse(
        id=artifact.id,
        selection_id=artifact.selection_id,
        document_version=artifact.document_version,
        source_node_ids=json.loads(artifact.source_node_ids_json),
        source_snapshots=json.loads(artifact.source_snapshots_json),
        source_hashes=json.loads(artifact.source_hashes_json),
        test_cases=test_cases,
        validation_status=artifact.validation_status,
        provider_info=json.loads(artifact.provider_info_json) if artifact.provider_info_json else None,
        created_at=artifact.created_at
    )
