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
        from src.services.rag.evidence_service import rag_evidence_service

        meta = {**(metadata or {}), "type": "resume"}
        await rag_evidence_service.index_resume(
            resume_id=str(resume_id),
            resume_text=text,
            company_id=str(meta.get("company_id") or meta.get("companyId") or "default"),
            metadata=meta,
        )

    async def index_job(self, job_id: str, jd_text: str, metadata: Optional[Dict] = None):
        """将岗位描述索引到统一 RAG pipeline。"""
        from src.services.rag.evidence_service import rag_evidence_service

        meta = {**(metadata or {}), "type": "job"}
        await rag_evidence_service.index_job(
            job_id=str(job_id),
            job_text=jd_text,
            company_id=str(meta.get("company_id") or meta.get("companyId") or "default"),
            metadata=meta,
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
        from src.services.rag.evidence_service import rag_evidence_service

        response = await rag_evidence_service.search_evidence(
            query=query_text,
            company_id=str(filter_metadata.get("company_id")) if filter_metadata and filter_metadata.get("company_id") else "default",
            source_types=[source_type],
            top_k=top_k,
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
                    job_skills: Optional[List[str]] = None,
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
        import hashlib
        import json
        from src.services.redis_service import redis_service

        # 结果缓存：把岗位正文和结构化技能纳入指纹，避免修改岗位后仍命中旧结果。
        fingerprint_payload = json.dumps(
            {"job_text": job_text or "", "job_skills": job_skills or []},
            ensure_ascii=False,
            sort_keys=True,
        )
        source_fingerprint = hashlib.sha1(fingerprint_payload.encode("utf-8")).hexdigest()[:12]
        cache_key = f"match:v7:{company_id}:{job_id}:{resume_id or 'none'}:{source_fingerprint}"
        try:
            cached = redis_service.get(cache_key)
            if cached and isinstance(cached, dict) and "score" in cached:
                return MatchResult(**cached)
        except Exception as e:
            print(f"[rag_matcher] cache read failed: {e}")

        # 岗位技能优先来自 jobs.skills，描述文本只作为“技能：...”字段兜底。
        job_keywords = self._extract_job_skills(job_text=job_text, job_skills=job_skills)
        resume_keywords = self._extract_resume_skills(resume_text, parsed_resume)
        matched_skills, missing_skills = self._skill_gap(
            job_keywords,
            resume_keywords,
            parsed_resume,
            resume_text,
        )

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

        if not matching_points and matched_skills:
            matching_points = [
                {"技能": skill, "等级": "中", "详情": "简历与岗位关键词命中"}
                for skill in matched_skills[:8]
            ]
        if not risk_points and missing_skills:
            risk_points = [
                {"技能": skill, "等级": "中", "详情": "岗位要求中存在但简历未明确体现"}
                for skill in missing_skills[:8]
            ]

        evidence: List[Dict[str, Any]] = []
        retrieval_scores: Dict[str, Any] = {}
        rank_scores: List[Dict[str, Any]] = []
        trace_id = None
        try:
            search_response = await self._search_match_evidence(
                job_id=job_id,
                resume_id=resume_id,
                job_text=job_text,
                resume_text=resume_text,
                parsed_resume=parsed_resume,
                company_id=company_id or "default",
            )
            evidence = self._dedupe_evidence([item.model_dump() for item in search_response.evidence])
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
        from src.services.rag.evidence_service import rag_evidence_service

        await rag_evidence_service.ensure_job_resume_index(
            job_id=str(job_id),
            resume_id=str(resume_id or f"inline-{job_id}"),
            job_text=job_text,
            resume_text=resume_text,
            company_id=str(company_id or "default"),
            parsed_resume=parsed_resume,
        )

    async def _search_match_evidence(
        self,
        job_id: str,
        resume_id: Optional[str],
        job_text: str,
        resume_text: str,
        parsed_resume: Optional[Dict[str, Any]],
        company_id: str,
    ):
        from src.services.rag.evidence_service import rag_evidence_service

        response = await rag_evidence_service.search_evidence(
            query=rag_evidence_service.build_match_query(
                job_text=job_text,
                resume_text=resume_text,
                parsed_resume=parsed_resume,
            ),
            company_id=str(company_id or "default"),
            source_types=["job", "resume", "knowledge"],
            top_k=24,
        )

        job_id = str(job_id)
        resume_id = str(resume_id) if resume_id is not None else None

        def allowed(source_type: str, source_id: str) -> bool:
            if source_type == "knowledge":
                return True
            if source_type == "job":
                return str(source_id) == job_id
            if source_type == "resume":
                return bool(resume_id and str(source_id) == resume_id)
            return False

        response.sources = [
            source for source in response.sources
            if allowed(source.sourceType, source.sourceId)
        ][:6]
        response.evidence = [
            item for item in response.evidence
            if allowed(item.sourceType, item.sourceId)
        ][:6]
        allowed_chunk_ids = {source.chunkId for source in response.sources}
        response.rankScores = [
            score for score in response.rankScores
            if score.get("chunkId") in allowed_chunk_ids
        ][:6]
        response.retrievalScores = {
            **response.retrievalScores,
            "evidenceScope": "current_job_resume_knowledge",
            "filteredReturned": len(response.evidence),
        }
        response.retrievalMetrics = response.retrievalScores
        return response

    def _skill_gap(
        self,
        job_keywords: set,
        resume_keywords: set,
        parsed_resume: Optional[Dict[str, Any]],
        resume_text: str = "",
    ) -> tuple[List[str], List[str]]:
        required = {str(keyword).lower() for keyword in job_keywords if len(str(keyword)) >= 2}
        resume_terms = {str(keyword).lower() for keyword in resume_keywords if len(str(keyword)) >= 2}
        if parsed_resume and isinstance(parsed_resume, dict):
            for skill in parsed_resume.get("skills") or []:
                canonical = self._canonical_skill(str(skill))
                if canonical:
                    resume_terms.add(canonical)
        matched_set = {
            skill for skill in required
            if self._resume_has_skill(skill, resume_terms, resume_text)
        }
        matched = sorted(matched_set, key=self._skill_sort_key)
        missing = sorted(required - matched_set, key=self._skill_sort_key)
        return [self._display_skill(skill) for skill in matched[:20]], [self._display_skill(skill) for skill in missing[:20]]

    def _dedupe_evidence(self, evidence: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        seen = set()
        result = []
        for item in evidence:
            key = (
                item.get("sourceType"),
                item.get("sourceId"),
                item.get("chunkId"),
                (item.get("text") or item.get("highlight") or "")[:120],
            )
            if key in seen:
                continue
            seen.add(key)
            result.append(item)
        return result

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

    # 技能解析辅助方法：用于别名归一化和文本命中判断，不作为岗位技能来源白名单。
    def _skill_aliases(self) -> Dict[str, str]:
        return {
            "python": "python",
            "go": "go",
            "golang": "go",
            "java": "java",
            "spring boot": "spring boot",
            "springboot": "spring boot",
            "mybatis-plus": "mybatis-plus",
            "mybatisplus": "mybatis-plus",
            "ssm": "ssm",
            "fastapi": "fastapi",
            "langchain": "langchain",
            "langgraph": "langgraph",
            "llamaindex": "llamaindex",
            "llama index": "llamaindex",
            "gpt": "gpt",
            "chatgpt": "gpt",
            "claude": "claude",
            "deepseek": "deepseek",
            "文心一言": "文心一言",
            "ernie": "文心一言",
            "rag": "rag",
            "milvus": "milvus",
            "pinecone": "pinecone",
            "chroma": "chroma",
            "redis": "redis",
            "mysql": "mysql",
            "docker": "docker",
            "nginx": "nginx",
            "linux": "linux",
            "vue": "vue 3",
            "vue3": "vue 3",
            "vue 3": "vue 3",
            "jwt": "jwt",
            "prompt": "prompt",
            "prompt engineering": "prompt",
            "prompt优化": "prompt",
            "prompt调优": "prompt",
            "提示词": "prompt",
        }

    def _canonical_skill(self, value: str) -> Optional[str]:
        import re

        text = str(value or "").strip().lower()
        if not text:
            return None
        compact = re.sub(r"[\s_\-/]+", "", text)
        for alias, canonical in self._skill_aliases().items():
            alias_lower = alias.lower()
            alias_compact = re.sub(r"[\s_\-/]+", "", alias_lower)
            if text == alias_lower or compact == alias_compact:
                return canonical
            if any("\u4e00" <= char <= "\u9fff" for char in alias_lower):
                if alias_lower in text or alias_compact in compact:
                    return canonical
            elif len(alias_compact) <= 3:
                pattern = rf"(?<![a-z0-9+#.\-]){re.escape(alias_lower)}(?![a-z0-9+#.\-])"
                if re.search(pattern, text):
                    return canonical
            elif alias_lower in text or alias_compact in compact:
                return canonical
        normalized = re.sub(r"\s+", " ", text.strip(" []\"'，,、；;：:")).strip()
        return normalized or None

    def _display_skill(self, skill: str) -> str:
        display = {
            "python": "Python",
            "go": "Go",
            "java": "Java",
            "spring boot": "Spring Boot",
            "mybatis-plus": "MyBatis-Plus",
            "ssm": "SSM",
            "fastapi": "FastAPI",
            "langchain": "LangChain",
            "langgraph": "LangGraph",
            "llamaindex": "LlamaIndex",
            "gpt": "GPT",
            "claude": "Claude",
            "deepseek": "DeepSeek",
            "文心一言": "文心一言",
            "rag": "RAG",
            "milvus": "Milvus",
            "pinecone": "Pinecone",
            "chroma": "Chroma",
            "redis": "Redis",
            "mysql": "MySQL",
            "docker": "Docker",
            "nginx": "Nginx",
            "linux": "Linux",
            "vue 3": "Vue 3",
            "jwt": "JWT",
            "prompt": "Prompt 调优",
        }
        if skill in display:
            return display[skill]
        if skill.replace(" ", "").replace("-", "").isalnum():
            return " ".join(part.capitalize() for part in skill.replace("-", " ").split())
        return skill

    def _skill_sort_key(self, skill: str) -> tuple[int, str]:
        priority = [
            "python", "go", "java", "fastapi", "spring boot", "mybatis-plus",
            "langchain", "langgraph", "llamaindex", "gpt", "claude", "deepseek",
            "文心一言", "rag", "milvus", "pinecone", "chroma", "redis", "mysql",
            "docker", "nginx", "linux", "vue 3", "prompt", "jwt",
        ]
        return (priority.index(skill) if skill in priority else len(priority), skill)

    def _text_mentions_skill(self, text: str, alias: str) -> bool:
        import re

        lowered = str(text or "").lower()
        alias_lower = alias.lower()
        compact_text = re.sub(r"[\s_\-/]+", "", lowered)
        compact_alias = re.sub(r"[\s_\-/]+", "", alias_lower)
        if any("\u4e00" <= char <= "\u9fff" for char in alias_lower):
            return alias_lower in lowered or compact_alias in compact_text
        if len(compact_alias) <= 3:
            pattern = rf"(?<![a-z0-9+#.\-]){re.escape(alias_lower)}(?![a-z0-9+#.\-])"
            return bool(re.search(pattern, lowered))
        return alias_lower in lowered or compact_alias in compact_text

    def _extract_keywords(self, text: str) -> set:
        """Extract only explicit technical skills, not generic Chinese phrases."""
        if not text:
            return set()
        skills = set()
        for alias, canonical in self._skill_aliases().items():
            if self._text_mentions_skill(text, alias):
                skills.add(canonical)
        return skills

    def _calculate_objective_score(self, job_text: str, resume_text: str,
                                   parsed_resume: Optional[Dict[str, Any]],
                                   job_keywords: set, resume_keywords: set) -> float:
        """Score by explicit job skill coverage plus experience evidence."""
        if not job_text or not resume_text:
            return 30.0

        required_skills = {str(skill).lower() for skill in job_keywords if skill}
        resume_skills = {str(skill).lower() for skill in resume_keywords if skill}
        if parsed_resume and isinstance(parsed_resume, dict):
            for skill in parsed_resume.get("skills") or []:
                canonical = self._canonical_skill(str(skill))
                if canonical:
                    resume_skills.add(canonical)

        if not required_skills:
            return 45.0 if resume_skills else 30.0

        matched = {
            skill for skill in required_skills
            if self._resume_has_skill(skill, resume_skills, resume_text)
        }
        recall = len(matched) / max(len(required_skills), 1)
        skill_score = recall * 60
        breadth_score = (min(len(matched), 5) / 5) * 15
        partial_score = self._partial_skill_score(required_skills - matched, resume_skills)

        exp_score = 0.0
        if parsed_resume and isinstance(parsed_resume, dict):
            exp_text = " ".join(
                f"{item.get('title', '')} {item.get('description', '')}"
                for item in (parsed_resume.get("experience") or [])
                if isinstance(item, dict)
            )
            exp_skills = self._extract_keywords(exp_text)
            if exp_skills:
                exp_matched = {
                    skill for skill in required_skills
                    if self._resume_has_skill(skill, exp_skills, exp_text)
                }
                exp_score = (len(exp_matched) / max(len(required_skills), 1)) * 15

        education_score = 5.0 if parsed_resume and parsed_resume.get("education") else 0.0
        total = skill_score + breadth_score + partial_score + exp_score + education_score
        return max(5.0, min(95.0, round(total, 1)))

    def _partial_skill_score(self, missing_required: set, resume_skills: set) -> float:
        related_groups = [
            ({"milvus", "pinecone"}, {"chroma"}, 5.0),
            ({"gpt", "claude", "文心一言"}, {"deepseek"}, 5.0),
            ({"llamaindex"}, {"langchain", "langgraph"}, 5.0),
        ]
        score = 0.0
        for required_group, alternative_group, points in related_groups:
            if missing_required & required_group and resume_skills & alternative_group:
                score += points
        return min(score, 15.0)


    def _extract_job_skills(
        self,
        *,
        job_text: str,
        job_skills: Optional[List[str]] = None,
    ) -> set:
        explicit = self._normalize_skill_list(job_skills or [])
        if explicit:
            return explicit
        return self._normalize_skill_list(self._parse_skill_candidates_from_text(job_text))

    def _extract_resume_skills(
        self,
        resume_text: str,
        parsed_resume: Optional[Dict[str, Any]],
    ) -> set:
        skills = []
        if parsed_resume and isinstance(parsed_resume, dict):
            skills.extend(parsed_resume.get("skills") or [])
        explicit = self._normalize_skill_list(skills)
        # The raw resume text is used only to detect required job skills later,
        # not to create arbitrary missing-skill candidates.
        explicit.update(self._extract_keywords(resume_text))
        return explicit

    def _normalize_skill_list(self, skills: List[Any]) -> set:
        normalized = set()
        for item in skills:
            if item is None:
                continue
            if isinstance(item, list):
                normalized.update(self._normalize_skill_list(item))
                continue
            skill = self._canonical_skill(str(item))
            if skill and not self._is_noise_skill(skill):
                normalized.add(skill)
        return normalized

    def _parse_skill_candidates_from_text(self, text: str) -> List[str]:
        import json
        import re

        candidates: List[str] = []
        if not text:
            return candidates

        for raw_array in re.findall(r"\[[^\]]+\]", text):
            try:
                parsed = json.loads(raw_array)
                if isinstance(parsed, list):
                    candidates.extend(str(item) for item in parsed)
            except Exception:
                pass

        for line in text.splitlines():
            if not re.search(r"(技能|skills|required skills|requirements)", line, re.IGNORECASE):
                continue
            value = re.split(r"[:：]", line, maxsplit=1)
            if len(value) != 2:
                continue
            candidates.extend(
                item.strip(" []\"'")
                for item in re.split(r"[,，、;/；]", value[1])
                if item.strip(" []\"'")
            )
        return candidates

    def _is_noise_skill(self, skill: str) -> bool:
        noise = {
            "岗位要求", "任职要求", "业务场景", "产品线", "体验", "具备",
            "熟练掌握", "实际项目", "本科及以上学历", "相关专业",
        }
        return skill in noise or len(skill) > 40

    def _resume_has_skill(self, required_skill: str, resume_terms: set, resume_text: str) -> bool:
        if required_skill in resume_terms:
            return True
        for group in self._equivalent_skill_groups():
            if required_skill in group and resume_terms & group:
                return True
        return self._text_mentions_skill(resume_text, required_skill)

    def _equivalent_skill_groups(self) -> List[set]:
        return [
            {"prompt", "prompt调优", "prompt优化", "提示词"},
            {"go", "golang"},
            {"vue 3", "vue3", "vue"},
        ]


rag_matcher = RAGMatcher()
