"""Live LLM Provider using standard HTTP endpoints (OpenAI / Gemini compatible)."""
import json
from typing import Dict, Any, Optional
import httpx
from app.llm.base import BaseLLMProvider
from app.llm.mock_provider import MockLLMProvider
from app.core.config import settings
from app.core.logging import logger

class LiveHTTPLLMProvider(BaseLLMProvider):
    """
    Live LLM provider calling OpenAI or Gemini endpoints via httpx.
    Falls back to MockLLMProvider if API keys are unconfigured.
    """

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or settings.OPENAI_API_KEY or settings.GEMINI_API_KEY
        self.model = model or settings.LLM_MODEL
        self.fallback_mock = MockLLMProvider()

    def get_provider_info(self) -> Dict[str, Any]:
        if not self.api_key:
            return {
                "provider": "mock-fallback",
                "model": "grounded-rule-synthesizer-v1",
                "note": "Live API key was absent; automatically fell back to deterministic mock provider"
            }
        return {
            "provider": "openai-compatible",
            "model": self.model,
            "deterministic": False
        }

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        if not self.api_key:
            logger.info("No live LLM API key detected; utilizing deterministic mock provider.")
            return self.fallback_mock.generate(prompt, system_prompt)

        # Standard OpenAI-compatible chat completion payload
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": self.model,
            "messages": messages,
            "response_format": {"type": "json_object"},
            "temperature": 0.2
        }

        try:
            with httpx.Client(timeout=settings.LLM_TIMEOUT_SECONDS) as client:
                resp = client.post(url, headers=headers, json=payload)
                resp.raise_for_status()
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                return content
        except Exception as e:
            logger.warning(f"Live LLM call encountered an error: {e}. Falling back to mock provider.")
            return self.fallback_mock.generate(prompt, system_prompt)
