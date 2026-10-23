"""LLM QA Output Validator and bounded retry engine."""
import json
from typing import Dict, Any, List, Optional, Tuple
from pydantic import ValidationError

from app.schemas.qa import QATestIdea, QAGenerationPayload
from app.llm.base import BaseLLMProvider
from app.core.config import settings
from app.core.logging import logger

class QAValidationError(Exception):
    """Raised when LLM output repeatedly fails validation after bounded retries."""
    def __init__(self, message: str, errors: List[str], raw_output: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.errors = errors
        self.raw_output = raw_output

class QAOutputValidator:
    """Validates LLM output against strict schemas and executes bounded corrective retries."""

    @staticmethod
    def build_system_prompt() -> str:
        return (
            "You are a principal QA test engineer reviewing technical medical device documentation.\n"
            "Your task is to generate actionable, grounded test ideas based strictly on the provided source text.\n"
            "You must return ONLY a valid JSON object matching this schema:\n"
            "{\n"
            '  "test_cases": [\n'
            "    {\n"
            '      "test_id": "string, e.g. TC-01",\n'
            '      "test_objective": "string",\n'
            '      "preconditions": ["string"],\n'
            '      "steps": ["string"],\n'
            '      "expected_result": "string",\n'
            '      "source_references": ["string"]\n'
            "    }\n"
            "  ]\n"
            "}\n"
            "Constraints:\n"
            "1. You MUST generate between 3 and 5 test cases (inclusive).\n"
            "2. All steps and expectations must be verifiable and grounded in the source text.\n"
            "3. Do not include markdown code fences or explanatory text outside the JSON."
        )

    @classmethod
    def generate_and_validate(
        cls,
        provider: BaseLLMProvider,
        context_text: str,
        custom_instructions: Optional[str] = None,
        max_retries: int = 2
    ) -> Tuple[QAGenerationPayload, str, Dict[str, Any]]:
        """
        Execute generation with bounded retries.
        Returns (payload, validation_status, provider_info).
        Raises QAValidationError if validation fails after all retries.
        """
        system_prompt = cls.build_system_prompt()
        base_prompt = f"Source Documentation Content:\n\n{context_text}\n\n"
        if custom_instructions:
            base_prompt += f"Specific testing focus: {custom_instructions}\n\n"
        base_prompt += "Generate 3 to 5 grounded QA test cases in valid JSON format now."

        current_prompt = base_prompt
        last_error_messages: List[str] = []
        last_raw_response: Optional[str] = None

        for attempt in range(max_retries + 1):
            try:
                logger.info(f"LLM Generation Attempt {attempt + 1}/{max_retries + 1}")
                raw_response = provider.generate(current_prompt, system_prompt=system_prompt)
                last_raw_response = raw_response

                # Strip possible markdown fences e.g. ```json ... ```
                clean_json_str = raw_response.strip()
                if clean_json_str.startswith("```"):
                    lines = clean_json_str.splitlines()
                    if lines[0].startswith("```"):
                        lines = lines[1:]
                    if lines and lines[-1].startswith("```"):
                        lines = lines[:-1]
                    clean_json_str = "\n".join(lines).strip()

                # Parse JSON
                try:
                    data = json.loads(clean_json_str)
                except json.JSONDecodeError as jde:
                    raise ValueError(f"Output is not valid JSON: {jde.msg} at line {jde.lineno} col {jde.colno}")

                # Validate against Pydantic schema (validates types, required fields, and 3-5 count)
                payload = QAGenerationPayload.model_validate(data)
                
                # Check additional field constraints
                for tc in payload.test_cases:
                    if not tc.test_id or not tc.test_objective or not tc.expected_result:
                        raise ValueError(f"Test case {tc.test_id} has empty required fields")
                    if not tc.preconditions or not tc.steps or not tc.source_references:
                        raise ValueError(f"Test case {tc.test_id} must have non-empty preconditions, steps, and source_references")

                validation_status = "VALID" if attempt == 0 else "REPAIRED_ON_RETRY"
                provider_info = provider.get_provider_info()
                provider_info["attempts"] = attempt + 1
                return payload, validation_status, provider_info

            except Exception as e:
                err_msg = str(e)
                logger.warning(f"Generation attempt {attempt + 1} failed validation: {err_msg}")
                last_error_messages.append(f"Attempt {attempt + 1}: {err_msg}")

                if attempt < max_retries:
                    # Construct corrective prompt
                    current_prompt = (
                        f"{base_prompt}\n\n"
                        f"CORRECTION NOTICE: Your previous output failed schema validation with error:\n"
                        f"{err_msg}\n\n"
                        f"Please correct the error and return exactly 3 to 5 valid test cases matching the schema."
                    )

        # All retries failed
        raise QAValidationError(
            message=f"Failed to produce valid QA test cases after {max_retries + 1} attempts.",
            errors=last_error_messages,
            raw_output=last_raw_response
        )
