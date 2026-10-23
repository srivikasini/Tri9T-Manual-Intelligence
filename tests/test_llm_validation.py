"""Automated tests for LLM output validation, failure handling, and retry mechanics."""
import pytest
from app.llm.mock_provider import MockLLMProvider
from app.llm.validator import QAOutputValidator, QAValidationError
from app.schemas.qa import QAGenerationPayload, QAGenerateRequest
from app.api.qa import generate_qa_test_ideas
from app.models.selection import Selection, SelectionNode
from app.models.node import SectionNode

SAMPLE_CONTEXT = """
### Section 4.1: Overpressure Protection
If cuff pressure exceeds 299 mmHg at any point, or exceeds 300 mmHg, the device immediately aborts.

### Section 4.2: Error Codes
E1: Cuff not connected
E2: Motion artifact detected
E3: Overpressure condition. Auto-deflates within 2 seconds.
"""

def test_successful_llm_generation_and_schema_validation():
    """Verify that MockLLMProvider produces schema-compliant test cases within 3 to 5 count."""
    provider = MockLLMProvider()
    payload, status, info = QAOutputValidator.generate_and_validate(
        provider=provider,
        context_text=SAMPLE_CONTEXT,
        max_retries=2
    )
    
    assert status == "VALID"
    assert 3 <= len(payload.test_cases) <= 5
    for tc in payload.test_cases:
        assert tc.test_id.startswith("TC-")
        assert len(tc.test_objective) > 10
        assert len(tc.preconditions) >= 1
        assert len(tc.steps) >= 1
        assert len(tc.expected_result) > 5
        assert len(tc.source_references) >= 1

def test_llm_timeout_failure():
    """Verify that provider timeouts raise TimeoutError."""
    provider = MockLLMProvider(failure_mode="TIMEOUT")
    with pytest.raises(QAValidationError) as exc_info:
        QAOutputValidator.generate_and_validate(
            provider=provider,
            context_text=SAMPLE_CONTEXT,
            max_retries=1
        )
    assert any("timed out" in err for err in exc_info.value.errors)

def test_llm_malformed_json_failure():
    """Verify that malformed JSON is caught and rejected."""
    provider = MockLLMProvider(failure_mode="MALFORMED_JSON")
    with pytest.raises(QAValidationError) as exc_info:
        QAOutputValidator.generate_and_validate(
            provider=provider,
            context_text=SAMPLE_CONTEXT,
            max_retries=1
        )
    assert any("not valid JSON" in err for err in exc_info.value.errors)

def test_llm_invalid_count_rejection():
    """Verify that output with fewer than 3 test cases is rejected."""
    provider = MockLLMProvider(failure_mode="INVALID_COUNT")
    with pytest.raises(QAValidationError) as exc_info:
        QAOutputValidator.generate_and_validate(
            provider=provider,
            context_text=SAMPLE_CONTEXT,
            max_retries=1
        )
    assert any("test_cases" in err or "at least 3" in err.lower() for err in exc_info.value.errors)

def test_llm_missing_field_rejection():
    """Verify that output missing required fields is rejected."""
    provider = MockLLMProvider(failure_mode="MISSING_FIELD")
    with pytest.raises(QAValidationError) as exc_info:
        QAOutputValidator.generate_and_validate(
            provider=provider,
            context_text=SAMPLE_CONTEXT,
            max_retries=1
        )
    assert any("expected_result" in err or "Field required" in err for err in exc_info.value.errors)

def test_bounded_retry_recovery():
    """Verify that failure on attempt 1 with recovery on attempt 2 succeeds with REPAIRED_ON_RETRY."""
    provider = MockLLMProvider(failure_mode="MALFORMED_JSON", recover_on_retry=True)
    payload, status, info = QAOutputValidator.generate_and_validate(
        provider=provider,
        context_text=SAMPLE_CONTEXT,
        max_retries=2
    )
    assert status == "REPAIRED_ON_RETRY"
    assert info["attempts"] == 2
    assert 3 <= len(payload.test_cases) <= 5

def test_duplicate_selection_idempotency(populated_db):
    """Verify deterministic duplicate selection behavior without unexpected overwrite."""
    node = populated_db.query(SectionNode).filter(SectionNode.document_version == "v1").first()
    sel = Selection(name="Idempotency Test Selection", document_version="v1")
    populated_db.add(sel)
    populated_db.flush()
    populated_db.add(SelectionNode(selection_id=sel.id, node_id=node.id, order_index=0))
    populated_db.commit()

    # First generation
    art1 = generate_qa_test_ideas(sel.id, QAGenerateRequest(force_regenerate=False), populated_db)
    
    # Second generation without force_regenerate
    art2 = generate_qa_test_ideas(sel.id, QAGenerateRequest(force_regenerate=False), populated_db)
    
    # Must return identical existing artifact
    assert art1.id == art2.id
    assert art1.created_at == art2.created_at
