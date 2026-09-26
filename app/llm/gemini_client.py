"""
Google Gemini API Client Implementation.
"""

import json
import logging
import re
from typing import Optional
import google.generativeai as genai
from app.core.config import settings
from app.llm.base import BaseLLMClient, LLMResponse

logger = logging.getLogger("GeminiClient")


class GeminiClient(BaseLLMClient):
    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        self.api_key = api_key or settings.GEMINI_API_KEY
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is not configured.")

        genai.configure(api_key=self.api_key)
        self.model_name = model_name or settings.GEMINI_MODEL
        self.model = genai.GenerativeModel(
            model_name=self.model_name,
            generation_config={
                "temperature": 0.0,
                "top_p": 0.95,
                "response_mime_type": "application/json"
            }
        )

    def generate(self, system_prompt: str, user_question: str) -> LLMResponse:
        full_prompt = f"{system_prompt}\n\nUSER QUESTION: {user_question}\nGenerate JSON response:"

        response = self.model.generate_content(full_prompt)
        raw_text = response.text.strip()

        # Parse JSON output
        try:
            # Strip markdown json code fences if any
            clean_json = re.sub(r"^```(?:json)?\s*", "", raw_text)
            clean_json = re.sub(r"\s*```$", "", clean_json)
            data = json.loads(clean_json)
            return LLMResponse(
                sql=data.get("sql", "").strip(),
                explanation=data.get("explanation", "").strip(),
                suggested_chart=data.get("suggested_chart", "table")
            )
        except Exception as e:
            logger.error(f"Failed to parse Gemini JSON output: {raw_text}. Error: {e}")
            raise ValueError(f"Gemini output parsing failed: {e}")
