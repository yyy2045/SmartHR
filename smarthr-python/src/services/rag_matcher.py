"""
RAG 匹配器 - 对简历和岗位进行向量化和语义匹配
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class MatchResult(BaseModel):
    """单份简历的匹配结果"""
    resume_id: str
    score: float  # 0-100
    matching_points: List[Dict[str, Any]] = Field(default_factory=list)
    risk_points: List[Dict[str, Any]] = Field(default_factory=list)
    summary: str = ""
    matched_skills: List[str] = Field(default_factory=list)
    missing_skills: List[str] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)
    evidence: List[Dict[str, Any]] = Field(default_factory=list)
    trace_id: Optional[str] = None
    retrieval_scores: Dict[str, Any] = Field(default_factory=dict)
    rank_scores: List[Dict[str, Any]] = Field(default_factory=list)


class RAGMatcher:
    """基于 Chroma 向量存储的 RAG 简历匹配"""

    def __init__(self):
        from src.services.llm_service import llm_service
        self.llm = llm_service
        self.collection_name = "knowledge_base"

    async def index_resume(self, resume_id: str, text: str, metadata: Optional[Dict] = None):
        """将简历文本索引到统一 RAG pipeline。"""
        from src.services.rag.pipeline import rag_pipeline
        from src.services.rag.schemas import RagIndexRequest

        meta = {**(metadata or {}), "type": "resume"}
        await rag_pipeline.index(
            RagIndexRequest(
                companyId=str(meta.get("company_id") or meta.get("companyId") or "default"),
                sourceType="resume",
                sourceId=str(resume_id),
                title=str(meta.get("candidate_name") or meta.get("title") or f"简历 {resume_id}"),
                chunks=[text],
                collection=self.collection_name,
                metadata=meta,
            )
        )

    async def index_job(self, job_id: str, jd_text: str, metadata: Optional[Dict] = None):
        """将岗位描述索引到统一 RAG pipeline。"""
        from src.services.rag.pipeline import rag_pipeline
        from src.services.rag.schemas import RagIndexRequest

        meta = {**(metadata or {}), "type": "job"}
        await rag_pipeline.index(
            RagIndexRequest(
                companyId=str(meta.get("company_id") or meta.get("companyId") or "default"),
                sourceType="job",
                sourceId=str(job_id),
                title=str(meta.get("title") or f"岗位 {job_id}"),
                chunks=[jd_text],
                collection=self.collection_name,
                metadata=meta,
            )
        )

    async def search_resumes(self, query_text: str, top_k: int = 10,
                             filter_metadata: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """根据文本查询搜索简历。"""
        return await self._search_source_type("resume", query_text, top_k, filter_metadata)

    async def search_jobs(self, query_text: str, top_k: int = 10,
                          filter_metadata: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """根据文本查询搜索岗位。"""
        return await self._search_source_type("job", query_text, top_k, filter_metadata)

    async def _search_source_type(
        self,
        source_type: str,
        query_text: str,
        top_k: int,
        filter_metadata: Optional[Dict],
    ) -> List[Dict[str, Any]]:
        from src.services.rag.pipeline import rag_pipeline
        from src.services.rag.schemas import RagSearchRequest

        response = await rag_pipeline.search(
            RagSearchRequest(
                query=query_text,
                companyId=str(filter_metadata.get("company_id")) if filter_metadata and filter_metadata.get("company_id") else None,
                sourceTypes=[source_type],
                collection=self.collection_name,
                topK=top_k,
            )
        )
        return [
            {
                "id": source.chunkId,
                "document": source.content,
                "distance": max(0.0, 1.0 - source.score),
                "metadata": source.metadata,
            }
            for source in response.sources
        ]

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
        cache_key = f"match:v2:{company_id}:{job_id}:{resume_id or 'none'}"
        try:
            cached = redis_service.get(cache_key)
            if cached and isinstance(cached, dict) and "score" in cached:
                return MatchResult(**cached)
        except Exception as e:
            print(f"[rag_matcher] cache read failed: {e}")

        # 关键词提取（支持中英文）
        job_keywords = self._extract_keywords(job_text)
        resume_keywords = self._extract_keywords(resume_text)
        matched_skills, missing_skills = self._skill_gap(job_keywords, resume_keywords, parsed_resume)

        await self._index_match_context(
            job_id=job_id,
            resume_id=resume_id,
            job_text=job_text,
            resume_text=resume_text,
            parsed_resume=parsed_resume,
            company_id=company_id or "default",
        )

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

        evidence: List[Dict[str, Any]] = []
        retrieval_scores: Dict[str, Any] = {}
        rank_scores: List[Dict[str, Any]] = []
        trace_id = None
        try:
            search_response = await self._search_match_evidence(
                job_text=job_text,
                resume_text=resume_text,
                parsed_resume=parsed_resume,
                company_id=company_id or "default",
            )
            evidence = [item.model_dump() for item in search_response.evidence]
            retrieval_scores = search_response.retrievalScores
            rank_scores = search_response.rankScores
            trace_id = search_response.traceId
        except Exception as e:
            print(f"[rag_matcher] evidence retrieval failed: {e}")

        result = MatchResult(
            resume_id=resume_id or "unknown",
            score=round(score, 1),
            matching_points=matching_points,
            risk_points=risk_points,
            summary=f"简历与岗位匹配分数 {score:.1f}/100",
            matched_skills=matched_skills,
            missing_skills=missing_skills,
            risks=self._risk_texts(risk_points, missing_skills),
            evidence=evidence,
            trace_id=trace_id,
            retrieval_scores=retrieval_scores,
            rank_scores=rank_scores,
        )

        # 写入缓存（24h）
        try:
            redis_service.set(cache_key, result.model_dump(), expire=86400)
        except Exception as e:
            print(f"[rag_matcher] cache write failed: {e}")

        return result

    async def _index_match_context(
        self,
        job_id: str,
        resume_id: Optional[str],
        job_text: str,
        resume_text: str,
        parsed_resume: Optional[Dict[str, Any]],
        company_id: str,
    ) -> None:
        if resume_text and resume_text.strip():
            metadata = {
                "company_id": company_id,
                "candidate_name": (parsed_resume or {}).get("candidate_name", "") if isinstance(parsed_resume, dict) else "",
            }
            await self.index_resume(resume_id or f"inline-{job_id}", resume_text, metadata)
        if job_text and job_text.strip():
            await self.index_job(job_id, job_text, {"company_id": company_id})

    async def _search_match_evidence(
        self,
        job_text: str,
        resume_text: str,
        parsed_resume: Optional[Dict[str, Any]],
        company_id: str,
    ):
        from src.services.rag.pipeline import rag_pipeline
        from src.services.rag.schemas import RagSearchRequest

        resume_brief = self._build_resume_brief(parsed_resume, resume_text)
        query = "\n".join(part for part in [job_text[:700], resume_brief[:700]] if part)
        if not query.strip():
            query = "候选人与岗位匹配证据"
        return await rag_pipeline.search(
            RagSearchRequest(
                query=query,
                companyId=company_id,
                sourceTypes=["job", "resume", "knowledge"],
                collection=self.collection_name,
                topK=6,
            )
        )

    def _skill_gap(
        self,
        job_keywords: set,
        resume_keywords: set,
        parsed_resume: Optional[Dict[str, Any]],
    ) -> tuple[List[str], List[str]]:
        required = {str(keyword).lower() for keyword in job_keywords if len(str(keyword)) >= 2}
        resume_terms = {str(keyword).lower() for keyword in resume_keywords if len(str(keyword)) >= 2}
        if parsed_resume and isinstance(parsed_resume, dict):
            resume_terms.update(str(skill).lower() for skill in parsed_resume.get("skills") or [])
        matched = sorted(required & resume_terms)
        missing = sorted(required - resume_terms)
        return matched[:20], missing[:20]

    def _risk_texts(self, risk_points: List[Dict[str, Any]], missing_skills: List[str]) -> List[str]:
        risks = []
        for risk in risk_points:
            if not isinstance(risk, dict):
                continue
            text = risk.get("详情") or risk.get("details") or risk.get("description")
            skill = risk.get("技能") or risk.get("skill")
            if text and skill:
                risks.append(f"{skill}: {text}")
            elif text:
                risks.append(str(text))
        if not risks and missing_skills:
            risks = [f"缺少岗位关键词或技能: {skill}" for skill in missing_skills[:5]]
        return risks

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
