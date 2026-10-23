"""Document and SectionNode API route handlers."""
import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.core.database import get_db
from app.models.document import Document, DocumentVersion
from app.models.node import SectionNode
from app.schemas.document import DocumentResponse, DocumentVersionResponse
from app.schemas.node import (
    NodeSummaryResponse,
    NodeDetailResponse,
    NodeTreeResponse,
    SearchResultResponse,
    SearchMatchResponse,
    TableData
)

router = APIRouter(prefix="/documents", tags=["Documents & Sections"])

@router.get("", response_model=List[DocumentVersionResponse])
def list_document_versions(db: Session = Depends(get_db)):
    """List all ingested document versions and metadata."""
    versions = db.query(DocumentVersion).all()
    results = []
    for v in versions:
        meta = json.loads(v.extraction_metadata) if v.extraction_metadata else None
        results.append(DocumentVersionResponse(
            version_id=v.version_id,
            document_id=v.document_id,
            filename=v.filename,
            file_hash=v.file_hash,
            page_count=v.page_count,
            ingested_at=v.ingested_at,
            extraction_metadata=meta
        ))
    return results

@router.get("/{version}/sections", response_model=List[NodeSummaryResponse])
def list_top_level_sections(version: str, db: Session = Depends(get_db)):
    """Capability 1: Listing top-level sections for a selected document version."""
    # Verify version exists
    doc_ver = db.query(DocumentVersion).filter(DocumentVersion.version_id == version).first()
    if not doc_ver:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Document version '{version}' not found")

    top_sections = (
        db.query(SectionNode)
        .filter(SectionNode.document_version == version, SectionNode.parent_id == None)
        .order_by(SectionNode.order_index)
        .all()
    )

    summaries = []
    for sec in top_sections:
        child_count = db.query(SectionNode).filter(SectionNode.parent_id == sec.id).count()
        summaries.append(NodeSummaryResponse(
            id=sec.id,
            document_version=sec.document_version,
            logical_id=sec.logical_id,
            parent_id=sec.parent_id,
            title=sec.title,
            section_number=sec.section_number,
            node_type=sec.node_type,
            page_start=sec.page_start,
            page_end=sec.page_end,
            content_hash=sec.content_hash,
            child_count=child_count
        ))
    return summaries

@router.get("/{version}/tree", response_model=List[NodeTreeResponse])
def get_hierarchy_tree(version: str, db: Session = Depends(get_db)):
    """Retrieve full hierarchical document tree for a version."""
    doc_ver = db.query(DocumentVersion).filter(DocumentVersion.version_id == version).first()
    if not doc_ver:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Document version '{version}' not found")

    all_nodes = (
        db.query(SectionNode)
        .filter(SectionNode.document_version == version)
        .order_by(SectionNode.order_index)
        .all()
    )

    node_map = {}
    roots = []

    for n in all_nodes:
        tree_node = NodeTreeResponse(
            id=n.id,
            document_version=n.document_version,
            logical_id=n.logical_id,
            title=n.title,
            section_number=n.section_number,
            node_type=n.node_type,
            page_start=n.page_start,
            page_end=n.page_end,
            content_hash=n.content_hash,
            children=[]
        )
        node_map[n.id] = tree_node

    for n in all_nodes:
        curr = node_map[n.id]
        if n.parent_id and n.parent_id in node_map:
            node_map[n.parent_id].children.append(curr)
        else:
            roots.append(curr)

    return roots

@router.get("/{version}/nodes/{node_id}", response_model=NodeDetailResponse)
def get_node_by_id(version: str, node_id: str, db: Session = Depends(get_db)):
    """Capability 2: Retrieving a node by ID, including metadata, children, full text, and content hash."""
    node = (
        db.query(SectionNode)
        .filter(SectionNode.document_version == version, SectionNode.id == node_id)
        .first()
    )
    if not node:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Node '{node_id}' not found in document version '{version}'"
        )

    # Fetch immediate children
    children = (
        db.query(SectionNode)
        .filter(SectionNode.parent_id == node.id)
        .order_by(SectionNode.order_index)
        .all()
    )

    child_responses = []
    for c in children:
        c_tables = [TableData(**t) for t in json.loads(c.tables_json)] if c.tables_json else []
        c_warnings = json.loads(c.extraction_warnings_json) if c.extraction_warnings_json else []
        c_bbox = json.loads(c.bbox_json) if c.bbox_json else None
        child_responses.append(NodeDetailResponse(
            id=c.id,
            document_version=c.document_version,
            logical_id=c.logical_id,
            parent_id=c.parent_id,
            title=c.title,
            section_number=c.section_number,
            full_text=c.full_text,
            node_type=c.node_type,
            page_start=c.page_start,
            page_end=c.page_end,
            bbox=c_bbox,
            tables=c_tables,
            content_hash=c.content_hash,
            extraction_warnings=c_warnings,
            order_index=c.order_index,
            children=[]
        ))

    tables = [TableData(**t) for t in json.loads(node.tables_json)] if node.tables_json else []
    warnings = json.loads(node.extraction_warnings_json) if node.extraction_warnings_json else []
    bbox = json.loads(node.bbox_json) if node.bbox_json else None
    meta = json.loads(node.metadata_json) if node.metadata_json else None

    return NodeDetailResponse(
        id=node.id,
        document_version=node.document_version,
        logical_id=node.logical_id,
        parent_id=node.parent_id,
        title=node.title,
        section_number=node.section_number,
        full_text=node.full_text,
        node_type=node.node_type,
        page_start=node.page_start,
        page_end=node.page_end,
        bbox=bbox,
        tables=tables,
        content_hash=node.content_hash,
        extraction_warnings=warnings,
        metadata=meta,
        order_index=node.order_index,
        children=child_responses
    )

@router.get("/{version}/search", response_model=SearchResultResponse)
def search_document_content(
    version: str,
    q: str = Query(min_length=1, max_length=100, description="Keyword search query"),
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """Capability 3: Searching document content with snippet highlighting."""
    doc_ver = db.query(DocumentVersion).filter(DocumentVersion.version_id == version).first()
    if not doc_ver:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Document version '{version}' not found")

    terms = q.strip().lower().split()
    query_filter = or_(*[SectionNode.full_text.ilike(f"%{term}%") for term in terms], *[SectionNode.title.ilike(f"%{term}%") for term in terms])
    
    matches = (
        db.query(SectionNode)
        .filter(SectionNode.document_version == version, query_filter)
        .all()
    )

    scored_results = []
    for node in matches:
        text_lower = node.full_text.lower()
        title_lower = node.title.lower()
        
        # Calculate matching score based on term frequencies
        score = 0.0
        for term in terms:
            if term in title_lower:
                score += 3.0
            score += text_lower.count(term) * 1.0

        # Create snippet with query term highlighted
        first_term_idx = -1
        for term in terms:
            idx = text_lower.find(term)
            if idx != -1:
                first_term_idx = idx
                break

        if first_term_idx != -1:
            start = max(0, first_term_idx - 60)
            end = min(len(node.full_text), first_term_idx + 120)
            prefix = "..." if start > 0 else ""
            suffix = "..." if end < len(node.full_text) else ""
            snippet = f"{prefix}{node.full_text[start:end].strip()}{suffix}"
        else:
            snippet = node.full_text[:150] + ("..." if len(node.full_text) > 150 else "")

        scored_results.append((score, SearchMatchResponse(
            node_id=node.id,
            document_version=node.document_version,
            logical_id=node.logical_id,
            title=node.title,
            section_number=node.section_number,
            matched_snippet=snippet,
            page=node.page_start,
            score=round(score, 2)
        )))

    scored_results.sort(key=lambda x: x[0], reverse=True)
    top_results = [r[1] for r in scored_results[:limit]]

    return SearchResultResponse(
        query=q,
        document_version=version,
        total_matches=len(scored_results),
        results=top_results
    )
