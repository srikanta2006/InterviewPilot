import json
import logging
from typing import Any, Dict, Optional, Type, TypeVar
from pydantic import BaseModel, ValidationError
from app.config import get_settings

logger = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)

DEFAULT_MODEL = "llama-3.3-70b-versatile"
FAST_MODEL = "llama-3.1-8b-instant"


class GroqClientService:
    """Wrapper around Groq API with validation and fallback handling."""

    def __init__(self, api_key: Optional[str] = None):
        settings = get_settings()
        self.api_key = api_key or settings.groq_api_key
        self._client = None

    @property
    def is_configured(self) -> bool:
        """Check if a real Groq API key is present."""
        if not self.api_key:
            return False
        # Ignore placeholder values
        if "placeholder" in self.api_key.lower() or "your_" in self.api_key.lower():
            return False
        return len(self.api_key.strip()) > 10

    def get_client(self):
        """Lazily initialize the Groq client."""
        if self._client is None and self.is_configured:
            try:
                from groq import Groq
                self._client = Groq(api_key=self.api_key)
            except ImportError:
                logger.warning("Groq SDK is not installed.")
                return None
        return self._client

    def extract_structured_json(
        self,
        system_prompt: str,
        user_prompt: str,
        response_model: Type[T],
        model: str = DEFAULT_MODEL,
        max_retries: int = 2,
    ) -> Optional[T]:
        """Request structured JSON from Groq and validate with a Pydantic model."""
        client = self.get_client()
        if not client:
            return None

        for attempt in range(max_retries + 1):
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.1,
                )
                raw_json = response.choices[0].message.content
                data = json.loads(raw_json)
                return response_model.model_validate(data)
            except ValidationError as ve:
                logger.warning(f"Schema validation failed on attempt {attempt + 1}: {ve}")
                if attempt == max_retries:
                    return None
            except Exception as e:
                logger.warning(f"Groq API call error on attempt {attempt + 1}: {e}")
                if attempt == max_retries:
                    return None
        return None
