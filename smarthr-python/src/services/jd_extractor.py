"""
JD (Job Description) Key Information Extractor
Extract key skills, experience requirements, education from JD text
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel


class JDKeyInfo(BaseModel):
    """Structured JD key information"""
    skills: List[str] = []
    experience_years: Optional[int] = None
    education: str = ""
    summary: str = ""
    requirements: List[str] = []


class JDExtractor:
    """Extract key information from job descriptions using LLM"""

    def __init__(self):
        from src.services.llm_service import llm_service
        self.llm = llm_service

    def _build_extraction_prompt(self, jd_text: str) -> tuple[str, str]:
        """Build prompts for JD extraction"""
        system_prompt = """You are a professional job description analyzer. Extract key information from the JD.
Return a JSON object with the following fields:
- skills: List of required technical skills (array of strings, e.g., ["Python", "Java", "SQL"])
- experience_years: Minimum years of experience required (number), null if not specified
- education: Minimum education requirement (string, e.g., "Bachelor's in Computer Science")
- summary: Brief 2-3 sentence summary of the role (string)
- requirements: List of key job requirements (array of strings)

Return ONLY the JSON object, no additional text."""

        user_prompt = f"Please analyze this job description and extract key information:\n\n{jd_text[:8000]}"
        return system_prompt, user_prompt

    def _parse_json_response(self, text: str) -> Dict[str, Any]:
        """Extract JSON from LLM response"""
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

    async def extract(self, jd_text: str) -> JDKeyInfo:
        """Extract key information from JD text"""
        system_prompt, user_prompt = self._build_extraction_prompt(jd_text)
        result = self.llm.generate(prompt=user_prompt, system_prompt=system_prompt)

        parsed = self._parse_json_response(result)
        return JDKeyInfo(
            skills=parsed.get("skills", []),
            experience_years=parsed.get("experience_years"),
            education=parsed.get("education", ""),
            summary=parsed.get("summary", ""),
            requirements=parsed.get("requirements", [])
        )


# Global instance
jd_extractor = JDExtractor()