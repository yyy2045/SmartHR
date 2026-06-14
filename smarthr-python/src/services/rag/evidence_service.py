"""Business-facing RAG indexing and evidence helpers."""

from typing import Any, Dict, List, Optional

from src.services.rag.chunker import semantic_chunk_text
from src.services.rag.pipeline import rag_pipeline
from src.services.rag.schemas import RagIndexRequest, RagSearchRequest, RagSearchResponse


class RagEvidenceService:
    """Keep job, resume, knowledge and interview evidence on the same RAG contract."""

    def __init__(self):
        self.collection = "knowledge_base"

    def chunk_text(self, text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
        return semantic_chunk_text(text, chunk_size=chunk_size, overlap=overlap)

    async def index_text(
        self,
        *,
        source_type: str,
        source_id: str,
        title: str,
        text: str,
        company_id: str = "default",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        chunks = self.chunk_text(text)
        if not chunks:
            return []
        response = await rag_pipeline.index(
            RagIndexRequest(
                companyId=str(company_id or "default"),
                sourceType=source_type,
                sourceId=str(source_id),
                title=title,
                chunks=chunks,
                collection=self.collection,
                metadata=metadata or {},
            )
        )
        return response.chunkIds

    async def index_job(
        self,
        job_id: str,
        job_text: str,
        company_id: str = "default",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        meta = {**(metadata or {}), "type": "job", "company_id": str(company_id or "default")}
        return await self.index_text(
            source_type="job",
            source_id=str(job_id),
            title=str(meta.get("title") or f"岗位 {job_id}"),
            text=job_text,
            company_id=str(company_id or "default"),
            metadata=meta,
        )

    async def index_resume(
        self,
        resume_id: str,
        resume_text: str,
        company_id: str = "default",
        parsed_resume: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        parsed = parsed_resume if isinstance(parsed_resume, dict) else {}
        meta = {
            **(metadata or {}),
            "type": "resume",
            "company_id": str(company_id or "default"),
            "candidate_name": parsed.get("candidate_name", ""),
            "skills": ",".join(str(skill) for skill in (parsed.get("skills") or [])),
        }
        return await self.index_text(
            source_type="resume",
            source_id=str(resume_id),
            title=str(meta.get("candidate_name") or meta.get("title") or f"简历 {resume_id}"),
            text=resume_text,
            company_id=str(company_id or "default"),
            metadata=meta,
        )

    async def index_interview_turn(
        self,
        *,
        session_id: str,
        turn_id: str,
        question: str,
        answer: str,
        company_id: str = "default",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        text = f"问题：{question}\n回答：{answer}".strip()
        meta = {**(metadata or {}), "type": "interview", "session_id": session_id}
        return await self.index_text(
            source_type="interview",
            source_id=f"{session_id}:{turn_id}",
            title=f"面试记录 {session_id}",
            text=text,
            company_id=str(company_id or "default"),
            metadata={**meta, "turn_id": turn_id},
        )

    async def ensure_job_resume_index(
        self,
        *,
        job_id: str,
        resume_id: str,
        job_text: str,
        resume_text: str,
        company_id: str = "default",
        parsed_resume: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, List[str]]:
        result = {"job": [], "resume": []}
        if job_text and job_text.strip():
            result["job"] = await self.index_job(job_id, job_text, company_id)
        if resume_text and resume_text.strip():
            result["resume"] = await self.index_resume(resume_id, resume_text, company_id, parsed_resume)
        return result

    async def search_evidence(
        self,
        *,
        query: str,
        company_id: str = "default",
        source_types: Optional[List[str]] = None,
        top_k: int = 6,
    ) -> RagSearchResponse:
        return await rag_pipeline.search(
            RagSearchRequest(
                query=query,
                companyId=str(company_id or "default"),
                sourceTypes=source_types or ["job", "resume", "knowledge", "interview"],
                collection=self.collection,
                topK=top_k,
            )
        )

    def build_match_query(
        self,
        *,
        job_text: str,
        resume_text: str,
        parsed_resume: Optional[Dict[str, Any]] = None,
    ) -> str:
        resume_brief = self.build_resume_brief(parsed_resume, resume_text)
        query = "\n".join(part for part in [job_text[:900], resume_brief[:900]] if part)
        return query.strip() or "候选人与岗位匹配证据"

    def build_resume_brief(self, parsed_resume: Optional[Dict[str, Any]], resume_text: str) -> str:
        if parsed_resume and isinstance(parsed_resume, dict):
            parts = []
            name = parsed_resume.get("candidate_name") or ""
            if name:
                parts.append(f"姓名：{name}")
            skills = parsed_resume.get("skills") or []
            if skills:
                parts.append(f"技能：{', '.join(str(skill) for skill in skills[:30])}")
            experience = parsed_resume.get("experience") or []
            for item in experience[:5]:
                if isinstance(item, dict):
                    parts.append(
                        f"经历：{item.get('title', '')} {item.get('company', '')} "
                        f"{(item.get('description') or '')[:160]}"
                    )
            if parts:
                return "\n".join(parts)
        return (resume_text or "")[:1500]


rag_evidence_service = RagEvidenceService()
