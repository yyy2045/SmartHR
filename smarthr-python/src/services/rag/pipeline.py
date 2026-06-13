"""Unified RAG indexing and hybrid retrieval pipeline."""

import json
import time
import uuid
from typing import Any, Dict, List

from src.services.rag.bm25_store import bm25_store
from src.services.rag.embedding_service import embedding_service
from src.services.rag.schemas import RagIndexRequest, RagIndexResponse, RagSearchRequest, RagSearchResponse, RagSource
from src.services.vector_store import vector_store_service


class RagPipeline:
    """Index and search documents through vector and keyword retrieval."""

    async def index(self, request: RagIndexRequest) -> RagIndexResponse:
        cleaned_chunks = [chunk.strip() for chunk in request.chunks if chunk and chunk.strip()]
        if not cleaned_chunks:
            return RagIndexResponse(
                status="empty",
                collection=request.collection,
                sourceId=request.sourceId,
                chunkIds=[],
            )

        chunk_ids = [
            f"{request.sourceType}:{request.sourceId}:chunk:{idx}"
            for idx, _ in enumerate(cleaned_chunks)
        ]
        metadatas = [
            self._build_metadata(request, chunk_id, idx)
            for idx, chunk_id in enumerate(chunk_ids)
        ]
        embeddings = await embedding_service.embed_documents(cleaned_chunks)

        # Chroma add is not idempotent; delete first so reindex works.
        vector_store_service.delete(request.collection, chunk_ids)
        vector_store_service.add(
            collection_name=request.collection,
            documents=cleaned_chunks,
            embeddings=embeddings,
            ids=chunk_ids,
            metadatas=metadatas,
        )
        bm25_store.add(request.collection, cleaned_chunks, chunk_ids, metadatas)

        return RagIndexResponse(
            status="indexed",
            collection=request.collection,
            sourceId=request.sourceId,
            chunkIds=chunk_ids,
        )

    async def search(self, request: RagSearchRequest) -> RagSearchResponse:
        trace_id = str(uuid.uuid4())
        started = time.time()
        filters = self._build_filters(request)
        query_embedding = await embedding_service.embed_query(request.query)
        vector_results = vector_store_service.search(
            collection_name=request.collection,
            query_embedding=query_embedding,
            top_k=max(request.topK * 3, request.topK),
            filters=filters,
        )
        keyword_results = bm25_store.search(
            collection=request.collection,
            query=request.query,
            top_k=max(request.topK * 3, request.topK),
            filters=filters,
        )

        merged = self._merge_results(vector_results, keyword_results, request.sourceTypes)
        sources = merged[:request.topK]
        return RagSearchResponse(
            query=request.query,
            sources=sources,
            traceId=trace_id,
            retrievalMetrics={
                "vectorCandidates": len(vector_results),
                "keywordCandidates": len(keyword_results),
                "returned": len(sources),
                "latencyMs": round((time.time() - started) * 1000, 2),
                "collection": request.collection,
            },
        )

    def _build_metadata(self, request: RagIndexRequest, chunk_id: str, idx: int) -> Dict[str, Any]:
        metadata = {
            **request.metadata,
            "companyId": request.companyId,
            "company_id": request.companyId,
            "sourceType": request.sourceType,
            "source_type": request.sourceType,
            "sourceId": request.sourceId,
            "source_id": request.sourceId,
            "chunkId": chunk_id,
            "chunk_id": chunk_id,
            "chunkIndex": idx,
            "title": request.title,
        }
        return {
            key: self._metadata_value(value)
            for key, value in metadata.items()
            if value is not None
        }

    def _metadata_value(self, value: Any) -> Any:
        if isinstance(value, (str, int, float, bool)):
            return value
        return json.dumps(value, ensure_ascii=False, default=str)

    def _build_filters(self, request: RagSearchRequest) -> Dict[str, Any] | None:
        filters = {}
        if request.companyId:
            filters["company_id"] = request.companyId
        return filters or None

    def _merge_results(
        self,
        vector_results: List[Dict[str, Any]],
        keyword_results: List[Dict[str, Any]],
        source_types: List[str],
    ) -> List[RagSource]:
        by_id: Dict[str, Dict[str, Any]] = {}
        for item in vector_results:
            chunk_id = item.get("id")
            if not chunk_id:
                continue
            metadata = item.get("metadata") or {}
            if source_types and metadata.get("sourceType") not in source_types:
                continue
            distance = item.get("distance")
            vector_score = max(0.0, 1.0 - float(distance)) if distance is not None else 0.0
            by_id.setdefault(chunk_id, {
                "id": chunk_id,
                "document": item.get("document", ""),
                "metadata": metadata,
                "vectorScore": vector_score,
                "keywordScore": 0.0,
            })
        max_keyword = max([item.get("keywordScore", 0.0) for item in keyword_results] or [0.0])
        for item in keyword_results:
            chunk_id = item.get("id")
            if not chunk_id:
                continue
            metadata = item.get("metadata") or {}
            if source_types and metadata.get("sourceType") not in source_types:
                continue
            normalized_keyword = (item.get("keywordScore", 0.0) / max_keyword) if max_keyword > 0 else 0.0
            current = by_id.setdefault(chunk_id, {
                "id": chunk_id,
                "document": item.get("document", ""),
                "metadata": metadata,
                "vectorScore": 0.0,
                "keywordScore": 0.0,
            })
            current["keywordScore"] = max(current.get("keywordScore", 0.0), normalized_keyword)

        sources = []
        for item in by_id.values():
            metadata = item.get("metadata") or {}
            vector_score = float(item.get("vectorScore") or 0.0)
            keyword_score = float(item.get("keywordScore") or 0.0)
            score = 0.7 * vector_score + 0.3 * keyword_score
            sources.append(RagSource(
                sourceType=metadata.get("sourceType") or metadata.get("source_type") or "unknown",
                sourceId=str(metadata.get("sourceId") or metadata.get("source_id") or ""),
                chunkId=str(metadata.get("chunkId") or metadata.get("chunk_id") or item.get("id")),
                title=str(metadata.get("title") or metadata.get("filename") or ""),
                content=item.get("document", ""),
                score=round(score, 4),
                vectorScore=round(vector_score, 4),
                keywordScore=round(keyword_score, 4),
                metadata=metadata,
            ))
        sources.sort(key=lambda source: source.score, reverse=True)
        return sources


rag_pipeline = RagPipeline()
