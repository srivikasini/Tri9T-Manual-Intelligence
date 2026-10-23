"""Document Ingestion API route handlers."""
import json
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.config import settings
from app.models.document import Document, DocumentVersion
from app.models.node import SectionNode
from app.schemas.document import IngestResponse
from app.ingestion.pdf_extractor import PDFExtractor
from app.hierarchy.tree_builder import HierarchyTreeBuilder
from app.core.logging import logger

router = APIRouter(tags=["Document Ingestion"])

class IngestPayload(BaseModel):
    file_path: Optional[str] = Field(default=None, description="Path to PDF manual file")
    version_id: str = Field(description="Version string, e.g. 'v1' or 'v2'")
    document_id: str = Field(default="ct200_manual", description="Parent document identifier")

def perform_ingestion(file_path: Path, version_id: str, document_id: str, db: Session) -> IngestResponse:
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Source PDF file not found at: {file_path}"
        )

    # Ingest through extraction pipeline
    extraction_data = PDFExtractor.extract_document(file_path, version_id)
    raw_sections = extraction_data["raw_sections"]
    global_warnings = extraction_data["global_warnings"]

    # Build normalized hierarchy
    normalized_nodes = HierarchyTreeBuilder.build_hierarchy(raw_sections, version_id)

    # Ensure parent document exists
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        doc = Document(id=document_id, title="CardioTrack CT-200 Technical Manual")
        db.add(doc)
        db.flush()

    # Create or update DocumentVersion
    doc_ver = db.query(DocumentVersion).filter(DocumentVersion.version_id == version_id).first()
    if not doc_ver:
        doc_ver = DocumentVersion(
            version_id=version_id,
            document_id=document_id,
            filename=extraction_data["filename"],
            file_hash=extraction_data["file_hash"],
            page_count=extraction_data["page_count"],
            extraction_metadata=json.dumps({"global_warnings": global_warnings})
        )
        db.add(doc_ver)
        db.flush()
    else:
        # Update metadata
        doc_ver.file_hash = extraction_data["file_hash"]
        doc_ver.page_count = extraction_data["page_count"]
        doc_ver.extraction_metadata = json.dumps({"global_warnings": global_warnings})
        # Remove old nodes for this version if re-ingesting
        db.query(SectionNode).filter(SectionNode.document_version == version_id).delete()
        db.flush()

    # Persist normalized nodes
    top_level_count = 0
    for node_data in normalized_nodes:
        if node_data.parent_id is None:
            top_level_count += 1

        db_node = SectionNode(
            id=node_data.node_id,
            document_version=version_id,
            logical_id=node_data.logical_id,
            parent_id=node_data.parent_id,
            title=node_data.title,
            section_number=node_data.section_number,
            full_text=node_data.full_text,
            node_type=node_data.node_type,
            page_start=node_data.page_start,
            page_end=node_data.page_end,
            bbox_json=json.dumps(node_data.bbox),
            tables_json=json.dumps(node_data.tables),
            content_hash=node_data.content_hash,
            extraction_warnings_json=json.dumps(node_data.warnings),
            order_index=node_data.order_index
        )
        db.add(db_node)

    db.commit()
    logger.info(f"Ingested {len(normalized_nodes)} nodes for version {version_id}")

    return IngestResponse(
        document_id=document_id,
        version_id=version_id,
        filename=extraction_data["filename"],
        file_hash=extraction_data["file_hash"],
        page_count=extraction_data["page_count"],
        total_nodes_extracted=len(normalized_nodes),
        top_level_sections_count=top_level_count,
        warnings=global_warnings
    )

@router.post("/ingest", response_model=IngestResponse, status_code=status.HTTP_200_OK)
def ingest_document(payload: IngestPayload, db: Session = Depends(get_db)):
    """Trigger ingestion of a manual version into the database."""
    if payload.file_path:
        pdf_path = Path(payload.file_path)
    elif payload.version_id == "v1":
        pdf_path = settings.V1_PDF_PATH
    elif payload.version_id == "v2":
        pdf_path = settings.V2_PDF_PATH
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must provide file_path for non-standard version IDs"
        )

    return perform_ingestion(pdf_path, payload.version_id, payload.document_id, db)
