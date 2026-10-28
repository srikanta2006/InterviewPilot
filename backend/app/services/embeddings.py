import hashlib
import logging
import math
import os
from typing import Any, List, Optional

logger = logging.getLogger(__name__)

DEFAULT_EMBEDDING_MODEL = "all-MiniLM-L6-v2"
EMBEDDING_DIMENSION = 384


class EmbeddingService:
    """
    Embedding provider utilizing local sentence-transformers (all-MiniLM-L6-v2).
    Implements Chroma's EmbeddingFunction interface so it can be plugged directly
    into ChromaDB collections.
    """

    def __init__(self, model_name: str = DEFAULT_EMBEDDING_MODEL, use_mock_fallback: Optional[bool] = None):
        self.model_name = model_name
        if use_mock_fallback is not None:
            self.use_mock_fallback = use_mock_fallback
        else:
            from app.config import get_settings
            self.use_mock_fallback = (
                os.environ.get("USE_MOCK_EMBEDDINGS") == "1"
                or get_settings().use_mock_embeddings
            )
        self._model = None

    def _load_model(self):
        if self._model is not None or self.use_mock_fallback:
            return

        try:
            from sentence_transformers import SentenceTransformer
            # Suppress excessive huggingface hub verbosity
            os.environ["TOKENIZERS_PARALLELISM"] = "false"
            self._model = SentenceTransformer(self.model_name)
            logger.info(f"Loaded embedding model: {self.model_name}")
        except Exception as e:
            logger.warning(
                f"Failed to load sentence-transformers model '{self.model_name}': {e}. "
                "Falling back to deterministic hash-based mock embeddings."
            )
            self.use_mock_fallback = True

    def _generate_mock_embedding(self, text: str) -> List[float]:
        """
        Deterministic pseudo-semantic 384-dimensional unit vector derived from text.
        Ensures tests and offline development run consistently without network or heavy weights.
        """
        vec = [0.0] * EMBEDDING_DIMENSION
        words = text.lower().split()
        for idx, word in enumerate(words):
            h = int(hashlib.sha256(word.encode("utf-8")).hexdigest(), 16)
            for dim in range(EMBEDDING_DIMENSION):
                # Distribute deterministic pseudo-signals
                bit_val = ((h >> (dim % 64)) & 1) * 2 - 1
                decay = 1.0 / (1.0 + 0.05 * idx)
                vec[dim] += bit_val * decay

        # Normalize to unit length
        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0:
            return [v / norm for v in vec]
        return [1.0 / math.sqrt(EMBEDDING_DIMENSION)] * EMBEDDING_DIMENSION

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Compute normalized vector embeddings for a batch of texts."""
        if not texts:
            return []

        self._load_model()

        if self._model is not None and not self.use_mock_fallback:
            try:
                embeddings = self._model.encode(
                    texts,
                    convert_to_numpy=True,
                    normalize_embeddings=True,
                    show_progress_bar=False,
                )
                return embeddings.tolist()
            except Exception as e:
                logger.warning(f"Error encoding with sentence-transformers: {e}. Using deterministic fallback.")

        return [self._generate_mock_embedding(t) for t in texts]

    @staticmethod
    def is_legacy() -> bool:
        return False

    def embed_query(self, input: Any) -> List[List[float]]:
        """Compute vector embeddings for search queries."""
        return self.__call__(input)

    def __call__(self, input: Any) -> List[List[float]]:
        """ChromaDB embedding_function signature."""
        if isinstance(input, str):
            input = [input]
        return self.embed_documents(input)

    def name(self) -> str:
        """ChromaDB embedding function name signature."""
        return f"sentence-transformers/{self.model_name}"

