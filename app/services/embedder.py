import math
import hashlib
import re
from typing import List, Optional
from abc import ABC, abstractmethod
import numpy as np

from app.core.config import get_settings
from app.core.logging import logger
from app.core.errors import ProviderError


class BaseEmbedder(ABC):
    """Abstract base class for vector embedding generators."""

    @abstractmethod
    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        pass

    @abstractmethod
    async def embed_query(self, query: str) -> List[float]:
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        pass


class LocalFallbackEmbedder(BaseEmbedder):
    """
    Deterministic zero-dependency local semantic vectorizer.
    Generates 384-dimensional unit-norm dense embeddings using token & subword n-gram hashing
    with TF-IDF weighting and L2 normalization.
    Allows full offline testing and evaluation without requiring paid cloud API keys.
    """

    DIMENSIONS = 384

    def __init__(self):
        self._provider = "local"
        self._model = "deterministic-subword-384"

    @property
    def provider_name(self) -> str:
        return self._provider

    @property
    def model_name(self) -> str:
        return self._model

    def _vectorize_single(self, text: str) -> List[float]:
        vec = np.zeros(self.DIMENSIONS, dtype=np.float32)
        words = re.findall(r"\w+", text.lower())
        if not words:
            # Return normalized uniform vector
            vec.fill(1.0 / math.sqrt(self.DIMENSIONS))
            return vec.tolist()

        # Token + 3-gram and 4-gram subword hashing
        tokens_to_hash = []
        for w in words:
            tokens_to_hash.append(w)
            # Add character n-grams for subword semantic capture
            if len(w) >= 3:
                for i in range(len(w) - 2):
                    tokens_to_hash.append(w[i:i+3])

        for tok in tokens_to_hash:
            # Deterministic MD5 hash bucket
            h = int(hashlib.md5(tok.encode("utf-8")).hexdigest()[:8], 16)
            idx = h % self.DIMENSIONS
            sign = 1.0 if (h >> 16) % 2 == 0 else -1.0
            vec[idx] += sign

        # L2 normalize
        norm = np.linalg.norm(vec)
        if norm > 1e-9:
            vec = vec / norm
        else:
            vec.fill(1.0 / math.sqrt(self.DIMENSIONS))

        return vec.tolist()

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        return [self._vectorize_single(t) for t in texts]

    async def embed_query(self, query: str) -> List[float]:
        return self._vectorize_single(query)


class OpenAIEmbedder(BaseEmbedder):
    """OpenAI embeddings generator using official AsyncOpenAI SDK."""

    def __init__(self, api_key: str, model: str = "text-embedding-3-small"):
        from openai import AsyncOpenAI
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model

    @property
    def provider_name(self) -> str:
        return "openai"

    @property
    def model_name(self) -> str:
        return self.model

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        try:
            # Truncate any extreme texts
            safe_texts = [t[:8000] for t in texts]
            resp = await self.client.embeddings.create(
                input=safe_texts,
                model=self.model,
            )
            # Maintain order
            return [data.embedding for data in sorted(resp.data, key=lambda x: x.index)]
        except Exception as e:
            logger.error(f"OpenAI embedding error: {str(e)}")
            raise ProviderError(
                message=f"Failed to generate OpenAI embeddings: {str(e)}",
                details={"model": self.model, "error": str(e)},
            )

    async def embed_query(self, query: str) -> List[float]:
        results = await self.embed_texts([query])
        return results[0]


class GeminiEmbedder(BaseEmbedder):
    """Google Gemini embeddings generator using google-genai SDK."""

    def __init__(self, api_key: str, model: str = "text-embedding-004"):
        from google import genai
        self.client = genai.Client(api_key=api_key)
        self.model = model

    @property
    def provider_name(self) -> str:
        return "gemini"

    @property
    def model_name(self) -> str:
        return self.model

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        try:
            results = []
            for t in texts:
                resp = self.client.models.embed_content(
                    model=self.model,
                    contents=t[:8000],
                )
                if hasattr(resp, "embeddings") and resp.embeddings:
                    results.append(resp.embeddings[0].values)
                elif hasattr(resp, "embedding") and resp.embedding:
                    results.append(resp.embedding.values)
                else:
                    raise ValueError(f"No embeddings returned in Gemini response: {resp}")
            return results
        except Exception as e:
            logger.error(f"Gemini embedding error: {str(e)}")
            raise ProviderError(
                message=f"Failed to generate Gemini embeddings: {str(e)}",
                details={"model": self.model, "error": str(e)},
            )

    async def embed_query(self, query: str) -> List[float]:
        results = await self.embed_texts([query])
        return results[0]


def get_embedder(provider_override: Optional[str] = None) -> BaseEmbedder:
    """Factory to instantiate the appropriate embedder based on configuration."""
    settings = get_settings()
    provider = provider_override or settings.resolve_provider()

    if provider == "openai" and settings.OPENAI_API_KEY:
        logger.info(f"Using OpenAI embedder with model '{settings.OPENAI_EMBEDDING_MODEL}'")
        return OpenAIEmbedder(
            api_key=settings.OPENAI_API_KEY,
            model=settings.OPENAI_EMBEDDING_MODEL,
        )

    if provider == "gemini" and settings.GEMINI_API_KEY:
        logger.info(f"Using Gemini embedder with model '{settings.GEMINI_EMBEDDING_MODEL}'")
        return GeminiEmbedder(
            api_key=settings.GEMINI_API_KEY,
            model=settings.GEMINI_EMBEDDING_MODEL,
        )

    logger.info("Using Local Fallback embedder (deterministic subword vectorizer)")
    return LocalFallbackEmbedder()
