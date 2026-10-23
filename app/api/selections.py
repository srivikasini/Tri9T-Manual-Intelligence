"""Selection management API route handlers."""
import hashlib
import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.document import DocumentVersion
from app.models.node import SectionNode
from app.models.selection import Selection, SelectionNode
from app.schemas.selection import (
    SelectionCreate,
    SelectionResponse,
    SelectionDetailResponse,
    SelectedNodeContent
)

router = APIRouter(prefix="/selections", tags=["Selections"])

@router.post("", response_model=SelectionResponse, status_code=status.HTTP_201_CREATED)
def create_selection(payload: SelectionCreate, db: Session = Depends(get_db)):
    """Capability 5: Creating named, version-pinned node selections."""
    # Verify version exists
    doc_ver = db.query(DocumentVersion).filter(DocumentVersion.version_id == payload.document_version).first()
    if not doc_ver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document version '{payload.document_version}' does not exist"
        )

    # Verify each node exists and belongs to this version
    existing_nodes = (
        db.query(SectionNode)
        .filter(
            SectionNode.document_version == payload.document_version,
            SectionNode.id.in_(payload.node_ids)
        )
        .all()
    )
    existing_node_map = {n.id: n for n in existing_nodes}
    missing_ids = [nid for nid in payload.node_ids if nid not in existing_node_map]

    if missing_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"The following node IDs were not found in version '{payload.document_version}': {missing_ids}"
        )

    # Create Selection record
    selection = Selection(
        name=payload.name,
        description=payload.description,
        document_version=payload.document_version
    )
    db.add(selection)
    db.flush()

    # Link nodes in requested order
    for idx, nid in enumerate(payload.node_ids):
        link = SelectionNode(
            selection_id=selection.id,
            node_id=nid,
            order_index=idx
        )
        db.add(link)

    db.commit()
    db.refresh(selection)

    return SelectionResponse(
        id=selection.id,
        name=selection.name,
        description=selection.description,
        document_version=selection.document_version,
        node_count=len(payload.node_ids),
        created_at=selection.created_at
    )

@router.get("", response_model=List[SelectionResponse])
def list_selections(
    version: Optional[str] = Query(default=None, description="Optional document version filter"),
    db: Session = Depends(get_db)
):
    """Retrieve all saved selections."""
    query = db.query(Selection)
    if version:
        query = query.filter(Selection.document_version == version)
    selections = query.order_by(Selection.created_at.desc()).all()

    results = []
    for s in selections:
        results.append(SelectionResponse(
            id=s.id,
            name=s.name,
            description=s.description,
            document_version=s.document_version,
            node_count=len(s.selection_nodes),
            created_at=s.created_at
        ))
    return results

@router.get("/{selection_id}", response_model=SelectionDetailResponse)
def get_selection_detail(selection_id: str, db: Session = Depends(get_db)):
    """Capability 6: Retrieving selections and their selected content."""
    selection = db.query(Selection).filter(Selection.id == selection_id).first()
    if not selection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Selection '{selection_id}' not found"
        )

    selected_nodes = []
    aggregated_text_parts = []
    hasher = hashlib.sha256()

    for link in selection.selection_nodes:
        n = link.node
        if n:
            tables = json.loads(n.tables_json) if n.tables_json else []
            node_content = SelectedNodeContent(
                node_id=n.id,
                logical_id=n.logical_id,
                title=n.title,
                section_number=n.section_number,
                full_text=n.full_text,
                content_hash=n.content_hash,
                page_start=n.page_start,
                page_end=n.page_end,
                tables=tables
            )
            selected_nodes.append(node_content)
            
            section_header = f"### Section {n.section_number or ''}: {n.title}\n"
            full_sec_text = f"{section_header}{n.full_text}\n"
            aggregated_text_parts.append(full_sec_text)
            hasher.update(n.content_hash.encode("utf-8"))

    combined_text = "\n\n".join(aggregated_text_parts)
    aggregated_hash = hasher.hexdigest()

    return SelectionDetailResponse(
        id=selection.id,
        name=selection.name,
        description=selection.description,
        document_version=selection.document_version,
        node_count=len(selected_nodes),
        created_at=selection.created_at,
        selected_nodes=selected_nodes,
        aggregated_text=combined_text,
        aggregated_hash=aggregated_hash
    )
