"""Automated tests for staleness and impact analysis."""
import json
import pytest
from app.models.node import SectionNode
from app.models.selection import Selection, SelectionNode
from app.models.qa_artifact import QAArtifact
from app.staleness.analyzer import StalenessAnalyzer
from app.schemas.staleness import StalenessSeverity, DriftType

def test_staleness_on_unchanged_nodes(populated_db):
    """Verify that an artifact whose source nodes did not change remains not stale."""
    # Section 1.1 Intended Use is identical in v1 and v2
    node = populated_db.query(SectionNode).filter(
        SectionNode.document_version == "v1",
        SectionNode.section_number == "1.1"
    ).first()
    assert node is not None

    sel = Selection(name="Unchanged Selection", document_version="v1")
    populated_db.add(sel)
    populated_db.flush()
    populated_db.add(SelectionNode(selection_id=sel.id, node_id=node.id, order_index=0))
    populated_db.commit()

    artifact = QAArtifact(
        selection_id=sel.id,
        document_version="v1",
        source_node_ids_json=json.dumps([node.id]),
        source_snapshots_json=json.dumps({node.id: node.full_text}),
        source_hashes_json=json.dumps({node.id: node.content_hash}),
        test_cases_json=json.dumps([]),
        validation_status="VALID"
    )
    populated_db.add(artifact)
    populated_db.commit()

    result = StalenessAnalyzer.evaluate_artifact_staleness(artifact, "v2", populated_db)
    assert result.is_stale is False
    assert result.overall_severity == StalenessSeverity.NONE
    assert result.affected_nodes_count == 0
    assert len(result.reasons) == 0

def test_staleness_on_content_drift(populated_db):
    """Verify detection of content drift with HIGH severity when parameters change."""
    # Section 4.2 Error Codes changed (E3 2s -> 1.5s, E6 added)
    node = populated_db.query(SectionNode).filter(
        SectionNode.document_version == "v1",
        SectionNode.section_number == "4.2"
    ).first()
    assert node is not None

    sel = Selection(name="Drift Selection", document_version="v1")
    populated_db.add(sel)
    populated_db.flush()
    populated_db.add(SelectionNode(selection_id=sel.id, node_id=node.id, order_index=0))
    populated_db.commit()

    artifact = QAArtifact(
        selection_id=sel.id,
        document_version="v1",
        source_node_ids_json=json.dumps([node.id]),
        source_snapshots_json=json.dumps({node.id: node.full_text}),
        source_hashes_json=json.dumps({node.id: node.content_hash}),
        test_cases_json=json.dumps([]),
        validation_status="VALID"
    )
    populated_db.add(artifact)
    populated_db.commit()

    result = StalenessAnalyzer.evaluate_artifact_staleness(artifact, "v2", populated_db)
    assert result.is_stale is True
    assert result.overall_severity == StalenessSeverity.HIGH
    assert result.affected_nodes_count == 1
    assert result.reasons[0].drift_type == DriftType.HASH_DRIFT
    assert result.reasons[0].text_diff is not None

def test_staleness_on_removed_node(populated_db):
    """Verify that a node missing in the target version is flagged as NODE_REMOVED with HIGH severity."""
    # Create synthetic v1 node not in v2
    synthetic_node = SectionNode(
        id="v1_sec_9_9_obsolete",
        document_version="v1",
        logical_id="sec:9.9:obsolete-feature",
        title="Obsolete Feature",
        section_number="9.9",
        full_text="This feature was deprecated.",
        node_type="section",
        page_start=1,
        page_end=1,
        content_hash="abc123456789",
        order_index=99
    )
    populated_db.add(synthetic_node)
    populated_db.commit()

    sel = Selection(name="Obsolete Feature Selection", document_version="v1")
    populated_db.add(sel)
    populated_db.flush()
    populated_db.add(SelectionNode(selection_id=sel.id, node_id=synthetic_node.id, order_index=0))
    populated_db.commit()

    artifact = QAArtifact(
        selection_id=sel.id,
        document_version="v1",
        source_node_ids_json=json.dumps([synthetic_node.id]),
        source_snapshots_json=json.dumps({synthetic_node.id: synthetic_node.full_text}),
        source_hashes_json=json.dumps({synthetic_node.id: synthetic_node.content_hash}),
        test_cases_json=json.dumps([]),
        validation_status="VALID"
    )
    populated_db.add(artifact)
    populated_db.commit()

    result = StalenessAnalyzer.evaluate_artifact_staleness(artifact, "v2", populated_db)
    assert result.is_stale is True
    assert result.overall_severity == StalenessSeverity.HIGH
    assert result.reasons[0].drift_type == DriftType.NODE_REMOVED
