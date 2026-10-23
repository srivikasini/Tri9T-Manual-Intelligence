"""Staleness and impact analysis API route handlers."""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.qa_artifact import QAArtifact
from app.models.document import DocumentVersion
from app.schemas.staleness import StalenessCheckResponse, BatchStalenessResponse
from app.staleness.analyzer import StalenessAnalyzer

router = APIRouter(tags=["Staleness & Impact Analysis"])

@router.get("/qa-artifacts/{artifact_id}/staleness", response_model=StalenessCheckResponse)
def check_artifact_staleness(
    artifact_id: str,
    target_version: str = Query(default="v2", description="Document version to test staleness against"),
    db: Session = Depends(get_db)
):
    """Capability 9: Checking and retrieving staleness and impact information for a QA artifact."""
    artifact = db.query(QAArtifact).filter(QAArtifact.id == artifact_id).first()
    if not artifact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"QA artifact '{artifact_id}' not found"
        )

    target_ver = db.query(DocumentVersion).filter(DocumentVersion.version_id == target_version).first()
    if not target_ver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Target document version '{target_version}' not found"
        )

    result = StalenessAnalyzer.evaluate_artifact_staleness(
        artifact=artifact,
        target_version=target_version,
        db=db
    )
    return result

@router.get("/staleness", response_model=BatchStalenessResponse)
def batch_check_staleness(
    target_version: str = Query(default="v2", description="Document version to test staleness against"),
    db: Session = Depends(get_db)
):
    """Batch evaluate staleness for all QA artifacts against a target document version."""
    target_ver = db.query(DocumentVersion).filter(DocumentVersion.version_id == target_version).first()
    if not target_ver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Target document version '{target_version}' not found"
        )

    all_artifacts = db.query(QAArtifact).all()
    results = []
    stale_count = 0

    for art in all_artifacts:
        res = StalenessAnalyzer.evaluate_artifact_staleness(
            artifact=art,
            target_version=target_version,
            db=db
        )
        if res.is_stale:
            stale_count += 1
        results.append(res)

    return BatchStalenessResponse(
        target_version=target_version,
        total_artifacts_evaluated=len(all_artifacts),
        stale_artifacts_count=stale_count,
        results=results
    )
