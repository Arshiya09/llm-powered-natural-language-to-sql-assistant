"""
LLM Client Factory.
"""

import logging
from app.core.config import settings
from app.llm.base import BaseLLMClient
from app.llm.gemini_client import GeminiClient
from app.llm.mock_client import MockLLMClient
from app.llm.openai_client import OpenAIClient

logger = logging.getLogger("LLMFactory")


def get_llm_client() -> BaseLLMClient:
    """Returns the configured LLM client with graceful fallback to mock mode."""
    provider = settings.LLM_PROVIDER.lower()

    if provider == "mock":
        return MockLLMClient()

    if provider == "gemini":
        if settings.GEMINI_API_KEY:
            try:
                return GeminiClient()
            except Exception as e:
                logger.warning(f"Failed to initialize GeminiClient: {e}")
        if settings.ENABLE_MOCK_FALLBACK:
            logger.info("Falling back to MockLLMClient (no valid GEMINI_API_KEY).")
            return MockLLMClient()
        raise ValueError("GEMINI_API_KEY is missing and mock fallback is disabled.")

    if provider == "openai":
        if settings.OPENAI_API_KEY:
            try:
                return OpenAIClient()
            except Exception as e:
                logger.warning(f"Failed to initialize OpenAIClient: {e}")
        if settings.ENABLE_MOCK_FALLBACK:
            logger.info("Falling back to MockLLMClient (no valid OPENAI_API_KEY).")
            return MockLLMClient()
        raise ValueError("OPENAI_API_KEY is missing and mock fallback is disabled.")

    return MockLLMClient()
