"""Recruitment Agent skills backed by the RAG pipeline and optional MCP tools."""

from typing import Any, Dict

from src.services.mcp_client import mcp_client
from src.services.rag.evaluation import rag_evaluation_service
from src.services.rag.pipeline import rag_pipeline
from src.services.rag.schemas import RagEvaluationRequest, RagSearchRequest
from src.tools.registry import ToolDefinition, tool_registry


_REGISTERED = False


async def _knowledge_qa(arguments: Dict[str, Any]) -> Dict[str, Any]:
    query = str(arguments.get("query") or "").strip()
    if not query:
        return {"status": "error", "message": "query 不能为空"}
    request = RagSearchRequest(
        query=query,
        companyId=arguments.get("companyId"),
        collection=arguments.get("collection") or "knowledge_base",
        sourceTypes=arguments.get("sourceTypes") or [],
        topK=int(arguments.get("topK") or 5),
    )
    response = await rag_pipeline.search(request)
    return {"status": "ok", "data": response.model_dump()}


async def _rag_evaluation(arguments: Dict[str, Any]) -> Dict[str, Any]:
    request = RagEvaluationRequest(
        companyId=arguments.get("companyId"),
        collection=arguments.get("collection") or "knowledge_base",
        topK=int(arguments.get("topK") or 5),
        threshold=arguments.get("threshold"),
        samples=arguments.get("samples") or [],
    )
    response = await rag_evaluation_service.run(request)
    return {"status": "ok", "data": response.model_dump()}


async def _mcp_tools(arguments: Dict[str, Any]) -> Dict[str, Any]:
    return await mcp_client.list_tools()


def ensure_recruitment_skills_registered() -> None:
    global _REGISTERED
    if _REGISTERED:
        return

    tool_registry.register(ToolDefinition(
        name="recruitment.knowledge_qa",
        description="基于企业知识库、岗位和简历上下文执行招聘问答检索。",
        inputSchema={
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "companyId": {"type": "string"},
                "sourceTypes": {"type": "array", "items": {"type": "string"}},
                "topK": {"type": "integer", "default": 5},
            },
            "required": ["query"],
        },
        handler=_knowledge_qa,
    ))
    tool_registry.register(ToolDefinition(
        name="recruitment.rag_evaluation",
        description="执行 RAG 评测，优先使用 Ragas，失败时降级为本地启发式评测。",
        inputSchema={
            "type": "object",
            "properties": {
                "companyId": {"type": "string"},
                "collection": {"type": "string", "default": "knowledge_base"},
                "topK": {"type": "integer", "default": 5},
                "threshold": {"type": "number", "default": 0.7},
                "samples": {"type": "array"},
            },
        },
        handler=_rag_evaluation,
    ))
    tool_registry.register(ToolDefinition(
        name="mcp.tools.list",
        description="列出可选 MCP 网关暴露的外部工具；未启用时返回空列表。",
        inputSchema={"type": "object", "properties": {}},
        handler=_mcp_tools,
    ))

    _REGISTERED = True
