import json
import logging
from typing import Any, Dict, List, Optional, Type, TypeVar
from pydantic import BaseModel, ValidationError
from app.config import get_settings

logger = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)

DEFAULT_MODEL = "openai/gpt-oss-120b"
FAST_MODEL = "qwen/qwen3.8-27b"

# Priority order for chat models on Groq
PREFERRED_CHAT_MODELS = [
    "openai/gpt-oss-120b",
    "qwen/qwen3.8-27b",
    "openai/gpt-oss-20b",
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "llama3-70b-8192",
    "llama3-8b-8192",
    "mixtral-8x7b-32768",
]


class GroqClientService:
    """Wrapper around Groq API with dynamic model discovery, validation, and zero-latency fallback."""

    def __init__(self, api_key: Optional[str] = None):
        settings = get_settings()
        # Explicit None check: if caller explicitly passes api_key="" (e.g. unit tests for fallback), respect it
        self.api_key = api_key if api_key is not None else settings.groq_api_key
        self._client = None
        self._active_model: Optional[str] = None
        self._remote_model_ids: Optional[set] = None

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

    def _get_remote_model_ids(self) -> set:
        """Fetch remote model IDs once from Groq account catalog."""
        if self._remote_model_ids is not None:
            return self._remote_model_ids
        client = self.get_client()
        if not client:
            self._remote_model_ids = set()
            return self._remote_model_ids
        try:
            self._remote_model_ids = {m.id for m in client.models.list().data}
        except Exception as e:
            logger.warning(f"Could not retrieve Groq model catalog: {e}")
            self._remote_model_ids = set()
        return self._remote_model_ids

    def resolve_model(self, requested_model: Optional[str] = None) -> str:
        """
        Dynamically determine the best accessible chat model for this Groq account.
        Only selects models that actually exist in the account's accessible catalog.
        """
        if self._active_model:
            return self._active_model

        remote_models = self._get_remote_model_ids()

        # If user explicitly requested a model that exists remotely, use it
        if requested_model and requested_model in remote_models:
            self._active_model = requested_model
            return self._active_model

        # Otherwise pick the highest-priority supported model that exists remotely
        for candidate in PREFERRED_CHAT_MODELS:
            if candidate in remote_models:
                self._active_model = candidate
                logger.info(f"GroqClient resolved active model: {candidate}")
                return self._active_model

        # If remote catalog lookup was unavailable, default to first preference
        self._active_model = DEFAULT_MODEL
        return self._active_model

    def extract_structured_json(
        self,
        system_prompt: str,
        user_prompt: str,
        response_model: Type[T],
        model: Optional[str] = None,
        max_retries: int = 1,
    ) -> Optional[T]:
        """
        Request structured JSON from Groq and validate with a Pydantic model.
        Uses verified accessible models and fails fast to local heuristics on error.
        """
        if not self.is_configured:
            return None

        client = self.get_client()
        if not client:
            return None

        current_model = self.resolve_model(model)

        for attempt in range(max_retries + 1):
            try:
                response = client.chat.completions.create(
                    model=current_model,
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
                    break

            except Exception as e:
                err_msg = str(e)
                logger.warning(f"Groq call error with {current_model} on attempt {attempt + 1}: {err_msg}")

                # If 404 or model not found, fail fast immediately - do NOT loop retries
                if "404" in err_msg or "model_not_found" in err_msg or "does not exist" in err_msg:
                    logger.info("Model not found on Groq account; immediately falling back to local engine.")
                    break

                if attempt == max_retries:
                    break

        return None
