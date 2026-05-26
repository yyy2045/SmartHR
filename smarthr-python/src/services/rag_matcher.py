"""
RAG 匹配器 - 对简历和岗位进行向量化和语义匹配
"""

import math
import asyncio
from typing import List, Dict, Any, Optional
from pydantic import BaseModel


class MatchResult(BaseModel):
    """单份简历的匹配结果"""
    resume_id: str
    score: float  # 0-100
    matching_points: List[Dict[str, Any]] = []
    risk_points: List[Dict[str, Any]] = []
    summary: str = ""


class RAGMatcher:
    """基于 Chroma 向量存储的 RAG 简历匹配"""

    def __init__(self):
        from src.services.vector_store import vector_store_service
        from src.services.llm_service import llm_service
        self.vector_store = vector_store_service
        self.llm = llm_service
        self._embeddings = None

    def _get_embeddings(self):
        """延迟加载嵌入向量（DeepSeek 的 OpenAI 兼容格式）"""
        if self._embeddings is None:
            from langchain_community.embeddings import OpenAIEmbeddings
            from src.config import settings

            self._embeddings = OpenAIEmbeddings(
                api_key=settings.deepseek_api_key,
                base_url=f"{settings.deepseek_base_url}/v1/embeddings",
                model="text-embedding-3-small"
            )
        return self._embeddings

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """计算两个向量的余弦相似度"""
        dot = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot / (norm1 * norm2)

    def _vector_to_list(self, embedding) -> List[float]:
        """将嵌入向量转换为浮点数列表"""
        if hasattr(embedding, 'tolist'):
            return embedding.tolist()
        elif isinstance(embedding, list):
            return embedding
        return list(embedding)

    async def index_resume(self, resume_id: str, text: str, metadata: Optional[Dict] = None):
        """将简历文本向量化和存储到 Chroma"""
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
        """将岗位描述向量化和存储到 Chroma"""
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
        """根据文本查询搜索简历"""
        embeddings = self._get_embeddings()
        query_vec = embeddings.embed_query(query_text)
        query_list = self._vector_to_list(query_vec)

        return self.vector_store.search(
            collection_name="resumes",
            query_embedding=query_list,
            top_k=top_k,
            filters=filter_metadata
        )

    async def search_jobs(self, query_text: str, top_k: int = 10,
                          filter_metadata: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """根据文本查询搜索岗位"""
        embeddings = self._get_embeddings()
        query_vec = embeddings.embed_query(query_text)
        query_list = self._vector_to_list(query_vec)

        return self.vector_store.search(
            collection_name="jobs",
            query_embedding=query_list,
            top_k=top_k,
            filters=filter_metadata
        )

    async def match(self, job_id: str, resume_text: str,
                    resume_id: Optional[str] = None,
                    job_text: str = "",
                    parsed_resume: Optional[Dict[str, Any]] = None,
                    company_id: Optional[str] = None) -> MatchResult:
        """将简历与岗位描述进行匹配

        参数:
            job_id: 岗位 ID
            resume_text: 简历原文（中文/英文均可）
            resume_id: 简历 ID
            job_text: 岗位描述全文（标题+描述+要求+技能）。若为空则 LLM 部分会跳过
            parsed_resume: 已结构化的简历数据，包含 skills/experience/education 等。
                若提供则用其替代 resume_text 全文喂 LLM，大幅降低 token
        """
        from src.services.redis_service import redis_service

        # 结果缓存：相同 (company_id, job_id, resume_id) 24h 内复用，避免重复点击烧 token
        cache_key = f"match:{company_id}:{job_id}:{resume_id or 'none'}"
        try:
            cached = redis_service.get(cache_key)
            if cached and isinstance(cached, dict) and "score" in cached:
                return MatchResult(**cached)
        except Exception as e:
            print(f"[rag_matcher] cache read failed: {e}")

        # 关键词提取（支持中英文）
        job_keywords = self._extract_keywords(job_text)
        resume_keywords = self._extract_keywords(resume_text)

        # 多维度客观评分
        score = self._calculate_objective_score(
            job_text=job_text,
            resume_text=resume_text,
            parsed_resume=parsed_resume,
            job_keywords=job_keywords,
            resume_keywords=resume_keywords
        )

        # LLM 生成匹配点和风险点（只有当 job_text 非空时才调用，避免无意义的 token 消耗）
        matching_points: List[Dict[str, Any]] = []
        risk_points: List[Dict[str, Any]] = []

        if job_text and job_text.strip():
            try:
                # 优先用结构化字段（token 仅 200~500），退回到截短的原文
                resume_brief = self._build_resume_brief(parsed_resume, resume_text)
                matching_points, risk_points = await self._generate_match_details(
                    job_text=job_text[:1500],
                    resume_brief=resume_brief
                )
            except Exception as e:
                print(f"[rag_matcher] LLM match details failed: {e}")

        result = MatchResult(
            resume_id=resume_id or "unknown",
            score=round(score, 1),
            matching_points=matching_points,
            risk_points=risk_points,
            summary=f"简历与岗位匹配分数 {score:.1f}/100"
        )

        # 写入缓存（24h）
        try:
            redis_service.set(cache_key, result.model_dump(), expire=86400)
        except Exception as e:
            print(f"[rag_matcher] cache write failed: {e}")

        return result

    def _build_resume_brief(self, parsed_resume: Optional[Dict[str, Any]],
                            resume_text: str) -> str:
        """优先用结构化的简历摘要，降低喂给 LLM 的 token"""
        if parsed_resume and isinstance(parsed_resume, dict):
            parts = []
            name = parsed_resume.get("candidate_name") or ""
            if name:
                parts.append(f"姓名：{name}")
            skills = parsed_resume.get("skills") or []
            if skills:
                parts.append(f"技能：{', '.join(str(s) for s in skills[:30])}")
            exp = parsed_resume.get("experience") or []
            if exp:
                exp_lines = []
                for e in exp[:5]:
                    if isinstance(e, dict):
                        exp_lines.append(
                            f"- {e.get('title','')} @ {e.get('company','')} "
                            f"({e.get('duration','')}): {(e.get('description') or '')[:120]}"
                        )
                if exp_lines:
                    parts.append("经历：\n" + "\n".join(exp_lines))
            edu = parsed_resume.get("education") or []
            if edu:
                edu_lines = []
                for e in edu[:3]:
                    if isinstance(e, dict):
                        edu_lines.append(
                            f"- {e.get('degree','')} {e.get('major','')} @ {e.get('school','')} ({e.get('year','')})"
                        )
                if edu_lines:
                    parts.append("教育：\n" + "\n".join(edu_lines))
            summary = parsed_resume.get("summary")
            if summary:
                parts.append(f"概要：{summary[:200]}")
            if parts:
                return "\n".join(parts)
        # 退回到截短的原文
        return (resume_text or "")[:1500]

    def _extract_keywords(self, text: str) -> set:
        """关键词提取（支持中英文）"""
        if not text:
            return set()
        import re
        # 英文/数字词（3 字以上）
        en_words = re.findall(r'\b[a-zA-Z0-9][a-zA-Z0-9+#.\-]{2,}\b', text.lower())
        en_stopwords = {
            'the', 'and', 'for', 'with', 'you', 'are', 'this', 'that', 'from',
            'have', 'has', 'was', 'will', 'can', 'your', 'job', 'job_id',
            'description', 'requirements'
        }
        en_keywords = {w for w in en_words if w not in en_stopwords}
        # 中文 2-4 字短语（粗粒度）
        cn_phrases = set(re.findall(r'[一-龥]{2,4}', text))
        cn_stopwords = {'岗位', '描述', '要求', '任职', '技能', '简历', '工作', '负责', '项目', '使用'}
        cn_keywords = cn_phrases - cn_stopwords
        return en_keywords | cn_keywords

    def _calculate_objective_score(self, job_text: str, resume_text: str,
                                   parsed_resume: Optional[Dict[str, Any]],
                                   job_keywords: set, resume_keywords: set) -> float:
        """多维度客观评分（0-100）"""
        if not job_text or not resume_text:
            return 30.0  # 缺少文本信息给低分

        # 维度1：关键词匹配率 (占40分)
        keyword_score = 0.0
        if job_keywords and resume_keywords:
            match_count = sum(1 for kw in job_keywords if kw in resume_keywords)
            recall = match_count / max(len(job_keywords), 1)
            precision = match_count / max(len(resume_keywords), 1)
            # F1 风格的综合得分
            if recall + precision > 0:
                f1 = 2 * recall * precision / (recall + precision)
                keyword_score = f1 * 40
        elif job_keywords or resume_keywords:
            keyword_score = 5.0  # 只有一个有关键词，极低

        # 维度2：技能匹配 (占30分)
        skill_score = 0.0
        if parsed_resume and isinstance(parsed_resume, dict):
            required_skills = set()
            # 从岗位描述中提技能关键词
            for kw in job_keywords:
                if len(kw) >= 2:
                    required_skills.add(kw.lower())
            resume_skills = set()
            for s in (parsed_resume.get("skills") or []):
                resume_skills.add(str(s).lower())
            if required_skills and resume_skills:
                matched = required_skills & resume_skills
                skill_score = (len(matched) / max(len(required_skills), 1)) * 30

        # 维度3：经验相关度 (占20分)
        exp_score = 0.0
        if parsed_resume and isinstance(parsed_resume, dict):
            exp_list = parsed_resume.get("experience") or []
            if exp_list:
                # 简单检查经历描述中是否包含岗位相关词
                exp_text = " ".join([
                    str(e.get("title", "")) + " " + str(e.get("description", ""))
                    for e in exp_list if isinstance(e, dict)
                ])
                exp_kw_match = sum(1 for kw in job_keywords if kw.lower() in exp_text.lower())
                exp_score = min(20.0, (exp_kw_match / max(len(job_keywords), 1)) * 20)

        # 维度4：教育背景相关度 (占10分)
        edu_score = 0.0
        if parsed_resume and isinstance(parsed_resume, dict):
            edu_list = parsed_resume.get("education") or []
            if edu_list:
                edu_text = " ".join([
                    str(e.get("major", "")) + " " + str(e.get("degree", ""))
                    for e in edu_list if isinstance(e, dict)
                ])
                edu_kw_match = sum(1 for kw in job_keywords if kw.lower() in edu_text.lower())
                edu_score = min(10.0, (edu_kw_match / max(len(job_keywords), 1)) * 10)

        total = keyword_score + skill_score + exp_score + edu_score
        return max(5.0, min(95.0, round(total, 1)))

    async def _generate_match_details(self, job_text: str,
                                      resume_brief: str) -> tuple[List[Dict], List[Dict]]:
        """使用 LLM 生成匹配点和风险点（输入精简，token 友好）"""
        system_prompt = (
            "你是招聘顾问。对比岗位描述与候选人简历，输出严格的 JSON：\n"
            "{\n"
            '  "matching_points": [ {"技能": "...(中文)", "等级": "高|中|低", "详情": "..."} ],\n'
            '  "risk_points":     [ {"技能": "...(中文)", "等级": "高|中|低", "详情": "..."} ]\n'
            "}\n"
            "技能 字段必须使用中文名称；等级 只允许填写 高、中、低；详情 控制在 30 字内。只返回 JSON。"
        )

        user_prompt = f"岗位：\n{job_text}\n\n候选人：\n{resume_brief}\n\n请按要求返回 JSON。"

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
        """使用解析后的结构化数据索引简历"""
        # 将关键字段组合为可搜索文本
        skills = parsed_data.get("skills", [])
        experience = parsed_data.get("experience", [])
        education = parsed_data.get("education", [])

        text_parts = [raw_text]
        if skills:
            text_parts.append(f"技能: {', '.join(skills)}")
        if experience:
            exp_text = ", ".join([f"{e.get('title', '')} at {e.get('company', '')}"
                                  for e in experience if isinstance(e, dict)])
            text_parts.append(f"经验: {exp_text}")
        if education:
            edu_text = ", ".join([f"{e.get('degree', '')} at {e.get('school', '')}"
                                  for e in education if isinstance(e, dict)])
            text_parts.append(f"学历: {edu_text}")

        full_text = "\n".join(text_parts)
        metadata = {
            "candidate_name": parsed_data.get("candidate_name", ""),
            "skills": ",".join(skills) if skills else ""
        }

        await self.index_resume(resume_id, full_text, metadata)


# 全局实例
rag_matcher = RAGMatcher()