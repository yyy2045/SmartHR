"""
RAG Matcher - Vectorize resumes and jobs, perform semantic matching
"""

import math
from typing import List, Dict, Any, Optional
from pydantic import BaseModel


class MatchResult(BaseModel):
    """Match result for a single resume"""
    resume_id: str
    score: float  # 0-100
    matching_points: List[Dict[str, Any]] = []
    risk_points: List[Dict[str, Any]] = []
    summary: str = ""


class RAGMatcher:
    """RAG-based resume matching using Chroma vector store"""

    def __init__(self):
        from src.services.vector_store import vector_store_service
        from src.services.llm_service import llm_service
        self.vector_store = vector_store_service
        self.llm = llm_service
        self._embeddings = None

    def _get_embeddings(self):
        """Lazy load embeddings (OpenAI-compatible format for DeepSeek)"""
        if self._embeddings is None:
            from langchain_community.embeddings import OpenAIEmbeddings
            from src.config import settings

            self._embeddings = OpenAIEmbeddings(
                api_key=settings.deepseek_api_key,
                base_url=f"{settings.deepseek_base_url}/v1/embeddings",
                model="deepseek-embed"
            )
        return self._embeddings

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        dot = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot / (norm1 * norm2)

    def _vector_to_list(self, embedding) -> List[float]:
        """Convert embedding to list of floats"""
        if hasattr(embedding, 'tolist'):
            return embedding.tolist()
        elif isinstance(embedding, list):
            return embedding
        return list(embedding)

    async def index_resume(self, resume_id: str, text: str, metadata: Optional[Dict] = None):
        """Vectorize and store resume text in Chroma"""
        embeddings = self._get_embeddings()
        embedding_vec = embeddings.embed_query(text)
        embedding_list = self._vector_to_list(embedding_vec)

        meta = metadata or {}
        meta["type"] = "resume"

        self.vector_store.add(
            collection_name="resumes",
            documents=[text],
            embeddings=[embedding_list],
            ids=[resume_id],
            metadatas=[meta]
        )

    async def index_job(self, job_id: str, jd_text: str, metadata: Optional[Dict] = None):
        """Vectorize and store job description in Chroma"""
        embeddings = self._get_embeddings()
        embedding_vec = embeddings.embed_query(jd_text)
        embedding_list = self._vector_to_list(embedding_vec)

        meta = metadata or {}
        meta["type"] = "job"

        self.vector_store.add(
            collection_name="jobs",
            documents=[jd_text],
            embeddings=[embedding_list],
            ids=[job_id],
            metadatas=[meta]
        )

    async def search_resumes(self, query_text: str, top_k: int = 10,
                             filter_metadata: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """Search resumes by text query"""
        embeddings = self._get_embeddings()
        query_vec = embeddings.embed_query(query_text)
        query_list = self._vector_to_list(query_vec)

        return self.vector_store.search(
            collection_name="resumes",
            query_embedding=query_list,
            top_k=top_k,
            filter_metadata=filter_metadata
        )

    async def search_jobs(self, query_text: str, top_k: int = 10,
                          filter_metadata: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """Search jobs by text query"""
        embeddings = self._get_embeddings()
        query_vec = embeddings.embed_query(query_text)
        query_list = self._vector_to_list(query_vec)

        return self.vector_store.search(
            collection_name="jobs",
            query_embedding=query_list,
            top_k=top_k,
            filter_metadata=filter_metadata
        )

    async def match(self, job_id: str, resume_text: str,
                    resume_id: Optional[str] = None) -> MatchResult:
        """Match a resume against a job description"""
        # Search for similar resumes using the job as query
        similar = await self.search_resumes(resume_text, top_k=5)

        # Calculate match score based on similarity
        score = 75.0  # Default score
        if similar:
            # Use the highest similarity as the base score
            # Chroma returns distances, convert to similarity (0-1 range)
            best_dist = similar[0].get("distance", 1.0)
            # Convert distance to similarity (roughly 0-1)
            similarity = max(0, 1.0 - best_dist)
            score = min(100, 50 + similarity * 50)  # Scale 0-1 to 50-100

        # Generate match details using LLM
        matching_points, risk_points = await self._generate_match_details(
            job_text=f"Job ID: {job_id}",
            resume_text=resume_text
        )

        return MatchResult(
            resume_id=resume_id or "unknown",
            score=round(score, 1),
            matching_points=matching_points,
            risk_points=risk_points,
            summary=f"Resume matches job with score {score:.1f}/100"
        )

    async def _generate_match_details(self, job_text: str,
                                      resume_text: str) -> tuple[List[Dict], List[Dict]]:
        """Use LLM to generate matching and risk points"""
        system_prompt = """You are a professional recruiter analyzing resume-job matches.
Compare the resume against the job description.
Return a JSON object with two fields:
- matching_points: List of objects with skill, match level (high/medium/low), and details
- risk_points: List of objects with skill, match level, and missing/skewed details

Return ONLY the JSON object, no additional text."""

        user_prompt = f"""Job Description:\n{job_text}\n\nResume:\n{resume_text[:4000]}
\nAnalyze the match and return JSON."""

        result = self.llm.generate(prompt=user_prompt, system_prompt=system_prompt)

        try:
            import json
            text = result.strip()
            start_idx = text.find("{")
            end_idx = text.rfind("}")
            if start_idx != -1 and end_idx != -1:
                parsed = json.loads(text[start_idx:end_idx+1])
                return parsed.get("matching_points", []), parsed.get("risk_points", [])
        except Exception:
            pass

        return [], []

    async def index_resume_with_keyinfo(self, resume_id: str, parsed_data: Dict[str, Any],
                                         raw_text: str):
        """Index resume using parsed structured data"""
        # Combine key fields into searchable text
        skills = parsed_data.get("skills", [])
        experience = parsed_data.get("experience", [])
        education = parsed_data.get("education", [])

        text_parts = [raw_text]
        if skills:
            text_parts.append(f"Skills: {', '.join(skills)}")
        if experience:
            exp_text = ", ".join([f"{e.get('title', '')} at {e.get('company', '')}"
                                  for e in experience if isinstance(e, dict)])
            text_parts.append(f"Experience: {exp_text}")
        if education:
            edu_text = ", ".join([f"{e.get('degree', '')} at {e.get('school', '')}"
                                  for e in education if isinstance(e, dict)])
            text_parts.append(f"Education: {edu_text}")

        full_text = "\n".join(text_parts)
        metadata = {
            "candidate_name": parsed_data.get("candidate_name", ""),
            "skills": ",".join(skills) if skills else ""
        }

        await self.index_resume(resume_id, full_text, metadata)


# Global instance
rag_matcher = RAGMatcher()