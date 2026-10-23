"""Automated integration tests for FastAPI REST API endpoints."""
import pytest
from fastapi.testclient import TestClient

def test_health_and_root(client: TestClient):
    """Verify health and root endpoints."""
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "healthy"}

    root_resp = client.get("/")
    assert root_resp.status_code == 200
    assert "status" in root_resp.json()

def test_list_document_versions(client: TestClient):
    """Verify document versions listing."""
    resp = client.get("/api/v1/documents")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 2
    version_ids = [d["version_id"] for d in data]
    assert "v1" in version_ids
    assert "v2" in version_ids

def test_capability_1_list_top_level_sections(client: TestClient):
    """Capability 1: Listing top-level sections for a selected document version."""
    resp = client.get("/api/v1/documents/v1/sections")
    assert resp.status_code == 200
    sections = resp.json()
    assert len(sections) == 8
    
    # Check section numbers 1 through 8
    sec_nums = [s["section_number"] for s in sections]
    assert "1" in sec_nums
    assert "2" in sec_nums
    assert "8" in sec_nums
    for s in sections:
        assert s["parent_id"] is None
        assert s["content_hash"] is not None

def test_capability_2_get_node_by_id(client: TestClient):
    """Capability 2: Retrieving a node by ID, including metadata, children, full text and content hash."""
    # First get a top section to know an ID
    sec_resp = client.get("/api/v1/documents/v1/sections")
    top_node_id = sec_resp.json()[0]["id"]
    
    resp = client.get(f"/api/v1/documents/v1/nodes/{top_node_id}")
    assert resp.status_code == 200
    node = resp.json()
    assert node["id"] == top_node_id
    assert "full_text" in node
    assert "content_hash" in node
    assert len(node["content_hash"]) == 64
    assert "children" in node
    assert isinstance(node["children"], list)

def test_capability_3_search_document_content(client: TestClient):
    """Capability 3: Searching document content."""
    resp = client.get("/api/v1/documents/v1/search?q=oscillometric")
    assert resp.status_code == 200
    search_data = resp.json()
    assert search_data["query"] == "oscillometric"
    assert search_data["total_matches"] > 0
    assert len(search_data["results"]) > 0
    first = search_data["results"][0]
    assert "matched_snippet" in first
    assert "oscillometric" in first["matched_snippet"].lower()

def test_capability_4_compare_versions(client: TestClient):
    """Capability 4: Comparing nodes across versions and returning changed status and useful diff."""
    resp = client.get("/api/v1/compare?base_version=v1&target_version=v2")
    assert resp.status_code == 200
    diff_data = resp.json()
    assert diff_data["base_version"] == "v1"
    assert diff_data["target_version"] == "v2"
    assert diff_data["total_base_nodes"] == 27
    assert diff_data["total_target_nodes"] == 28
    
    summary = diff_data["summary"]
    assert "UNCHANGED" in summary
    assert "MODIFIED" in summary
    assert "ADDED" in summary
    assert summary["ADDED"] == 1

def test_capability_5_and_6_selections_workflow(client: TestClient):
    """Capabilities 5 & 6: Create named selection and retrieve selected content."""
    # Find two node IDs in v1
    sec_resp = client.get("/api/v1/documents/v1/sections")
    nodes = sec_resp.json()[:2]
    node_ids = [n["id"] for n in nodes]
    
    # Create selection
    payload = {
        "name": "Integration Test Selection",
        "document_version": "v1",
        "description": "API verification selection",
        "node_ids": node_ids
    }
    create_resp = client.post("/api/v1/selections", json=payload)
    assert create_resp.status_code == 201
    sel = create_resp.json()
    assert sel["name"] == payload["name"]
    assert sel["node_count"] == 2
    selection_id = sel["id"]
    
    # Retrieve selection
    get_resp = client.get(f"/api/v1/selections/{selection_id}")
    assert get_resp.status_code == 200
    sel_detail = get_resp.json()
    assert sel_detail["id"] == selection_id
    assert len(sel_detail["selected_nodes"]) == 2
    assert len(sel_detail["aggregated_text"]) > 0
    assert len(sel_detail["aggregated_hash"]) == 64

def test_capability_7_and_8_qa_generation_workflow(client: TestClient):
    """Capabilities 7 & 8: Generate 3-5 QA test ideas and retrieve artifact."""
    # Create selection
    sec_resp = client.get("/api/v1/documents/v1/sections")
    node_ids = [sec_resp.json()[0]["id"]]
    sel_resp = client.post("/api/v1/selections", json={
        "name": "QA Test Suite",
        "document_version": "v1",
        "node_ids": node_ids
    })
    selection_id = sel_resp.json()["id"]
    
    # Generate QA ideas
    gen_resp = client.post(f"/api/v1/selections/{selection_id}/generate-qa", json={"force_regenerate": True})
    assert gen_resp.status_code == 201
    artifact = gen_resp.json()
    assert artifact["selection_id"] == selection_id
    assert 3 <= len(artifact["test_cases"]) <= 5
    assert artifact["validation_status"] in ["VALID", "REPAIRED_ON_RETRY"]
    artifact_id = artifact["id"]
    
    # Retrieve artifact by ID
    get_art = client.get(f"/api/v1/qa-artifacts/{artifact_id}")
    assert get_art.status_code == 200
    assert get_art.json()["id"] == artifact_id

    # Retrieve artifacts list by selection ID
    list_art = client.get(f"/api/v1/qa-artifacts?selection_id={selection_id}")
    assert list_art.status_code == 200
    assert len(list_art.json()) >= 1

def test_capability_9_staleness_and_impact(client: TestClient):
    """Capability 9: Checking and retrieving staleness and impact information."""
    # Create selection containing modified Section 4.2 Error Codes
    node_4_2_resp = client.get("/api/v1/documents/v1/search?q=Error+Codes")
    node_4_2_id = node_4_2_resp.json()["results"][0]["node_id"]
    
    sel_resp = client.post("/api/v1/selections", json={
        "name": "Staleness API Test",
        "document_version": "v1",
        "node_ids": [node_4_2_id]
    })
    selection_id = sel_resp.json()["id"]
    
    # Generate QA
    gen_resp = client.post(f"/api/v1/selections/{selection_id}/generate-qa", json={"force_regenerate": True})
    artifact_id = gen_resp.json()["id"]
    
    # Check staleness
    stale_resp = client.get(f"/api/v1/qa-artifacts/{artifact_id}/staleness?target_version=v2")
    assert stale_resp.status_code == 200
    stale_data = stale_resp.json()
    assert stale_data["artifact_id"] == artifact_id
    assert stale_data["is_stale"] is True
    assert stale_data["overall_severity"] in ["HIGH", "MEDIUM"]
    assert len(stale_data["reasons"]) >= 1

    # Batch check
    batch_resp = client.get("/api/v1/staleness?target_version=v2")
    assert batch_resp.status_code == 200
    batch_data = batch_resp.json()
    assert batch_data["total_artifacts_evaluated"] >= 1

def test_api_error_handling_and_status_codes(client: TestClient):
    """Verify appropriate HTTP status codes (404, 400, 422) and safe error payloads."""
    # 404 on invalid version
    resp = client.get("/api/v1/documents/v999/sections")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()

    # 404 on invalid node
    resp = client.get("/api/v1/documents/v1/nodes/non_existent_node_uuid")
    assert resp.status_code == 404

    # 400 on invalid node in selection
    resp = client.post("/api/v1/selections", json={
        "name": "Bad Selection",
        "document_version": "v1",
        "node_ids": ["invalid_uuid"]
    })
    assert resp.status_code == 400

    # 422 on missing required field
    resp = client.post("/api/v1/selections", json={
        "document_version": "v1"
        # missing name and node_ids
    })
    assert resp.status_code == 422
