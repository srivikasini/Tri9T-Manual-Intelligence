"""Base LLM Provider abstract interface."""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class BaseLLMProvider(ABC):
    """Abstract interface for LLM test generation providers."""

    @abstractmethod
    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """
        Generate a text response from the model.
        Must return raw text (expected to be JSON format).
        """
        pass

    @abstractmethod
    def get_provider_info(self) -> Dict[str, Any]:
        """Return provider and model metadata for provenance tracking."""
        pass
