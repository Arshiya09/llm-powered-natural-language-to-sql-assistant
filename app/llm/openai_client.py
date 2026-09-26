"""
OpenAI API Client Implementation.
"""

import json
import logging
from typing import Optional
from openai import OpenAI
from app.core.config import settings
from app.llm.base import BaseLLMClient, LLMResponse

logger = logging.getLogger("OpenAIClient")


class OpenAIClient(BaseLLMClient):
    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        self.api_key = api_key or settings.OPENAI_API_KEY
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is not configured.")

        self.client = OpenAI(api_key=self.api_key)
        self.model_name = model_name or settings.OPENAI_MODEL

    def generate(self, system_prompt: str, user_question: str) -> LLMResponse:
        completion = self.client.chat.completions.create(
            model=self.model_name,
            temperature=0.0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_question}
            ]
        )

        content = completion.choices[0].message.content or "{}"
        data = json.loads(content)
        return LLMResponse(
            sql=data.get("sql", "").strip(),
            explanation=data.get("explanation", "").strip(),
            suggested_chart=data.get("suggested_chart", "table")
        )
