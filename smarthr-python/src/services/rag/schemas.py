"""Shared RAG request/response schemas."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class RagSource(BaseModel):
    sourceType: str
    sourceId: str
    chunkId: str
    title: str = ""
    content: str
    score: float = 0.0
    vectorScore: Optional[float] = None
    keywordScore: Optional[float] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RagIndexRequest(BaseModel):
    companyId: str = "default"
    sourceType: str = "knowledge"
    sourceId: str
    title: str = ""
    chunks: List[str]
    collection: str = "knowledge_base"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RagIndexResponse(BaseModel):
    status: str
    collection: str
    sourceId: str
    chunkIds: List[str]


class RagSearchRequest(BaseModel):
    query: str
    companyId: Optional[str] = None
    sourceTypes: List[str] = Field(default_factory=list)
    collection: str = "knowledge_base"
    topK: int = 5


class RagSearchResponse(BaseModel):
    query: str
    sources: List[RagSource]
    retrievalMetrics: Dict[str, Any] = Field(default_factory=dict)
    traceId: Optional[str] = None
