"""Embedding adapter for local BGE, OpenAI-compatible providers, and dev mock."""

import hashlib
import math
import os
import re
from typing import Any, Dict, List, Optional

from src.config import settings


class EmbeddingService:
    """Create embeddings through the configured provider.

    Production demo deployments use a host-mounted local bge-base-zh-v1.5 model.
    The deterministic mock is kept only for local development and tests.
    """

    def __init__(self):
        self._client = None
        self._client_provider = None
        self._load_error: Optional[str] = None

    def _get_client(self):
        provider = self._provider()
        if self._client is not None and self._client_provider == provider:
            return self._client

        if provider == "mock":
            self._ensure_mock_allowed()
            return None

        if provider in {"local_bge", "bge", "sentence_transformers", "sentence-transformers"}:
            model_path = getattr(settings, "local_bge_model_path", "")
            if not model_path or not os.path.isdir(model_path):
                raise RuntimeError(f"本地 BGE 模型目录不存在: {model_path}")
            try:
                from sentence_transformers import SentenceTransformer

                self._client = SentenceTransformer(model_path, device="cpu")
                self._client_provider = provider
                self._load_error = None
                return self._client
            except Exception as exc:
                self._load_error = str(exc)
                raise RuntimeError(f"本地 BGE 模型加载失败: {exc}") from exc

        api_key = getattr(settings, "embedding_api_key", "") or settings.deepseek_api_key
        if not api_key:
            raise RuntimeError("Embedding API Key 未配置，非开发模式不会降级到 mock embedding")
        from langchain_openai import OpenAIEmbeddings

        self._client = OpenAIEmbeddings(
            api_key=api_key,
            base_url=getattr(settings, "embedding_base_url", "") or settings.deepseek_base_url,
            model=getattr(settings, "embedding_model", "text-embedding-3-small"),
        )
        self._client_provider = provider
        self._load_error = None
        return self._client

    async def embed_documents(self, texts: List[str]) -> List[List[float]]:
        client = self._get_client()
        if client is None:
            return [self._mock_embedding(text) for text in texts]
        if self._is_local_provider():
            vectors = client.encode(texts, normalize_embeddings=True)
            return [self._vector_to_list(vector) for vector in vectors]
        return await client.aembed_documents(texts)

    async def embed_query(self, text: str) -> List[float]:
        client = self._get_client()
        if client is None:
            return self._mock_embedding(text)
        if self._is_local_provider():
            vector = client.encode(text, normalize_embeddings=True)
            return self._vector_to_list(vector)
        return await client.aembed_query(text)

    async def healthcheck(self) -> Dict[str, Any]:
        status = self.status()
        try:
            vector = await self.embed_query("SmartHR embedding health check")
            status.update({
                "status": "UP",
                "loaded": self._client is not None,
                "testEmbedding": True,
                "actualDimensions": len(vector),
            })
        except Exception as exc:
            status.update({
                "status": "DOWN",
                "testEmbedding": False,
                "error": str(exc),
            })
        return status

    def status(self) -> Dict[str, Any]:
        model_path = getattr(settings, "local_bge_model_path", "")
        return {
            "provider": self._provider(),
            "model": getattr(settings, "embedding_model", ""),
            "expectedDimensions": getattr(settings, "embedding_dimensions", None),
            "modelPath": model_path,
            "modelPathExists": bool(model_path and os.path.isdir(model_path)),
            "loaded": self._client is not None,
            "mockAllowed": bool(getattr(settings, "allow_mock_embedding", False)),
            "lastError": self._load_error,
        }

    def _provider(self) -> str:
        return str(getattr(settings, "embedding_provider", "mock") or "mock").lower()

    def _is_local_provider(self) -> bool:
        return self._provider() in {"local_bge", "bge", "sentence_transformers", "sentence-transformers"}

    def _ensure_mock_allowed(self):
        if not getattr(settings, "allow_mock_embedding", False):
            raise RuntimeError("mock embedding 仅允许开发模式，请配置本地 BGE 模型")

    def _vector_to_list(self, vector) -> List[float]:
        if hasattr(vector, "tolist"):
            return [float(value) for value in vector.tolist()]
        return [float(value) for value in vector]

    def _mock_embedding(self, text: str, dimensions: Optional[int] = None) -> List[float]:
        self._ensure_mock_allowed()
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
