# Tri9T Manual Intelligence Platform

A portfolio-grade document intelligence and QA generation platform built with **Python 3.14**, **FastAPI**, **SQLAlchemy**, and **PyMuPDF / pdfplumber**.

The platform ingests technical manuals (`ct200_manual.pdf` v1 and `ct200_manual_v2.pdf` v2), extracts multi-level section hierarchies, tables, bounding box provenance, and extraction anomaly warnings, performs cross-version matching and unified diffing, manages version-pinned selections, generates grounded QA test ideas (3–5 cases) with strict schema validation, and tracks artifact staleness when documentation changes.

---

## Quick Start & Verification

### 1. Environment Setup
The project uses the local virtual environment in `.venv`:
```powershell
# Verify Python version (Python 3.14+)
.\.venv\Scripts\python.exe -V
```

If reinstalling or setting up from scratch:
```powershell
.\.venv\Scripts\pip.exe install -r requirements.txt
# OR
.\.venv\Scripts\pip.exe install fastapi uvicorn sqlalchemy pydantic pymupdf pdfplumber pytest httpx
```

### 2. Ingest Manuals (v1 and v2)
Run the built-in CLI to ingest both manual versions into the SQLite database:
```powershell
# Ingest Base Manual (v1)
.\.venv\Scripts\python.exe -m app.cli ingest --version v1 --file data/ct200_manual.pdf

# Ingest Revised Manual (v2)
.\.venv\Scripts\python.exe -m app.cli ingest --version v2 --file data/ct200_manual_v2.pdf
```

### 3. Compare Document Versions (v1 -> v2)
Inspect the cross-version changes, unified diffs, and additions:
```powershell
.\.venv\Scripts\python.exe -m app.cli compare --base v1 --target v2
```

### 4. Run Automated Test Suite
Run the 30-test automated pytest suite:
```powershell
.\.venv\Scripts\pytest.exe -o pythonpath=. -v tests/
```
Expected output: **30 passed in ~3s** with 100% pass rate.

### 5. Launch the Platform & View the Frontend Dashboard
Start the FastAPI server:
```powershell
.\.venv\Scripts\uvicorn.exe app.main:app --host 127.0.0.1 --port 8000 --reload
```
Once the server is running, open your web browser to:
- **🎨 Interactive Web Dashboard (Frontend)**: [http://127.0.0.1:8000/dashboard](http://127.0.0.1:8000/dashboard)
  - **1. Document Explorer**: Full hierarchical tree navigation, real-time keyword/error-code search, and extracted tables viewer.
  - **2. Version Diff & Comparison**: Cross-version AST change detection with line-level syntax-highlighted unified diffs (green/red) and filter buttons.
  - **3. Selections & QA Generator**: Dropdown to view pre-seeded QA suites or generate new grounded test cases with strict schema validation.
  - **4. Staleness & Impact Engine**: Continuous audit of test suites against revision manuals with inline drift diffs.
- **⚡ Interactive Swagger API Documentation**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc Documentation**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
- **Health Check**: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

> **💡 Note for Reviewers**: The links above run on your local machine (`127.0.0.1:8000`). Start the server with `uvicorn app.main:app --reload` in your terminal first, then open `http://127.0.0.1:8000/dashboard` in your browser.

---

## Core Capabilities (All 9 Assignment Requirements)

| Capability | HTTP Route | Description |
|---|---|---|
| **1. List Sections** | `GET /api/v1/documents/{version}/sections` | Returns top-level sections for a document version with child counts and content hashes. |
| **2. Retrieve Node** | `GET /api/v1/documents/{version}/nodes/{node_id}` | Retrieves full node details, children, text, bounding box, tables, and warnings. |
| **3. Content Search** | `GET /api/v1/documents/{version}/search?q={query}` | Keyword search with term highlighting and relevance scores. |
| **4. Compare Versions** | `GET /api/v1/compare?base_version=v1&target_version=v2` | Compares nodes across revisions, returning change types and unified diffs. |
| **5. Create Selection** | `POST /api/v1/selections` | Creates named, version-pinned selections of ordered nodes. |
| **6. Retrieve Selection** | `GET /api/v1/selections/{selection_id}` | Retrieves selection details and aggregated text/hash. |
| **7. Generate QA Ideas** | `POST /api/v1/selections/{selection_id}/generate-qa` | Synthesizes 3–5 grounded QA test cases using strict schema validation and bounded retries. |
| **8. Retrieve QA Artifacts** | `GET /api/v1/qa-artifacts` | Retrieves generated artifacts filtered by selection or node. |
| **9. Staleness Analysis** | `GET /api/v1/qa-artifacts/{artifact_id}/staleness` | Evaluates artifact staleness against a target version with severity rating. |

---

## End-to-End Workflow Demonstration

### Step 1: Create a Version-Pinned Selection on v1
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/selections" \
     -H "Content-Type: application/json" \
     -d '{
       "name": "Safety Systems Suite",
       "document_version": "v1",
       "node_ids": [
         "v1_sec_4_1_overpressure-protection",
         "v1_sec_4_2_error-codes"
       ]
     }'
```

### Step 2: Generate Grounded QA Test Ideas
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/selections/{selection_id}/generate-qa" \
     -H "Content-Type: application/json" \
     -d '{"force_regenerate": false}'
```

### Step 3: Check Staleness When Ingesting v2
```bash
curl "http://127.0.0.1:8000/api/v1/qa-artifacts/{artifact_id}/staleness?target_version=v2"
```
The platform detects that Section 4.2 Error Codes had content drift (+1 line, -1 line, added error code E6 and reduced deflation time from 2.0s to 1.5s), flags the artifact as `is_stale: true`, assigns `overall_severity: HIGH`, and provides a unified diff and remediation recommendation.

---

## Architecture & Documentation Index

Comprehensive documentation is provided in the `docs/` directory:
- [API Reference (`docs/api.md`)](docs/api.md): Complete route documentation with curl commands and sample payloads.
- [Architecture & Design Decisions (`docs/architecture.md`)](docs/architecture.md): System architecture, technology choices, node identity strategy, and matching heuristics.
- [Edge Cases & Limitations (`docs/edge_cases.md`)](docs/edge_cases.md): Deep-dive into irregular numbering, missing intermediate headings, duplicate titles, and page break continuations.
- [Decision Log (`docs/decision_log.md`)](docs/decision_log.md): Rigorous answers to the three assignment architectural questions.
- [Git Commit Plan (`docs/git_commit_plan.md`)](docs/git_commit_plan.md): Incremental milestone commit structure.
- [Submission Email Draft (`docs/submission_email.md`)](docs/submission_email.md): Submission letter for the evaluation team.

---

## Project Structure

```
Tri9T-Manual-Intelligence/
├── app/
│   ├── core/           # Config, database engine, logging
│   ├── ingestion/      # PyMuPDF extractor, pdfplumber table parser, provenance
│   ├── hierarchy/      # Node identity, SHA-256 hasher, tree builder, normalizer
│   ├── diffing/        # Heuristic cross-version matcher, change detector, differ
│   ├── models/         # SQLAlchemy ORM models (Document, Node, Selection, QAArtifact, Staleness)
│   ├── schemas/        # Strict Pydantic v2 schemas
│   ├── llm/            # BaseLLMProvider, MockLLMProvider, LiveHTTPLLMProvider, validator
│   ├── staleness/      # Staleness & impact severity analysis engine
│   ├── api/            # FastAPI route handlers for all capabilities
│   ├── static/         # Interactive Single-Page Dashboard (dashboard.html)
│   ├── main.py         # FastAPI application entrypoint
│   └── cli.py          # Command-line interface tool
├── data/
│   ├── ct200_manual.pdf        # Base document (v1)
│   ├── ct200_manual_v2.pdf     # Revised document (v2)
│   └── manual_intelligence.db  # Generated SQLite persistence store
├── docs/               # System documentation, design decisions, and decision log
├── tests/              # 30-test automated pytest suite
├── .gitignore          # Git ignore rules
├── .env.example        # Environment variable configuration template
└── README.md           # This document
```
