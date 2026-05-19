"""
简历 API - 简历解析与匹配接口
"""

from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import uuid

router = APIRouter(prefix="/api/resume", tags=["简历"])


class ResumeParseRequest(BaseModel):
    """简历解析请求"""
    raw_text: str


class ResumeMatchRequest(BaseModel):
    """简历匹配请求"""
    resume_id: str
    job_id: str
    resume_text: str
    job_text: Optional[str] = ""
    parsed_resume: Optional[Dict[str, Any]] = None


class ParsedResume(BaseModel):
    """解析后的简历数据"""
    candidate_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    skills: List[str] = []
    experience: List[Dict[str, Any]] = []
    education: List[Dict[str, Any]] = []
    summary: Optional[str] = None


@router.post("/upload")
async def upload_resume(file: UploadFile = File(...)):
    """
    上传并解析简历文件（PDF 或 Word）
    使用 LLM 从文本中提取结构化数据
    """
    from src.services.resume_parser import resume_parser

    # 验证文件类型
    allowed_types = ["application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail=f"不支持的文件类型: {file.content_type}")

    # 读取文件内容
    content = await file.read()

    # 生成简历 ID
    resume_id = str(uuid.uuid4())

    try:
        # 解析简历，获取原始文本和结构化数据
        parsed, raw_text = await resume_parser.parse_with_file_content(file.filename, content)

        return {
            "resume_id": resume_id,
            "status": "parsed",
            "data": parsed,
            "raw_text": raw_text,
            "file_name": file.filename
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"简历解析失败: {str(e)}")


@router.post("/parse")
async def parse_resume(request: ResumeParseRequest):
    """
    使用 LLM 将简历原文解析为结构化数据
    """
    from src.services.resume_parser import resume_parser

    try:
        parsed = await resume_parser.parse_text(request.raw_text)
        return {
            "status": "parsed",
            "data": parsed
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"简历解析失败: {str(e)}")


@router.post("/match")
async def match_resume(request: ResumeMatchRequest):
    """
    使用 RAG 将简历与岗位描述进行匹配
    """
    from src.services.rag_matcher import rag_matcher

    try:
        result = await rag_matcher.match(
            job_id=request.job_id,
            resume_text=request.resume_text,
            resume_id=request.resume_id,
            job_text=request.job_text or "",
            parsed_resume=request.parsed_resume
        )

        return {
            "status": "matched",
            "resume_id": result.resume_id,
            "match_score": result.score,
            "matching_points": result.matching_points,
            "risk_points": result.risk_points,
            "summary": result.summary
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"简历匹配失败: {str(e)}")


@router.get("/{resume_id}")
async def get_resume(resume_id: str):
    """根据 ID 获取简历（占位 - 实际从 Java 后端获取）"""
    return {
        "resume_id": resume_id,
        "status": "not_found",
        "message": "本地缓存中未找到简历 - 请从 Java 后端获取"
    }


@router.post("/index")
async def index_resume(resume_id: str, resume_text: str, parsed_data: Optional[Dict[str, Any]] = None):
    """
    将简历索引到向量数据库用于 RAG 匹配
    """
    from src.services.rag_matcher import rag_matcher

    try:
        if parsed_data:
            await rag_matcher.index_resume_with_keyinfo(resume_id, parsed_data, resume_text)
        else:
            await rag_matcher.index_resume(resume_id, resume_text)

        return {"status": "indexed", "resume_id": resume_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"简历索引失败: {str(e)}")


@router.post("/jd/index")
async def index_job(job_id: str, jd_text: str, metadata: Optional[Dict[str, Any]] = None):
    """
    将岗位描述索引到向量数据库
    """
    from src.services.rag_matcher import rag_matcher

    try:
        await rag_matcher.index_job(job_id, jd_text, metadata)
        return {"status": "indexed", "job_id": job_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"岗位索引失败: {str(e)}")