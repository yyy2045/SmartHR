"""Embedding adapter with a deterministic mock fallback."""

import hashlib
import math
import re
from typing import List, Optional

from src.config import settings


class EmbeddingService:
    """Create embeddings through a configured provider or local mock vectors."""

    def __init__(self):
        self._client = None

    def _get_client(self):
        if self._client is not None:
            return self._client
        provider = getattr(settings, "embedding_provider", "mock")
        api_key = getattr(settings, "embedding_api_key", "") or settings.deepseek_api_key
        if provider == "mock" or not api_key:
            return None
        from langchain_openai import OpenAIEmbeddings

        self._client = OpenAIEmbeddings(
            api_key=api_key,
            base_url=getattr(settings, "embedding_base_url", "") or settings.deepseek_base_url,
            model=getattr(settings, "embedding_model", "text-embedding-3-small"),
        )
        return self._client

    async def embed_documents(self, texts: List[str]) -> List[List[float]]:
        client = self._get_client()
        if client is None:
            return [self._mock_embedding(text) for text in texts]
        return await client.aembed_documents(texts)

    async def embed_query(self, text: str) -> List[float]:
        client = self._get_client()
        if client is None:
            return self._mock_embedding(text)
        return await client.aembed_query(text)

    def _mock_embedding(self, text: str, dimensions: Optional[int] = None) -> List[float]:
        dim = dimensions or getattr(settings, "embedding_dimensions", 256)
        vector = [0.0] * dim
        tokens = self._tokenize(text)
        if not tokens:
            return vector
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            idx = int.from_bytes(digest[:4], "big") % dim
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[idx] += sign
        norm = math.sqrt(sum(v * v for v in vector))
        if norm == 0:
            return vector
        return [v / norm for v in vector]

    def _tokenize(self, text: str) -> List[str]:
        if not text:
            return []
        en_tokens = re.findall(r"[a-zA-Z0-9+#.\-]{2,}", text.lower())
        cn_tokens = re.findall(r"[\u4e00-\u9fff]{1,2}", text)
        return en_tokens + cn_tokens


embedding_service = EmbeddingService()
