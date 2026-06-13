"""Unified RAG API."""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.config import settings
from src.services.mcp_client import mcp_client
from src.services.rag.evaluation import rag_evaluation_service
from src.services.rag.evidence_service import rag_evidence_service
from src.services.rag.pipeline import rag_pipeline
from src.services.rag.schemas import (
    RagEvaluationRequest,
    RagEvaluationResponse,
    RagIndexRequest,
    RagIndexResponse,
    RagSearchRequest,
    RagSearchResponse,
)
from src.skills import ensure_recruitment_skills_registered
from src.tools.registry import tool_registry

router = APIRouter(prefix="/api/rag", tags=["RAG"])


class ToolCallRequest(BaseModel):
    name: str
    arguments: Dict[str, Any] = {}


class RagRebuildDocument(BaseModel):
    sourceType: str
    sourceId: str
    title: str = ""
    text: str = ""
    companyId: str = "default"
    metadata: Dict[str, Any] = {}


class RagRebuildRequest(BaseModel):
    documents: List[RagRebuildDocument]


class RagRebuildResponse(BaseModel):
    status: str
    indexed: int
    skipped: int
    failed: int
    details: List[Dict[str, Any]]


@router.post("/index", response_model=RagIndexResponse)
async def index_documents(request: RagIndexRequest):
    """Index normalized chunks into the unified RAG pipeline."""
    try:
        return await rag_pipeline.index(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"RAG 索引失败: {e}")


@router.post("/search", response_model=RagSearchResponse)
async def search_documents(request: RagSearchRequest):
    """Search indexed content with hybrid vector + keyword retrieval."""
    if not request.query or not request.query.strip():
        raise HTTPException(status_code=400, detail="query 不能为空")
    try:
        return await rag_pipeline.search(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"RAG 检索失败: {e}")


@router.post("/rebuild", response_model=RagRebuildResponse)
async def rebuild_index(request: RagRebuildRequest):
    """Batch rebuild business documents into the unified RAG index."""
    details: List[Dict[str, Any]] = []
    indexed = 0
    skipped = 0
    failed = 0

    for document in request.documents:
        if not document.text or not document.text.strip():
            skipped += 1
            details.append({
                "sourceType": document.sourceType,
                "sourceId": document.sourceId,
                "status": "skipped",
                "reason": "text 为空",
            })
            continue
        try:
            chunk_ids = await rag_evidence_service.index_text(
                source_type=document.sourceType,
                source_id=document.sourceId,
                title=document.title,
                text=document.text,
                company_id=document.companyId,
                metadata=document.metadata,
            )
            indexed += 1
            details.append({
                "sourceType": document.sourceType,
                "sourceId": document.sourceId,
                "status": "indexed",
                "chunks": len(chunk_ids),
                "chunkIds": chunk_ids,
            })
        except Exception as exc:
            failed += 1
            details.append({
                "sourceType": document.sourceType,
                "sourceId": document.sourceId,
                "status": "failed",
                "error": str(exc),
            })

    return RagRebuildResponse(
        status="completed" if failed == 0 else "partial_failed",
        indexed=indexed,
        skipped=skipped,
        failed=failed,
        details=details,
    )


@router.post("/evaluations/run", response_model=RagEvaluationResponse)
async def run_evaluation(request: RagEvaluationRequest):
    """Run sample-based RAG evaluation."""
    try:
        return await rag_evaluation_service.run(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"RAG 评测失败: {e}")


@router.get("/evaluations/latest", response_model=RagEvaluationResponse)
async def latest_evaluation():
    """Return latest Python-side RAG evaluation result."""
    return rag_evaluation_service.latest() or rag_evaluation_service.empty_result()


@router.get("/skills")
async def list_internal_skills():
    """List project-internal Agent skills/tools."""
    if not settings.expose_internal_rag_tools:
        raise HTTPException(status_code=404, detail="internal RAG tools are not exposed")
    ensure_recruitment_skills_registered()
    return {
        "skills": tool_registry.list_tools(),
        "mcp": {
            "enabled": mcp_client.is_enabled(),
        },
    }


@router.post("/skills/call")
async def call_internal_skill(request: ToolCallRequest):
    """Call a registered project-internal skill/tool."""
    if not settings.expose_internal_rag_tools:
        raise HTTPException(status_code=404, detail="internal RAG tools are not exposed")
    ensure_recruitment_skills_registered()
    return await tool_registry.call(request.name, request.arguments)


@router.get("/mcp/tools")
async def list_mcp_tools():
    """List optional MCP gateway tools."""
    if not settings.expose_internal_rag_tools:
        raise HTTPException(status_code=404, detail="MCP tools are not exposed")
    return await mcp_client.list_tools()
