"""
知识库 API - 企业知识库管理
"""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import io

from src.services.document_processor import document_processor
from src.services.knowledge_retriever import knowledge_retriever
from src.services.redis_service import redis_service

router = APIRouter(tags=["知识库"])


class DocumentUploadResponse(BaseModel):
    """文档上传响应"""
    document_id: str
    filename: str
    status: str
    chunks: int
    title: str
    chunk_ids: List[str] = []


class KnowledgeSearchRequest(BaseModel):
    """知识库搜索请求"""
    query: str
    company_id: Optional[str] = None
    doc_type: Optional[str] = None
    top_k: int = 5


class KnowledgeSearchResult(BaseModel):
    """知识库搜索结果"""
    content: str
    source: str
    similarity: float


class DocumentResponse(BaseModel):
    """文档响应"""
    document_id: str
    title: str
    doc_type: str
    company_id: Optional[str]
    uploaded_at: str
    status: str
    chunks: int
    content: Optional[str] = None


@router.post("/documents/{document_id}", response_model=DocumentUploadResponse)
async def upload_document(
    document_id: str,
    file: UploadFile = File(...),
    company_id: str = Form(...),
    doc_type: str = Form(...),  # POLICY, MANUAL, HISTORY, OTHER
    title: str = Form(...)  # 自定义文档标题
):
    """
    上传文档（PDF、Word、TXT）并向量化到知识库
    UUID 由 Java 生成并通过路径传入
    """
    # 读取文件内容
    content = await file.read()
    filename = file.filename or "unknown"

    # 使用从 Java 传入的 UUID
    # 在 Redis 中存储元数据用于追踪
    metadata = {
        "doc_id": document_id,
        "filename": filename,
        "title": title,
        "company_id": company_id,
        "doc_type": doc_type,
        "status": "PROCESSING"
    }

    # 异步处理文档
    text = None
    chunk_ids = []
    try:
        # 处理文件内容并向量化
        text = document_processor.extract_text_from_bytes(content, filename)
        chunks = document_processor.chunk_text(text)
        chunk_ids = await document_processor.vectorize_chunks(chunks, {
            **metadata,
            "collection": "knowledge_base"
        })

        metadata["status"] = "INDEXED"
        metadata["chunks"] = len(chunk_ids)
        metadata["chunk_ids"] = chunk_ids

    except Exception as e:
        metadata["status"] = "FAILED"
        metadata["error"] = str(e)
        metadata["chunks"] = 0
        metadata["chunk_ids"] = []
        print(f"[knowledge] process error: {e}")

    # 将完整文本存入 Redis 供预览使用
    doc_id = metadata.get("doc_id")
    doc_company_id = metadata.get("company_id")  # 使用不同变量名避免遮盖
    if doc_id and doc_company_id and text:
        preview_key = f"doc_preview:{doc_company_id}:{doc_id}"
        try:
            redis_service.set(preview_key, {"content": text[:10000], "filename": filename}, expire=None)
        except Exception as e:
            print(f"[knowledge] preview save error: {e}")

    # 使用复合键保存文档元数据: doc:{company_id}:{document_id}
    doc_key = f"doc:{doc_company_id}:{document_id}"
    redis_service.set(doc_key, metadata, expire=None)

    return DocumentUploadResponse(
        document_id=document_id,
        filename=filename,
        status=metadata["status"],
        chunks=metadata.get("chunks", 0),
        title=title or filename.rsplit('.', 1)[0] if filename else "Untitled",
        chunk_ids=metadata.get("chunk_ids", [])
    )


@router.get("/documents", response_model=Dict[str, Any])
async def list_documents(
    company_id: Optional[str] = None,
    doc_type: Optional[str] = None,
    page: int = 1,
    size: int = 20
):
    """
    列出公司的所有文档，支持可选过滤
    """
    # 使用更精确的 key 模式过滤
    pattern = f"doc:{company_id}:*" if company_id else "doc:*"
    keys = redis_service.scan_keys(pattern)

    documents = []
    for key in keys:
        doc = redis_service.get(key)
        if not doc or not isinstance(doc, dict):
            continue

        # 按 company_id 和 doc_type 过滤
        if company_id and doc.get("company_id") != company_id:
            continue
        if doc_type and doc.get("doc_type") != doc_type:
            continue

        documents.append({
            "document_id": doc.get("doc_id"),
            "title": doc.get("title") or doc.get("filename", "").rsplit('.', 1)[0] if doc.get("filename") else "Untitled",
            "filename": doc.get("filename"),
            "doc_type": doc.get("doc_type"),
            "company_id": doc.get("company_id"),
            "status": doc.get("status"),
            "chunks": doc.get("chunks", 0),
            "uploaded_at": doc.get("uploaded_at", "")
        })

    # 分页
    start = (page - 1) * size
    end = start + size
    paginated = documents[start:end]

    return {
        "documents": paginated,
        "total": len(documents),
        "page": page,
        "size": size
    }


@router.get("/documents/{document_id}", response_model=Dict[str, Any])
async def get_document(document_id: str, company_id: Optional[str] = None):
    """获取文档详情"""
    # 如果提供了 company_id 则使用复合键，否则尝试旧版键
    if company_id:
        doc_key = f"doc:{company_id}:{document_id}"
    else:
        doc_key = f"doc:{document_id}"
    doc = redis_service.get(doc_key)

    if not doc:
        raise HTTPException(status_code=404, detail="文档未找到")

    # 尝试获取预览内容
    doc_company_id = doc.get('company_id', '')
    preview_key = f"doc_preview:{company_id or doc_company_id}:{document_id}"
    preview_data = redis_service.get(preview_key)

    return {
        "document_id": doc.get("doc_id"),
        "title": doc.get("title") or doc.get("filename", "").rsplit('.', 1)[0] if doc.get("filename") else "Untitled",
        "filename": doc.get("filename"),
        "doc_type": doc.get("doc_type"),
        "company_id": doc.get("company_id"),
        "status": doc.get("status"),
        "chunks": doc.get("chunks", 0),
        "chunk_ids": doc.get("chunk_ids", []),
        "content": preview_data.get("content") if preview_data and isinstance(preview_data, dict) else None
    }


@router.delete("/documents/{document_id}")
async def delete_document(document_id: str, company_id: Optional[str] = None):
    """删除文档及其在知识库中的向量"""
    # 如果提供了 company_id 则使用复合键，否则尝试旧版键
    if company_id:
        doc_key = f"doc:{company_id}:{document_id}"
    else:
        doc_key = f"doc:{document_id}"
    doc = redis_service.get(doc_key)

    if not doc:
        raise HTTPException(status_code=404, detail="文档未找到")

    # 先尝试从向量存储删除，成功后再删 Redis（保持一致性）
    chunk_ids = doc.get("chunk_ids", [])
    if chunk_ids:
        try:
            from src.services.vector_store import vector_store_service
            vector_store_service.delete("knowledge_base", chunk_ids)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"删除向量失败: {e}")

    # 只有向量删除成功后才删 Redis
    redis_service.delete(doc_key)

    return {
        "status": "deleted",
        "document_id": document_id
    }


@router.post("/search", response_model=Dict[str, Any])
async def search_knowledge(request: KnowledgeSearchRequest):
    """
    在知识库中进行语义搜索
    返回相关文档片段及相似度分数
    """
    # company_id 用于数据隔离，未提供时使用默认值
    company_id = request.company_id or "default"

    try:
        # 按公司搜索
        results = await knowledge_retriever.search_by_company(
            company_id=company_id,
            query=request.query,
            top_k=request.top_k
        )

        # 格式化结果
        formatted_results = []
        for r in results:
            metadata = r.get("metadata", {})
            distance = r.get("distance", 0)
            # 将距离转换为相似度分数（距离越小相似度越高）
            similarity = max(0, 1 - distance) if distance else 0.85

            formatted_results.append({
                "content": r.get("document", ""),
                "source": metadata.get("filename", "Unknown"),
                "doc_type": metadata.get("doc_type", "UNKNOWN"),
                "similarity": round(similarity, 3)
            })

        return {
            "query": request.query,
            "results": formatted_results,
            "total": len(formatted_results)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")


@router.get("/search", response_model=Dict[str, Any])
async def search_knowledge_get(
    query: str,
    company_id: str,
    doc_type: Optional[str] = None,
    top_k: int = 5
):
    """
    在知识库中进行语义搜索（GET 版本）
    """
    req = KnowledgeSearchRequest(
        query=query,
        company_id=company_id,
        doc_type=doc_type,
        top_k=top_k
    )
    return await search_knowledge(req)


@router.post("/documents/{document_id}/reindex")
async def reindex_document(document_id: str, company_id: Optional[str] = None):
    """
    重新处理和向量化文档
    用于原始处理失败的情况
    """
    if company_id:
        doc_key = f"doc:{company_id}:{document_id}"
    else:
        doc_key = f"doc:{document_id}"
    doc = redis_service.get(doc_key)

    if not doc:
        raise HTTPException(status_code=404, detail="文档未找到")

    filename = doc.get("filename", "")
    company_id = doc.get("company_id", "") or company_id or "default"
    doc_type = doc.get("doc_type", "OTHER")
    title = doc.get("title") or filename or document_id

    preview_key = f"doc_preview:{company_id}:{document_id}"
    preview_data = redis_service.get(preview_key)
    content = preview_data.get("content") if isinstance(preview_data, dict) else None
    if not content:
        raise HTTPException(status_code=400, detail="文档预览内容不存在，无法重建索引，请重新上传文档")

    try:
        chunks = document_processor.chunk_text(content)
        chunk_ids = await document_processor.vectorize_chunks(chunks, {
            **doc,
            "doc_id": document_id,
            "filename": filename,
            "title": title,
            "company_id": company_id,
            "doc_type": doc_type,
            "collection": "knowledge_base",
            "source_type": "knowledge",
        })
        doc["status"] = "INDEXED"
        doc["chunks"] = len(chunk_ids)
        doc["chunk_ids"] = chunk_ids
        redis_service.set(doc_key, doc, expire=None)
    except Exception as e:
        doc["status"] = "FAILED"
        doc["error"] = str(e)
        redis_service.set(doc_key, doc, expire=None)
        raise HTTPException(status_code=500, detail=f"文档重建索引失败: {e}")

    return {
        "status": doc["status"],
        "document_id": document_id,
        "chunks": doc.get("chunks", 0),
        "chunk_ids": doc.get("chunk_ids", []),
        "message": "文档索引已重建"
    }
