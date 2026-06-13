"""Unified RAG API."""

from fastapi import APIRouter, HTTPException

from src.services.rag.pipeline import rag_pipeline
from src.services.rag.schemas import RagIndexRequest, RagIndexResponse, RagSearchRequest, RagSearchResponse

router = APIRouter(prefix="/api/rag", tags=["RAG"])


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
