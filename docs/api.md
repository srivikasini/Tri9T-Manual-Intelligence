# Tri9T Manual Intelligence Platform — API Reference

The Tri9T Manual Intelligence API is built with FastAPI and provides fully-typed REST endpoints for document ingestion, hierarchical section navigation, full-text search, cross-version diffing, named selections, grounded LLM QA generation, and staleness/impact analysis.

Interactive OpenAPI documentation is available locally at:
- **Swagger UI**: `http://127.0.0.1:8000/docs`
- **ReDoc**: `http://127.0.0.1:8000/redoc`

All endpoints are prefixed with `/api/v1`.

---

## 1. Document & Ingestion Endpoints

### 1.1 Ingest Document Version
- **Method**: `POST`
- **Endpoint**: `/api/v1/ingest`
- **Description**: Ingests a PDF document into the platform, parsing layout blocks, headings, tables, provenance coordinates, and extraction anomalies.
- **Request Body**:
  ```json
  {
    "file_path": "data/ct200_manual.pdf",
    "version_id": "v1",
    "document_id": "ct200_manual"
  }
  ```
- **Example Response** (`200 OK`):
  ```json
  {
    "document_id": "ct200_manual",
    "version_id": "v1",
    "filename": "ct200_manual.pdf",
    "file_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "page_count": 6,
    "total_nodes_extracted": 27,
    "top_level_sections_count": 8,
    "warnings": [
      "Missing intermediate heading level between 2.1 and 2.1.1.1",
      "Irregular/out-of-order numbering: section 3.4 directly followed 3.2",
      "Duplicate heading title 'Error Codes' under different parent sections (sections: ['4.2', '7.1'])"
    ]
  }
  ```

### 1.2 List Ingested Versions
- **Method**: `GET`
- **Endpoint**: `/api/v1/documents`
- **Example Response** (`200 OK`):
  ```json
  [
    {
      "version_id": "v1",
      "document_id": "ct200_manual",
      "filename": "ct200_manual.pdf",
      "file_hash": "e3b0c4...",
      "page_count": 6,
      "ingested_at": "2026-10-23T08:41:57Z"
    },
    {
      "version_id": "v2",
      "document_id": "ct200_manual",
      "filename": "ct200_manual_v2.pdf",
      "file_hash": "4a71bc...",
      "page_count": 7,
      "ingested_at": "2026-10-23T08:42:18Z"
    }
  ]
  ```

---

## 2. Navigation & Content Retrieval Endpoints

### 2.1 List Top-Level Sections (Capability 1)
- **Method**: `GET`
- **Endpoint**: `/api/v1/documents/{version}/sections`
- **Example**: `GET /api/v1/documents/v1/sections`
- **Example Response** (`200 OK`):
  ```json
  [
    {
      "id": "v1_sec_1_device-overview",
      "document_version": "v1",
      "logical_id": "sec:1:device-overview",
      "parent_id": null,
      "title": "Device Overview",
      "section_number": "1",
      "node_type": "section",
      "page_start": 1,
      "page_end": 1,
      "content_hash": "f290d291a5e1...",
      "child_count": 2
    },
    {
      "id": "v1_sec_2_physical-and-electrical-specifications",
      "document_version": "v1",
      "logical_id": "sec:2:physical-and-electrical-specifications",
      "parent_id": null,
      "title": "Physical and Electrical Specifications",
      "section_number": "2",
      "node_type": "section",
      "page_start": 1,
      "page_end": 2,
      "content_hash": "b8a1c901e...",
      "child_count": 3
    }
  ]
  ```

### 2.2 Retrieve Node by ID (Capability 2)
- **Method**: `GET`
- **Endpoint**: `/api/v1/documents/{version}/nodes/{node_id}`
- **Example**: `GET /api/v1/documents/v1/nodes/v1_sec_4_2_error-codes`
- **Example Response** (`200 OK`):
  ```json
  {
    "id": "v1_sec_4_2_error-codes",
    "document_version": "v1",
    "logical_id": "sec:4.2:error-codes",
    "parent_id": "v1_sec_4_alarms-and-safety-behavior",
    "title": "Error Codes",
    "section_number": "4.2",
    "full_text": "Code Meaning Device Behavior E1 Cuff not connected or leak detected Aborts measurement, displays E1...",
    "node_type": "subsection",
    "page_start": 4,
    "page_end": 4,
    "bbox": [33.0, 135.8, 128.8, 153.5],
    "tables": [
      {
        "headers": ["Code", "Meaning", "Device Behavior"],
        "rows": [
          ["E1", "Cuff not connected or leak detected", "Aborts measurement, displays E1"],
          ["E2", "Motion artifact detected during measurement", "Aborts measurement, displays E2, prompts retry"],
          ["E3", "Overpressure condition", "Auto-deflates within 2 seconds, displays E3"],
          ["E4", "Low battery during measurement", "Aborts measurement, displays E4"],
          ["E5", "Internal sensor fault", "Device disables measurement function, displays E5 until serviced"]
        ],
        "page": 4
      }
    ],
    "content_hash": "9c12a78b54f...",
    "extraction_warnings": [
      "Duplicate heading title 'Error Codes' under different parent sections (sections: ['4.2', '7.1'])"
    ],
    "order_index": 14,
    "children": []
  }
  ```

### 2.3 Search Document Content (Capability 3)
- **Method**: `GET`
- **Endpoint**: `/api/v1/documents/{version}/search?q={query}&limit=10`
- **Example**: `GET /api/v1/documents/v1/search?q=overpressure`
- **Example Response** (`200 OK`):
  ```json
  {
    "query": "overpressure",
    "document_version": "v1",
    "total_matches": 3,
    "results": [
      {
        "node_id": "v1_sec_4_1_overpressure-protection",
        "document_version": "v1",
        "logical_id": "sec:4.1:overpressure-protection",
        "title": "Overpressure Protection",
        "section_number": "4.1",
        "matched_snippet": "...If cuff pressure exceeds 299 mmHg at any point, or exceeds 300 mmHg, the device immediately aborts...",
        "page": 4,
        "score": 5.0
      }
    ]
  }
  ```

---

## 3. Version Comparison & Diffing (Capability 4)

### 3.1 Cross-Version Comparison
- **Method**: `GET`
- **Endpoint**: `/api/v1/compare?base_version=v1&target_version=v2`
- **Example Response** (`200 OK`):
  ```json
  {
    "base_version": "v1",
    "target_version": "v2",
    "total_base_nodes": 27,
    "total_target_nodes": 28,
    "summary": {
      "UNCHANGED": 23,
      "MODIFIED": 4,
      "ADDED": 1
    },
    "comparisons": [
      {
        "logical_id": "sec:4.2:error-codes",
        "change_type": "MODIFIED",
        "matching_confidence": 1.0,
        "is_ambiguous": false,
        "base_node_id": "v1_sec_4_2_error-codes",
        "base_section_number": "4.2",
        "target_node_id": "v2_sec_4_2_error-codes",
        "target_section_number": "4.2",
        "unified_diff": "--- v1:4.2\n+++ v2:4.2\n@@ -1 +1 @@\n-Auto-deflates within 2 seconds...\n+Auto-deflates within 1.5 seconds... E6 Bluetooth sync failure...",
        "diff_summary": {
          "added_lines": 1,
          "deleted_lines": 1
        },
        "explanation": "Section content has changed"
      },
      {
        "logical_id": "sec:5.3:data-export",
        "change_type": "ADDED",
        "matching_confidence": 1.0,
        "is_ambiguous": false,
        "target_node_id": "v2_sec_5_3_data-export",
        "target_section_number": "5.3",
        "explanation": "Section 5.3 'Data Export' was added in v2"
      }
    ]
  }
  ```

---

## 4. Selections Management (Capabilities 5 & 6)

### 4.1 Create Selection
- **Method**: `POST`
- **Endpoint**: `/api/v1/selections`
- **Request Body**:
  ```json
  {
    "name": "Safety Systems Test Suite",
    "document_version": "v1",
    "description": "Validation suite for alarms and overpressure mechanisms",
    "node_ids": [
      "v1_sec_4_1_overpressure-protection",
      "v1_sec_4_2_error-codes"
    ]
  }
  ```
- **Example Response** (`201 Created`):
  ```json
  {
    "id": "sel_afbaa803e321",
    "name": "Safety Systems Test Suite",
    "description": "Validation suite for alarms and overpressure mechanisms",
    "document_version": "v1",
    "node_count": 2,
    "created_at": "2026-10-23T08:43:28Z"
  }
  ```

### 4.2 Retrieve Selection Detail
- **Method**: `GET`
- **Endpoint**: `/api/v1/selections/{selection_id}`
- **Example Response** (`200 OK`):
  ```json
  {
    "id": "sel_afbaa803e321",
    "name": "Safety Systems Test Suite",
    "document_version": "v1",
    "node_count": 2,
    "created_at": "2026-10-23T08:43:28Z",
    "selected_nodes": [
      {
        "node_id": "v1_sec_4_1_overpressure-protection",
        "logical_id": "sec:4.1:overpressure-protection",
        "title": "Overpressure Protection",
        "section_number": "4.1",
        "full_text": "If cuff pressure exceeds 299 mmHg...",
        "content_hash": "a1b2...",
        "page_start": 4,
        "page_end": 4,
        "tables": []
      }
    ],
    "aggregated_text": "### Section 4.1: Overpressure Protection\nIf cuff pressure exceeds 299 mmHg...\n\n### Section 4.2: Error Codes\n...",
    "aggregated_hash": "c83f9104..."
  }
  ```

---

## 5. QA Artifact Generation & Retrieval (Capabilities 7 & 8)

### 5.1 Generate QA Test Ideas
- **Method**: `POST`
- **Endpoint**: `/api/v1/selections/{selection_id}/generate-qa`
- **Request Body**:
  ```json
  {
    "force_regenerate": false,
    "custom_instructions": "Focus specifically on overpressure safety margins"
  }
  ```
- **Example Response** (`201 Created`):
  ```json
  {
    "id": "qa_5635388e121f",
    "selection_id": "sel_afbaa803e321",
    "document_version": "v1",
    "source_node_ids": [
      "v1_sec_4_1_overpressure-protection",
      "v1_sec_4_2_error-codes"
    ],
    "source_snapshots": {
      "v1_sec_4_1_overpressure-protection": "If cuff pressure exceeds 299 mmHg at any point...",
      "v1_sec_4_2_error-codes": "Code Meaning Device Behavior E1..."
    },
    "source_hashes": {
      "v1_sec_4_1_overpressure-protection": "a1b2c3d4...",
      "v1_sec_4_2_error-codes": "e5f6g7h8..."
    },
    "test_cases": [
      {
        "test_id": "TC-01",
        "test_objective": "Verify overpressure protection triggers safety auto-deflation within specified time threshold",
        "preconditions": [
          "CardioTrack CT-200 connected to pneumatic test fixture with calibrated pressure sensor",
          "Device powered on with User 1 profile active"
        ],
        "steps": [
          "Initiate blood pressure measurement sequence by pressing Start button",
          "Simulate cuff occlusion causing pneumatic pressure to exceed 299 mmHg",
          "Measure duration between overpressure threshold exceedance and valve release",
          "Observe device display for generated error code"
        ],
        "expected_result": "Device must immediately abort inflation, trigger auto-deflate valve within 1.5-2.0 seconds, and display error code E3.",
        "source_references": ["Section 4.1", "Section 4.2"]
      },
      {
        "test_id": "TC-02",
        "test_objective": "Verify motion artifact detection halts measurement and instructs user to retry",
        "preconditions": [
          "CT-200 standard cuff fitted snugly around human subject or simulated arm mannequin",
          "Device powered on in resting position"
        ],
        "steps": [
          "Press Start button to initiate cuff inflation",
          "During oscillometric measurement cycle, induce continuous arm motion for 3 seconds",
          "Observe system response and display output"
        ],
        "expected_result": "System detects motion artifact, aborts measurement, releases cuff pressure, displays error code E2, and prompts retry.",
        "source_references": ["Section 4.2", "Section 3.2"]
      },
      {
        "test_id": "TC-03",
        "test_objective": "Verify automatic shutoff engages after 60 seconds of inactivity to conserve battery power",
        "preconditions": [
          "CT-200 powered by four fresh AA alkaline batteries",
          "Device powered on and idle at main profile selection screen"
        ],
        "steps": [
          "Power on device by pressing power button for one second",
          "Leave device unattended with no button presses or cuff connection",
          "Record time elapsed until display turns off completely"
        ],
        "expected_result": "Device automatically powers down after exactly 60 seconds of inactivity.",
        "source_references": ["Section 3.4", "Section 2.1.1.1"]
      }
    ],
    "validation_status": "VALID",
    "provider_info": {
      "provider": "mock",
      "model": "grounded-rule-synthesizer-v1",
      "deterministic": true,
      "attempts": 1
    },
    "created_at": "2026-10-23T08:43:28Z"
  }
  ```

### 5.2 Retrieve Artifact by ID
- **Method**: `GET`
- **Endpoint**: `/api/v1/qa-artifacts/{artifact_id}`
- **Example Response** (`200 OK`): Full QAArtifact payload as above.

---

## 6. Staleness & Impact Analysis (Capability 9)

### 6.1 Check Artifact Staleness
- **Method**: `GET`
- **Endpoint**: `/api/v1/qa-artifacts/{artifact_id}/staleness?target_version=v2`
- **Example Response** (`200 OK`):
  ```json
  {
    "artifact_id": "qa_5635388e121f",
    "selection_id": "sel_afbaa803e321",
    "base_version": "v1",
    "target_version": "v2",
    "is_stale": true,
    "overall_severity": "HIGH",
    "total_source_nodes": 2,
    "affected_nodes_count": 1,
    "reasons": [
      {
        "node_id": "v1_sec_4_2_error-codes",
        "logical_id": "sec:4.2:error-codes",
        "drift_type": "HASH_DRIFT",
        "severity": "HIGH",
        "description": "Content drift detected in Section 4.2 ('Error Codes'): +1 lines, -1 lines.",
        "stored_hash": "e5f6g7h8...",
        "current_hash": "9c12a78b...",
        "text_diff": "--- v1:4.2\n+++ v2:4.2\n@@ -1 +1 @@\n-Auto-deflates within 2 seconds...\n+Auto-deflates within 1.5 seconds... E6 Bluetooth sync failure..."
      }
    ],
    "recommendation": "Artifact has 1 affected source node(s) with HIGH severity. Regeneration against current version is recommended to preserve test veracity.",
    "checked_at": "2026-10-23T08:47:23Z"
  }
  ```

### 6.2 Batch Staleness Evaluation
- **Method**: `GET`
- **Endpoint**: `/api/v1/staleness?target_version=v2`
- **Example Response** (`200 OK`):
  ```json
  {
    "target_version": "v2",
    "total_artifacts_evaluated": 1,
    "stale_artifacts_count": 1,
    "results": [ ... ]
  }
  ```
