"""
Resume Parser Service - Extract text from PDF/Word and parse with LLM
"""

import re
import json
from typing import Optional, Dict, Any, List
from pathlib import Path

# Text extraction
try:
    import PyPDF2
except ImportError:
    PyPDF2 = None

try:
    from docx import Document
except ImportError:
    Document = None


class ResumeParser:
    """Parse resume files (PDF/Word) into structured data using LLM"""

    def __init__(self):
        from src.services.llm_service import llm_service
        self.llm = llm_service

    def extract_text_from_file(self, file_path: str) -> str:
        """Extract raw text from PDF or Word file"""
        path = Path(file_path)
        suffix = path.suffix.lower()

        if suffix == ".pdf":
            return self._extract_pdf(file_path)
        elif suffix in [".docx", ".doc"]:
            return self._extract_docx(file_path)
        else:
            raise ValueError(f"Unsupported file format: {suffix}")

    def _extract_pdf(self, file_path: str) -> str:
        """Extract text from PDF using PyPDF2"""
        if PyPDF2 is None:
            raise ImportError("PyPDF2 not installed")
        text = []
        with open(file_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text.append(page_text)
        return "\n".join(text)

    def _extract_docx(self, file_path: str) -> str:
        """Extract text from Word document"""
        if Document is None:
            raise ImportError("python-docx not installed")
        doc = Document(file_path)
        return "\n".join([para.text for para in doc.paragraphs])

    def _build_parsing_prompt(self, raw_text: str) -> tuple[str, str]:
        """Build system and user prompts for LLM parsing"""
        system_prompt = """You are a professional resume parser. Extract structured information from the resume text.
Return a JSON object with the following fields:
- candidate_name: The person's full name (string)
- email: Email address (string)
- phone: Phone number (string)
- skills: List of technical and soft skills (array of strings)
- experience: List of work experiences, each with company, title, duration, description (array of objects)
- education: List of education records with school, degree, field, year (array of objects)
- summary: Brief 2-3 sentence summary of the candidate (string)

Return ONLY the JSON object, no additional text."""

        user_prompt = f"Please parse this resume and return structured data:\n\n{raw_text[:8000]}"
        return system_prompt, user_prompt

    async def parse_text(self, raw_text: str) -> Dict[str, Any]:
        """Parse resume raw text into structured data using LLM"""
        system_prompt, user_prompt = self._build_parsing_prompt(raw_text)
        result = self.llm.generate(prompt=user_prompt, system_prompt=system_prompt)

        # Parse LLM response as JSON
        parsed = self._parse_json_response(result)
        return parsed

    def _parse_json_response(self, text: str) -> Dict[str, Any]:
        """Extract JSON from LLM response"""
        # Try to find JSON in the response
        text = text.strip()

        # Handle cases where LLM returns markdown code block
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1]) if lines[-1].endswith("```") else "\n".join(lines[1:])

        text = text.strip("`")

        # Try to find JSON object
        start_idx = text.find("{")
        end_idx = text.rfind("}")

        if start_idx != -1 and end_idx != -1:
            json_str = text[start_idx:end_idx+1]
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                pass

        # Fallback: return with summary only
        return {
            "candidate_name": None,
            "email": None,
            "phone": None,
            "skills": [],
            "experience": [],
            "education": [],
            "summary": text[:500]
        }

    async def parse(self, file_path: str = None, raw_text: str = None) -> Dict[str, Any]:
        """Main entry point - parse from file or raw text"""
        if file_path:
            text = self.extract_text_from_file(file_path)
        elif raw_text:
            text = raw_text
        else:
            raise ValueError("Either file_path or raw_text must be provided")

        return await self.parse_text(text)

    async def parse_with_file_content(self, file_path: str, file_content: bytes) -> Dict[str, Any]:
        """Parse resume from uploaded file content (bytes)"""
        import tempfile
        import os

        suffix = Path(file_path).suffix.lower()
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(file_content)
            tmp_path = tmp.name

        try:
            return await self.parse(file_path=tmp_path)
        finally:
            os.unlink(tmp_path)


# Global instance
resume_parser = ResumeParser()