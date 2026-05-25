"""
简历解析服务 - 从 PDF/Word 提取文本并使用 LLM 解析
"""

import re
import json
from typing import Optional, Dict, Any, List
from pathlib import Path

# 文本提取
try:
    import PyPDF2
except ImportError:
    PyPDF2 = None

try:
    from docx import Document
except ImportError:
    Document = None


class ResumeParser:
    """解析简历文件（PDF/Word）为使用 LLM 的结构化数据"""

    def __init__(self):
        from src.services.llm_service import llm_service
        self.llm = llm_service

    def extract_text_from_file(self, file_path: str) -> str:
        """从 PDF 或 Word 文件提取原始文本"""
        path = Path(file_path)
        suffix = path.suffix.lower()

        if suffix == ".pdf":
            return self._extract_pdf(file_path)
        elif suffix in [".docx", ".doc"]:
            return self._extract_docx(file_path)
        else:
            raise ValueError(f"不支持的文件格式: {suffix}")

    def _extract_pdf(self, file_path: str) -> str:
        """使用 PyPDF2 从 PDF 提取文本"""
        if PyPDF2 is None:
            raise ImportError("未安装 PyPDF2")
        text = []
        with open(file_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text.append(page_text)
        return "\n".join(text)

    def _extract_docx(self, file_path: str) -> str:
        """从 Word 文档提取文本"""
        if Document is None:
            raise ImportError("未安装 python-docx")
        doc = Document(file_path)
        return "\n".join([para.text for para in doc.paragraphs])

    def _build_parsing_prompt(self, raw_text: str) -> tuple[str, str]:
        """构建 LLM 解析的系统提示和用户提示"""
        system_prompt = """你是一个专业的简历解析器。从简历文本中提取结构化信息。
返回包含以下字段的 JSON 对象（必须使用 snake_case 命名）：
- candidate_name: 姓名（字符串）
- email: 电子邮箱（字符串）
- phone: 电话号码（字符串）
- skills: 技术技能和软技能列表（字符串数组）
- experience: 工作经验列表，每个包含 company, title, duration, description（对象数组）
- education: 教育经历列表，包含 school, degree, major, year（对象数组）
- summary: 候选人简要 2-3 句 summary（字符串）

重要：返回的 JSON 对象必须使用 snake_case 作为 key 名称，例如 candidate_name 而不是 candidateName。
只返回 JSON 对象，不要添加其他文本。"""

        user_prompt = f"请解析此简历并返回结构化数据：\n\n{raw_text[:8000]}"
        return system_prompt, user_prompt

    async def parse_text(self, raw_text: str) -> Dict[str, Any]:
        """使用 LLM 将简历原文解析为结构化数据"""
        system_prompt, user_prompt = self._build_parsing_prompt(raw_text)
        result = self.llm.generate(prompt=user_prompt, system_prompt=system_prompt)

        # 解析 LLM 响应为 JSON
        parsed = self._parse_json_response(result)
        return parsed

    def _parse_json_response(self, text: str) -> Dict[str, Any]:
        """从 LLM 响应中提取 JSON"""
        # 尝试从响应中找到 JSON
        text = text.strip()

        # 处理 LLM 返回 markdown 代码块的情况
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1]) if lines[-1].endswith("```") else "\n".join(lines[1:])

        text = text.strip("`")

        # 尝试找到 JSON 对象
        start_idx = text.find("{")
        end_idx = text.rfind("}")

        if start_idx != -1 and end_idx != -1:
            json_str = text[start_idx:end_idx+1]
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                pass

        # 降级方案：只返回摘要
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
        """主要入口方法 - 从文件或原文解析"""
        if file_path:
            text = self.extract_text_from_file(file_path)
        elif raw_text:
            text = raw_text
        else:
            raise ValueError("必须提供 file_path 或 raw_text 之一")

        return await self.parse_text(text)

    async def parse_with_file_content(self, file_path: str, file_content: bytes) -> tuple[Dict[str, Any], str]:
        """从上传的文件内容（字节）解析简历，返回(解析结果, 原始文本)"""
        import tempfile
        import os

        suffix = Path(file_path).suffix.lower() if file_path else ""
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(file_content)
                tmp_path = tmp.name
            raw_text = self.extract_text_from_file(tmp_path)
            parsed = await self.parse_text(raw_text)
            return parsed, raw_text
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.unlink(tmp_path)


# 全局实例
resume_parser = ResumeParser()