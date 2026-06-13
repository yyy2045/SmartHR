"""Shared RAG request/response schemas."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class RagSource(BaseModel):
    sourceType: str
    sourceId: str
    chunkId: str
    title: str = ""
    content: str
    text: str = ""
    highlight: str = ""
    score: float = 0.0
    vectorScore: Optional[float] = None
    keywordScore: Optional[float] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RagEvidence(BaseModel):
    sourceType: str
    sourceId: str
    title: str = ""
    chunkId: str
    score: float = 0.0
    text: str
    highlight: str = ""
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
    evidence: List[RagEvidence] = Field(default_factory=list)
    retrievalScores: Dict[str, Any] = Field(default_factory=dict)
    rankScores: List[Dict[str, Any]] = Field(default_factory=list)
    retrievalMetrics: Dict[str, Any] = Field(default_factory=dict)
    traceId: Optional[str] = None


class RagEvaluationSample(BaseModel):
    question: str
    groundTruth: str = ""
    answer: Optional[str] = None
    expectedSourceIds: List[str] = Field(default_factory=list)
    companyId: Optional[str] = None
    sourceTypes: List[str] = Field(default_factory=list)


class RagEvaluationRequest(BaseModel):
    companyId: Optional[str] = None
    collection: str = "knowledge_base"
    topK: int = 5
    threshold: Optional[float] = None
    samples: List[RagEvaluationSample] = Field(default_factory=list)


class RagEvaluationSampleResult(BaseModel):
    question: str
    answer: str = ""
    groundTruth: str = ""
    sourceIds: List[str] = Field(default_factory=list)
    traceId: Optional[str] = None
    metrics: Dict[str, float] = Field(default_factory=dict)
    passed: bool = False
    reason: str = ""


class RagEvaluationResponse(BaseModel):
    runId: str
    status: str
    evaluator: str
    threshold: float
    sampleCount: int
    metrics: Dict[str, float] = Field(default_factory=dict)
    failedSamples: List[RagEvaluationSampleResult] = Field(default_factory=list)
    sampleResults: List[RagEvaluationSampleResult] = Field(default_factory=list)
    startedAt: str
    completedAt: str
    notes: str = ""
