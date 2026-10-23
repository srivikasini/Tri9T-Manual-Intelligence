# Architectural Decision Log — Tri9T Manual Intelligence Platform

This document addresses the three core architectural questions specified in the Project Master Brief, documenting deliberate engineering trade-offs, silent error failure modes, and boundary behaviors.

---

## Question 1: What is the most likely silent wrong result, and how will it be detected?

### The Failure Mode: False-Equivalence in Cross-Version Node Matching
The most dangerous failure in an automated document intelligence system is **false equivalence**—silently assuming two sections across document versions are identical or equivalent when they have actually diverged semantically or procedure-wise.

Specifically, in technical manuals:
- **Case A**: A section is heavily rephrased or split into two sub-sections, but retains a high token overlap (Jaccard similarity ~ 0.70). An aggressive heuristic matcher could pair the revised section to the wrong sub-section.
- **Case B**: A section title remains unchanged (e.g., `4.3 Alarm Thresholds`), but the internal technical parameter is revised from `E1–E5` to `E1–E6` and deflation time changes from `2.0s` to `1.5s`. If matching relied solely on heading equality without content hashing, the system would silently declare the section `UNCHANGED`.

### Detection & Mitigation Strategy
1. **Cryptographic Content Hashing (SHA-256)**:
   - Logical equivalence is completely decoupled from content equality.
   - Even if two nodes share an exact `logical_id` with 100% matching confidence, the platform compares their `content_hash`. Any alteration in characters, punctuation, numbers, or table cells marks the node as `MODIFIED` rather than `UNCHANGED`.
2. **Ambiguity Flagging (`is_ambiguous = True`)**:
   - If two or more candidate target nodes match a base node with a confidence score difference of less than `0.10`, the match is explicitly flagged as ambiguous.
   - Ambiguous matches are exposed through the API (`GET /api/v1/compare`) and in staleness checks, alerting QA engineers to review the match manually rather than silently accepting it.
3. **Structured Audit Diffs**:
   - Whenever a node is marked `MODIFIED`, unified line-by-line diffs are stored and returned, making the exact additions and deletions human-inspectable.

---

## Question 2: Where was simplicity chosen over correctness, and what breaks as a result?

### The Trade-off: Deterministic Single-Column Reading Order vs. Multi-Column Flow Segmentation

#### What was chosen:
In `app/ingestion/pdf_extractor.py`, text blocks within each page are sorted primarily by vertical coordinate (`y0`) from top to bottom:
```python
blocks.sort(key=lambda b: b[1])  # sort by y0
```

#### Why simplicity was chosen:
For standard medical, regulatory, and engineering manuals (such as the CardioTrack CT-200 manual), content flows predominantly top-to-bottom in a single primary column, with occasional inline tables or specification blocks. Implementing full XY-Cut, Voronoi tessellation, or deep learning document layout models (e.g. LayoutLM) introduces massive C-library compilation dependencies, non-deterministic inference latencies, and platform fragility without adding value for linear manuals.

#### What breaks as a result:
If an ingested PDF features a strict multi-column layout (such as a 3-column academic journal article or newspaper):
1. **Interleaved Text**: The extractor will read horizontally across columns at each vertical band (Line 1 Col 1 -> Line 1 Col 2 -> Line 1 Col 3) instead of reading down Column 1 first.
2. **Broken Sentence Flow**: Paragraph continuation logic across page breaks would fail because sentences would appear split and interleaved with adjacent column text.

#### Path to Full Production Generalization:
To support multi-column layouts in the future without adding heavy neural models, a lightweight vertical gutter detection pass can be introduced before block sorting to segment pages into distinct column bounding boxes.

---

## Question 3: What input is unsupported, and how does the system behave?

### 1. Pure Scanned Bitmap Images Without Embedded Text
- **Unsupported Input**: A PDF created by scanning physical paper with a photocopier where pages are stored exclusively as raster images (JPEG/PNG) without an embedded OCR text stream.
- **System Behavior**:
  - `pymupdf.open()` opens the PDF successfully, but `page.get_text("dict")["blocks"]` returns zero text blocks.
  - The extraction pipeline logs a warning and initializes the document fallback root (`doc_root: "Document Overview"`).
  - The ingestion succeeds with `total_nodes_extracted = 1` and `page_count = N`, but full text will be empty.
  - The system does not crash or corrupt the database.

### 2. Encrypted or Password-Protected PDFs
- **Unsupported Input**: A PDF with an owner/user password or AES-256 certificate encryption.
- **System Behavior**:
  - `pymupdf.open()` detects `doc.is_encrypted == True`.
  - The API catches the exception and returns a structured `400 Bad Request` or `422 Unprocessable Entity` with message: `"PDF is password-protected or encrypted and cannot be parsed"`.
  - No corrupted records are written to SQLite.

### 3. Non-PDF Files Submitted to Ingestion Endpoint
- **Unsupported Input**: Submitting a Word (`.docx`), Markdown (`.md`), or image file directly to `/api/v1/ingest`.
- **System Behavior**:
  - `pymupdf.open()` raises `pymupdf.FileDataError`.
  - Caught cleanly by FastAPI error handling, returning `400 Bad Request` with message: `"Cannot open file as PDF: unsupported document format"`.

### 4. Selection Payloads Referencing Non-Existent or Cross-Version Nodes
- **Unsupported Input**: A selection request (`POST /api/v1/selections`) providing node IDs from version `v2` while `document_version` is specified as `v1`.
- **System Behavior**:
  - The validation layer verifies that every requested node ID exists specifically within the targeted `document_version`.
  - If any ID fails validation, the request is rejected with `400 Bad Request`: `"The following node IDs were not found in version 'v1': [...]"`.
  - Foreign key and relational constraints ensure orphan selection links cannot be created.
