"""Automated tests for version matching and change detection."""
import pytest
from app.models.node import SectionNode
from app.diffing.change_detector import ChangeDetector
from app.diffing.matcher import CrossVersionMatcher, text_similarity, token_jaccard_similarity
from app.diffing.differ import TextDiffer
from app.schemas.diff import ChangeType

def test_text_similarity_and_jaccard():
    """Verify string similarity and token Jaccard calculations."""
    assert text_similarity("Error Codes", "error codes") == 1.0
    assert text_similarity("Error Codes", "Error Codes List") > 0.70
    assert text_similarity("Alpha", "Omega") < 0.30

    assert token_jaccard_similarity("The device inﬂates", "The device inﬂates slowly") > 0.60
    assert token_jaccard_similarity("Apple banana", "Orange peach") == 0.0

def test_unified_diff_generation():
    """Verify unified diff output and line metric computation."""
    old_text = "Line 1: 300 cycles\nLine 2: 15% threshold\n"
    new_text = "Line 1: 250 cycles\nLine 2: 10% threshold\nLine 3: Extra note\n"
    
    diff_str, summary = TextDiffer.generate_unified_diff(old_text, new_text, "v1", "v2")
    assert "--- v1" in diff_str
    assert "+++ v2" in diff_str
    assert summary["added_lines"] >= 2
    assert summary["deleted_lines"] >= 2

def test_version_comparison_v1_to_v2(populated_db):
    """Verify change detection between ct200_manual v1 and v2."""
    base_nodes = populated_db.query(SectionNode).filter(SectionNode.document_version == "v1").order_by(SectionNode.order_index).all()
    target_nodes = populated_db.query(SectionNode).filter(SectionNode.document_version == "v2").order_by(SectionNode.order_index).all()
    
    comp_resp = ChangeDetector.compare_versions(
        base_version="v1",
        target_version="v2",
        base_nodes=base_nodes,
        target_nodes=target_nodes
    )
    
    assert comp_resp.total_base_nodes == 27
    assert comp_resp.total_target_nodes == 28
    
    summary = comp_resp.summary
    assert summary["UNCHANGED"] >= 20
    assert summary["MODIFIED"] >= 3
    assert summary["ADDED"] == 1
    
    # Check Section 5.3 is ADDED
    added_comp = next((c for c in comp_resp.comparisons if c.change_type == ChangeType.ADDED), None)
    assert added_comp is not None
    assert "data-export" in added_comp.logical_id or "5.3" in (added_comp.target_section_number or "")
    
    # Check Section 4.2 Error Codes is MODIFIED with unified diff
    mod_4_2 = next((c for c in comp_resp.comparisons if c.base_section_number == "4.2"), None)
    assert mod_4_2 is not None
    assert mod_4_2.change_type == ChangeType.MODIFIED
    assert mod_4_2.unified_diff is not None
    assert "E6" in mod_4_2.unified_diff or "1.5" in mod_4_2.unified_diff
