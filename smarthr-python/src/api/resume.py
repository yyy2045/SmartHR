"""
Resume API - Resume parsing and matching endpoints
"""

from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import uuid

router = APIRouter(prefix="/api/resume", tags=["resume"])


class ResumeParseRequest(BaseModel):
    raw_text: str


class ResumeMatchRequest(BaseModel):
    resume_id: str
    job_id: str
    resume_text: str


class ParsedResume(BaseModel):
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
    Upload and parse a resume file (PDF or Word)
    Extract text and parse into structured data using LLM
    """
    from src.services.resume_parser import resume_parser

    # Validate file type
    allowed_types = ["application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {file.content_type}")

    # Read file content
    content = await file.read()

    # Generate resume ID
    resume_id = str(uuid.uuid4())

    try:
        # Parse the resume
        parsed = await resume_parser.parse_with_file_content(file.filename, content)

        return {
            "resume_id": resume_id,
            "status": "parsed",
            "data": parsed,
            "file_name": file.filename
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse resume: {str(e)}")


@router.post("/parse")
async def parse_resume(request: ResumeParseRequest):
    """
    Parse resume raw text into structured data using LLM
    """
    from src.services.resume_parser import resume_parser

    try:
        parsed = await resume_parser.parse_text(request.raw_text)
        return {
            "status": "parsed",
            "data": parsed
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse resume: {str(e)}")


@router.post("/match")
async def match_resume(request: ResumeMatchRequest):
    """
    Match resume against job description using RAG
    """
    from src.services.rag_matcher import rag_matcher

    try:
        result = await rag_matcher.match(
            job_id=request.job_id,
            resume_text=request.resume_text,
            resume_id=request.resume_id
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
        raise HTTPException(status_code=500, detail=f"Failed to match resume: {str(e)}")


@router.get("/{resume_id}")
async def get_resume(resume_id: str):
    """Get resume by ID (placeholder - actual implementation calls Java backend)"""
    return {
        "resume_id": resume_id,
        "status": "not_found",
        "message": "Resume not found in local cache - retrieve from Java backend"
    }


@router.post("/index")
async def index_resume(resume_id: str, resume_text: str, parsed_data: Optional[Dict[str, Any]] = None):
    """
    Index a resume into the vector store for RAG matching
    """
    from src.services.rag_matcher import rag_matcher

    try:
        if parsed_data:
            await rag_matcher.index_resume_with_keyinfo(resume_id, parsed_data, resume_text)
        else:
            await rag_matcher.index_resume(resume_id, resume_text)

        return {"status": "indexed", "resume_id": resume_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to index resume: {str(e)}")


@router.post("/jd/index")
async def index_job(job_id: str, jd_text: str, metadata: Optional[Dict[str, Any]] = None):
    """
    Index a job description into the vector store
    """
    from src.services.rag_matcher import rag_matcher

    try:
        await rag_matcher.index_job(job_id, jd_text, metadata)
        return {"status": "indexed", "job_id": job_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to index job: {str(e)}")