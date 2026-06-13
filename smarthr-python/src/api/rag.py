"""Unified RAG API."""

from typing import Any, Dict

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.services.mcp_client import mcp_client
from src.services.rag.evaluation import rag_evaluation_service
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
    ensure_recruitment_skills_registered()
    return await tool_registry.call(request.name, request.arguments)


@router.get("/mcp/tools")
async def list_mcp_tools():
    """List optional MCP gateway tools."""
    return await mcp_client.list_tools()
