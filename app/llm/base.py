"""
Abstract Base LLM Client Protocol.
"""

from abc import ABC, abstractmethod
from typing import Optional
from pydantic import BaseModel


class LLMResponse(BaseModel):
    sql: str
    explanation: str
    suggested_chart: Optional[str] = "table"


class BaseLLMClient(ABC):
    @abstractmethod
    def generate(self, system_prompt: str, user_question: str) -> LLMResponse:
        """Translates a natural language question into SQL using LLM."""
        pass
