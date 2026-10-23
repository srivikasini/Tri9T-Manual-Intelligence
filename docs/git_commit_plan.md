# Git Commit & Milestone Plan — Tri9T Manual Intelligence Platform

This plan outlines the structured, incremental commit milestones used to develop, test, and release the platform.

---

## Milestone 1: Project Foundation & Environment Configuration
- **Commit**: `feat(core): initialize project workspace, environment configs, and git hygiene`
- **Scope**:
  - Add `.gitignore` for Python, virtual environments, and SQLite database files.
  - Create `.env.example` with application and LLM provider configuration keys.
  - Implement `app/core/config.py` and `app/core/logging.py`.
  - Establish `app/core/database.py` with SQLAlchemy engine and declarative base.

---

## Milestone 2: Domain Models & Schema Contracts
- **Commit**: `feat(models): implement relational database models and strict pydantic schemas`
- **Scope**:
  - Define `Document`, `DocumentVersion`, `SectionNode`, `Selection`, `SelectionNode`, `QAArtifact`, and `StalenessCheck` ORM models.
  - Create complete Pydantic v2 schemas (`app/schemas/`) for documents, nodes, diffing, selections, QA test ideas, and staleness evaluations.

---

## Milestone 3: PDF Ingestion & Hierarchy Normalization
- **Commit**: `feat(ingestion): implement PDF layout parsing, table extraction, and hierarchy normalizer`
- **Scope**:
  - Implement PyMuPDF font-size and boldness heading detector.
  - Implement `pdfplumber` multi-row table extraction with spurious border fragment filtering.
  - Implement `app/hierarchy/identity.py` for stable cross-version logical IDs.
  - Implement `app/hierarchy/hasher.py` for deterministic SHA-256 content hashing.
  - Handle missing intermediate headings, out-of-order numbering, and duplicate titles under different parents.

---

## Milestone 4: Cross-Version Matching & Change Detection
- **Commit**: `feat(diffing): implement heuristic node matcher, change detector, and unified diff generator`
- **Scope**:
  - Implement multi-factor matching (logical ID, section number, heading similarity, token Jaccard).
  - Implement change categorization: `UNCHANGED`, `MODIFIED`, `ADDED`, `REMOVED`, `MOVED`.
  - Generate unified line diffs with addition/deletion metrics.
  - Track matching confidence scores and ambiguity flags.

---

## Milestone 5: LLM Provider Abstraction & Strict Output Validation
- **Commit**: `feat(llm): implement pluggable LLM provider, deterministic mock synthesizer, and bounded validator`
- **Scope**:
  - Define `BaseLLMProvider` interface.
  - Implement `MockLLMProvider` with grounded assertions and failure injection modes (timeout, malformed JSON, invalid count, missing fields).
  - Implement `LiveHTTPLLMProvider` with automatic fallback.
  - Implement `QAOutputValidator` enforcing 3-to-5 test count constraints and bounded corrective retries.

---

## Milestone 6: Staleness & Impact Analysis Engine
- **Commit**: `feat(staleness): implement artifact staleness detector and impact severity scoring`
- **Scope**:
  - Compare stored source hashes and snapshots against target version nodes.
  - Detect content drift (`HASH_DRIFT`), node removals (`NODE_REMOVED`), and structural shifts (`NODE_MOVED`).
  - Implement severity classification: `HIGH` (parameter/safety changes), `MEDIUM` (wording/procedural changes), `LOW` (formatting/structural relocations).

---

## Milestone 7: FastAPI REST API & Ingestion CLI
- **Commit**: `feat(api): implement REST API endpoints for all 9 assignment capabilities and CLI tool`
- **Scope**:
  - Implement endpoints for listing sections, node retrieval, search, version comparison, selections, QA generation, and staleness checks.
  - Implement global exception handlers preventing internal stack trace leaks.
  - Build `app/cli.py` for command-line ingestion, comparison, and staleness checks.

---

## Milestone 8: Comprehensive Automated Test Suite
- **Commit**: `test: add automated test suite covering extraction edge cases, diffing, selections, LLM, and staleness`
- **Scope**:
  - Create pytest test fixtures using SQLite `StaticPool`.
  - Add tests for 5 extraction edge cases.
  - Add tests for version matching and diffing.
  - Add tests for LLM schema enforcement and bounded retry recovery.
  - Add integration tests for all 9 API capabilities and HTTP error codes.

---

## Milestone 9: Documentation & Submission Release
- **Commit**: `docs: add comprehensive README, API reference, architecture guide, edge case analysis, and decision log`
- **Scope**:
  - Author comprehensive `README.md`.
  - Author `docs/api.md`, `docs/architecture.md`, `docs/edge_cases.md`, and `docs/decision_log.md`.
  - Prepare `docs/submission_email.md`.
