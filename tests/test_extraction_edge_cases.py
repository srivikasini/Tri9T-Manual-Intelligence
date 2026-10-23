"""Automated tests for document extraction edge cases."""
import pytest
from pathlib import Path
from app.ingestion.pdf_extractor import PDFExtractor
from app.ingestion.table_parser import TableParser
from app.hierarchy.tree_builder import HierarchyTreeBuilder

def test_missing_intermediate_heading_level():
    """Verify detection of missing intermediate heading level (2.1 to 2.1.1.1 without 2.1.1)."""
    res = PDFExtractor.extract_document(Path("data/ct200_manual.pdf"), "v1")
    warnings = res["global_warnings"]
    
    # Check warning was raised
    assert any("Missing intermediate heading level" in w and "2.1.1.1" in w for w in warnings)
    
    # Check hierarchy builder linked 2.1.1.1 under 2.1
    normalized = HierarchyTreeBuilder.build_hierarchy(res["raw_sections"], "v1")
    node_map = {n.section_number: n for n in normalized if n.section_number}
    
    node_2_1 = node_map.get("2.1")
    node_2_1_1_1 = node_map.get("2.1.1.1")
    
    assert node_2_1 is not None
    assert node_2_1_1_1 is not None
    assert node_2_1_1_1.parent_id == node_2_1.node_id

def test_irregular_and_out_of_order_numbering():
    """Verify detection of out-of-order numbering (Section 3.4 preceding Section 3.3)."""
    res = PDFExtractor.extract_document(Path("data/ct200_manual.pdf"), "v1")
    warnings = res["global_warnings"]
    
    assert any("Irregular/out-of-order numbering" in w and "3.4" in w for w in warnings)
    assert any("Irregular/out-of-order numbering" in w and "3.3" in w for w in warnings)

def test_duplicate_headings_under_different_parents():
    """Verify handling of duplicate heading titles ('Error Codes' under 4.2 and 7.1)."""
    res = PDFExtractor.extract_document(Path("data/ct200_manual.pdf"), "v1")
    warnings = res["global_warnings"]
    
    assert any("Duplicate heading title 'Error Codes'" in w for w in warnings)
    
    normalized = HierarchyTreeBuilder.build_hierarchy(res["raw_sections"], "v1")
    error_nodes = [n for n in normalized if n.title == "Error Codes"]
    
    assert len(error_nodes) == 2
    # Ensure they have distinct logical IDs and parent IDs
    assert error_nodes[0].logical_id != error_nodes[1].logical_id
    assert error_nodes[0].parent_id != error_nodes[1].parent_id
    assert "4.2" in error_nodes[0].section_number or "7.1" in error_nodes[0].section_number
    assert "4.2" in error_nodes[1].section_number or "7.1" in error_nodes[1].section_number

def test_page_break_continuation():
    """Verify that multi-page sections properly capture content spanning page boundaries."""
    res = PDFExtractor.extract_document(Path("data/ct200_manual_v2.pdf"), "v2")
    sections = res["raw_sections"]
    
    # Section 4.3 starts on page 4 and continues onto page 5 in v2
    sec_4_3 = next((s for s in sections if s.section_number == "4.3"), None)
    assert sec_4_3 is not None
    assert sec_4_3.page_start == 4
    assert sec_4_3.page_end == 5
    
    # Section 6.1 starts on page 5 and continues onto page 6 in v2
    sec_6_1 = next((s for s in sections if s.section_number == "6.1"), None)
    assert sec_6_1 is not None
    assert sec_6_1.page_start == 5
    assert sec_6_1.page_end == 6

def test_table_extraction_and_cell_integrity():
    """Verify accurate extraction of multi-row tables and header cell values."""
    tables_v1 = TableParser.extract_tables_from_pdf(Path("data/ct200_manual.pdf"))
    assert len(tables_v1) >= 2
    
    # Find Error Codes table
    err_table = next((t for t in tables_v1 if "Code" in t["headers"]), None)
    assert err_table is not None
    assert "Meaning" in err_table["headers"]
    assert "Device Behavior" in err_table["headers"]
    
    # Verify rows in v1 (E1 through E5)
    row_codes = [r[0] for r in err_table["rows"]]
    assert "E1" in row_codes
    assert "E2" in row_codes
    assert "E3" in row_codes
    assert "E4" in row_codes
    assert "E5" in row_codes

    # Verify v2 has added row E6
    tables_v2 = TableParser.extract_tables_from_pdf(Path("data/ct200_manual_v2.pdf"))
    err_table_v2 = next((t for t in tables_v2 if "Code" in t["headers"]), None)
    assert err_table_v2 is not None
    row_codes_v2 = [r[0] for r in err_table_v2["rows"]]
    assert "E6" in row_codes_v2
    assert len(err_table_v2["rows"]) == len(err_table["rows"]) + 1
