"""Automated tests for selection creation, version pinning, and retrieval."""
import pytest
from app.models.node import SectionNode
from app.models.selection import Selection
from app.api.selections import create_selection, get_selection_detail
from app.schemas.selection import SelectionCreate
from fastapi import HTTPException

def test_selection_creation_and_ordering(populated_db):
    """Verify selection persistence and preservation of exact node order."""
    v1_nodes = (
        populated_db.query(SectionNode)
        .filter(SectionNode.document_version == "v1")
        .limit(3)
        .all()
    )
    assert len(v1_nodes) >= 3
    
    # Intentionally reverse node order
    node_ids = [v1_nodes[2].id, v1_nodes[0].id, v1_nodes[1].id]
    
    payload = SelectionCreate(
        name="Custom Ordering Suite",
        description="Testing node order preservation",
        document_version="v1",
        node_ids=node_ids
    )
    
    created = create_selection(payload, populated_db)
    assert created.id.startswith("sel_")
    assert created.node_count == 3
    assert created.document_version == "v1"
    
    # Retrieve detail
    detail = get_selection_detail(created.id, populated_db)
    assert len(detail.selected_nodes) == 3
    assert [n.node_id for n in detail.selected_nodes] == node_ids
    assert len(detail.aggregated_text) > 0
    assert len(detail.aggregated_hash) == 64

def test_selection_with_invalid_node_id(populated_db):
    """Verify that specifying non-existent node IDs raises a 400 Bad Request."""
    payload = SelectionCreate(
        name="Invalid Suite",
        document_version="v1",
        node_ids=["non_existent_node_uuid_999"]
    )
    
    with pytest.raises(HTTPException) as exc_info:
        create_selection(payload, populated_db)
        
    assert exc_info.value.status_code == 400
    assert "not found in version 'v1'" in exc_info.value.detail
