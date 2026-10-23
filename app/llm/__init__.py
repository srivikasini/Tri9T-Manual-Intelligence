"""LLM package exports."""
from app.llm.base import BaseLLMProvider
from app.llm.mock_provider import MockLLMProvider
from app.llm.live_provider import LiveHTTPLLMProvider
from app.llm.validator import QAOutputValidator, QAValidationError

def get_llm_provider(failure_mode=None, recover_on_retry=False) -> BaseLLMProvider:
    """Factory function returning the configured LLM provider."""
    from app.core.config import settings
    if settings.LLM_PROVIDER == "live" and (settings.OPENAI_API_KEY or settings.GEMINI_API_KEY):
        return LiveHTTPLLMProvider()
    return MockLLMProvider(failure_mode=failure_mode, recover_on_retry=recover_on_retry)

__all__ = [
    "BaseLLMProvider",
    "MockLLMProvider",
    "LiveHTTPLLMProvider",
    "QAOutputValidator",
    "QAValidationError",
    "get_llm_provider"
]
