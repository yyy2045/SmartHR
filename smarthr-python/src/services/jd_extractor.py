"""
JD（岗位描述）关键信息提取器
从 JD 文本中提取关键技能、经验要求、学历等
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel


class JDKeyInfo(BaseModel):
    """岗位关键信息结构"""
    skills: List[str] = []
    experience_years: Optional[int] = None
    education: str = ""
    summary: str = ""
    requirements: List[str] = []


class JDExtractor:
    """使用 LLM 从岗位描述中提取关键信息"""

    def __init__(self):
        from src.services.llm_service import llm_service
        self.llm = llm_service

    def _build_extraction_prompt(self, jd_text: str) -> tuple[str, str]:
        """构建 JD 提取提示"""
        system_prompt = """你是一个专业的岗位描述分析师。从 JD 中提取关键信息。
返回包含以下字段的 JSON 对象：
- skills: 所需技术技能列表（字符串数组，如 ["Python", "Java", "SQL"]）
- experience_years: 最低工作经验年限（数字），未指定则为 null
- education: 最低学历要求（字符串，如 "计算机科学学士"）
- summary: 职位简要 2-3 句 summary（字符串）
- requirements: 关键岗位要求列表（字符串数组）

只返回 JSON 对象，不要添加其他文本。"""

        user_prompt = f"请分析此岗位描述并提取关键信息：\n\n{jd_text[:8000]}"
        return system_prompt, user_prompt

    def _parse_json_response(self, text: str) -> Dict[str, Any]:
        """从 LLM 响应中提取 JSON"""
        text = text.strip()

        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])

        text = text.strip("`")

        start_idx = text.find("{")
        end_idx = text.rfind("}")

        if start_idx != -1 and end_idx != -1:
            import json
            try:
                return json.loads(text[start_idx:end_idx+1])
            except json.JSONDecodeError:
                pass

        return {
            "skills": [],
            "experience_years": None,
            "education": "",
            "summary": text[:500],
            "requirements": []
        }

    def extract(self, jd_text: str) -> JDKeyInfo:
        """从 JD 文本中提取关键信息"""
        system_prompt, user_prompt = self._build_extraction_prompt(jd_text)
        result = self.llm.generate(prompt=user_prompt, system_prompt=system_prompt)

        parsed = self._parse_json_response(result)
        experience_years = parsed.get("experience_years")
        if experience_years is not None:
            try:
                experience_years = int(experience_years)
            except (ValueError, TypeError):
                experience_years = None
        return JDKeyInfo(
            skills=parsed.get("skills", []),
            experience_years=experience_years,
            education=parsed.get("education", ""),
            summary=parsed.get("summary", ""),
            requirements=parsed.get("requirements", [])
        )


# 全局实例
jd_extractor = JDExtractor()