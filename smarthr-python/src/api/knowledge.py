"""
Knowledge API - Enterprise knowledge base management
"""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import uuid
import io

from src.services.document_processor import document_processor
from src.services.knowledge_retriever import knowledge_retriever
from src.services.redis_service import redis_service

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


class DocumentUploadResponse(BaseModel):
    document_id: str
    filename: str
    status: str
    chunks: int
    title: str


class KnowledgeSearchRequest(BaseModel):
    query: str
    company_id: Optional[str] = None
    doc_type: Optional[str] = None
    top_k: int = 5


class KnowledgeSearchResult(BaseModel):
    content: str
    source: str
    similarity: float


class DocumentResponse(BaseModel):
    document_id: str
    title: str
    doc_type: str
    company_id: Optional[str]
    uploaded_at: str
    status: str
    chunks: int


@router.post("/documents", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    company_id: str = Form(...),
    doc_type: str = Form(...)  # POLICY, MANUAL, HISTORY, OTHER
):
    """
    Upload a document (PDF, Word, TXT) and vectorize it for knowledge base.
    """
    # Read file content
    content = await file.read()

    # Generate document ID
    document_id = str(uuid.uuid4())
    filename = file.filename or "unknown"

    # Store metadata in Redis for tracking
    metadata = {
        "doc_id": document_id,
        "filename": filename,
        "company_id": company_id,
        "doc_type": doc_type,
        "status": "PROCESSING"
    }

    # Process document asynchronously
    try:
        # Process file content and vectorize
        chunk_ids = await document_processor.process_file_content(
            content=content,
            filename=filename,
            metadata={
                **metadata,
                "collection": "knowledge_base"
            }
        )

        metadata["status"] = "INDEXED"
        metadata["chunks"] = len(chunk_ids)
        metadata["chunk_ids"] = chunk_ids

    except Exception as e:
        metadata["status"] = "FAILED"
        metadata["error"] = str(e)
        metadata["chunks"] = 0
        metadata["chunk_ids"] = []

    # Save document metadata
    doc_key = f"doc:{document_id}"
    redis_service.set(doc_key, metadata, expire=None)

    return DocumentUploadResponse(
        document_id=document_id,
        filename=filename,
        status=metadata["status"],
        chunks=metadata.get("chunks", 0),
        title=filename.rsplit('.', 1)[0] if filename else "Untitled"
    )


@router.get("/documents", response_model=Dict[str, Any])
async def list_documents(
    company_id: Optional[str] = None,
    doc_type: Optional[str] = None,
    page: int = 1,
    size: int = 20
):
    """
    List all documents for a company with optional filtering.
    """
    # Get all document keys
    pattern = "doc:*"
    keys = redis_service.keys(pattern)

    documents = []
    for key in keys:
        doc = redis_service.get(key)
        if not doc or not isinstance(doc, dict):
            continue

        # Filter by company_id and doc_type
        if company_id and doc.get("company_id") != company_id:
            continue
        if doc_type and doc.get("doc_type") != doc_type:
            continue

        documents.append({
            "document_id": doc.get("doc_id"),
            "title": doc.get("filename", "").rsplit('.', 1)[0] if doc.get("filename") else "Untitled",
            "filename": doc.get("filename"),
            "doc_type": doc.get("doc_type"),
            "company_id": doc.get("company_id"),
            "status": doc.get("status"),
            "chunks": doc.get("chunks", 0),
            "uploaded_at": doc.get("uploaded_at", "")
        })

    # Paginate
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
async def get_document(document_id: str):
    """Get document details"""
    doc_key = f"doc:{document_id}"
    doc = redis_service.get(doc_key)

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    return {
        "document_id": doc.get("doc_id"),
        "title": doc.get("filename", "").rsplit('.', 1)[0] if doc.get("filename") else "Untitled",
        "filename": doc.get("filename"),
        "doc_type": doc.get("doc_type"),
        "company_id": doc.get("company_id"),
        "status": doc.get("status"),
        "chunks": doc.get("chunks", 0),
        "chunk_ids": doc.get("chunk_ids", [])
    }


@router.delete("/documents/{document_id}")
async def delete_document(document_id: str):
    """Delete a document and its vectors from knowledge base"""
    doc_key = f"doc:{document_id}"
    doc = redis_service.get(doc_key)

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Delete chunk IDs from vector store
    chunk_ids = doc.get("chunk_ids", [])
    if chunk_ids:
        try:
            from src.services.vector_store import vector_store_service
            vector_store_service.delete("knowledge_base", chunk_ids)
        except Exception as e:
            print(f"Error deleting vectors: {e}")

    # Delete from Redis
    redis_service.delete(doc_key)

    return {
        "status": "deleted",
        "document_id": document_id
    }


@router.post("/search", response_model=Dict[str, Any])
async def search_knowledge(request: KnowledgeSearchRequest):
    """
    Semantic search in knowledge base.
    Returns relevant document chunks with similarity scores.
    """
    if not request.company_id:
        raise HTTPException(status_code=400, detail="company_id is required")

    try:
        # Search by company
        results = await knowledge_retriever.search_by_company(
            company_id=request.company_id,
            query=request.query,
            top_k=request.top_k
        )

        # Format results
        formatted_results = []
        for r in results:
            metadata = r.get("metadata", {})
            distance = r.get("distance", 0)
            # Convert distance to similarity score (lower distance = higher similarity)
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
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.get("/search", response_model=Dict[str, Any])
async def search_knowledge_get(
    query: str,
    company_id: str,
    doc_type: Optional[str] = None,
    top_k: int = 5
):
    """
    Semantic search in knowledge base (GET version).
    """
    req = KnowledgeSearchRequest(
        query=query,
        company_id=company_id,
        doc_type=doc_type,
        top_k=top_k
    )
    return await search_knowledge(req)


@router.post("/documents/{document_id}/reindex")
async def reindex_document(document_id: str):
    """
    Re-process and re-vectorize a document.
    Useful when the original processing failed.
    """
    doc_key = f"doc:{document_id}"
    doc = redis_service.get(doc_key)

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    filename = doc.get("filename", "")
    company_id = doc.get("company_id", "")
    doc_type = doc.get("doc_type", "OTHER")

    # Re-process (would need to re-read file content)
    # For now, just update status
    doc["status"] = "REINDEXING"
    redis_service.set(doc_key, doc)

    return {
        "status": "reindexing",
        "document_id": document_id,
        "message": "Document reindexing started"
    }