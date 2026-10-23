"""Version comparison and diff API route handlers."""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.document import DocumentVersion
from app.models.node import SectionNode
from app.schemas.diff import VersionComparisonResponse
from app.diffing.change_detector import ChangeDetector

router = APIRouter(tags=["Version Comparison & Diffing"])

@router.get("/compare", response_model=VersionComparisonResponse)
def compare_document_versions(
    base_version: str = Query(default="v1", description="Base document version to compare from"),
    target_version: str = Query(default="v2", description="Target document version to compare to"),
    db: Session = Depends(get_db)
):
    """Capability 4: Comparing nodes across versions and returning changed status and useful diffs."""
    # Validate base and target versions exist
    base_ver = db.query(DocumentVersion).filter(DocumentVersion.version_id == base_version).first()
    if not base_ver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Base document version '{base_version}' not found"
        )

    target_ver = db.query(DocumentVersion).filter(DocumentVersion.version_id == target_version).first()
    if not target_ver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Target document version '{target_version}' not found"
        )

    # Fetch nodes for both versions
    base_nodes = (
        db.query(SectionNode)
        .filter(SectionNode.document_version == base_version)
        .order_by(SectionNode.order_index)
        .all()
    )

    target_nodes = (
        db.query(SectionNode)
        .filter(SectionNode.document_version == target_version)
        .order_by(SectionNode.order_index)
        .all()
    )

    result = ChangeDetector.compare_versions(
        base_version=base_version,
        target_version=target_version,
        base_nodes=base_nodes,
        target_nodes=target_nodes
    )

    return result
