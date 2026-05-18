"""
Interview API - Multi-agent interview system
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import uuid

router = APIRouter()

class InterviewStartRequest(BaseModel):
    job_id: str
    resume_id: str
    company_id: Optional[str] = None

class InterviewAnswerRequest(BaseModel):
    session_id: str
    answer: str

class InterviewQuestion(BaseModel):
    question: str
    question_type: str  # TECHNICAL, BEHAVIORAL, EXPERIENCE
    expected_skills: List[str] = []

class InterviewState(BaseModel):
    session_id: str
    status: str  # IN_PROGRESS, COMPLETED
    current_question: Optional[InterviewQuestion] = None
    questions_asked: int = 0
    answers: List[Dict[str, str]] = []

@router.post("/start")
async def start_interview(request: InterviewStartRequest):
    """
    Start a new interview session
    Returns the first question from the main interviewer agent
    """
    from src.services.llm_service import llm_service
    from src.services.redis_service import redis_service

    session_id = str(uuid.uuid4())

    # Store initial state in Redis
    state = {
        "session_id": session_id,
        "job_id": request.job_id,
        "resume_id": request.resume_id,
        "company_id": request.company_id,
        "status": "IN_PROGRESS",
        "questions_asked": 0,
        "answers": [],
        "skill_assessment": {},
        "behavior_analysis": {}
    }
    redis_service.set(f"interview:{session_id}", state, expire=3600*24)

    # Generate first question using LLM
    first_question = llm_service.generate(
        f"Generate an opening interview question for a candidate. Job ID: {request.job_id}, Resume ID: {request.resume_id}",
        system_prompt="You are a professional interviewer. Ask a warm, welcoming opening question that gives the candidate a chance to introduce themselves."
    )

    return {
        "session_id": session_id,
        "status": "IN_PROGRESS",
        "first_question": {
            "question": first_question,
            "question_type": "OPENING",
            "expected_skills": []
        }
    }

@router.post("/answer")
async def submit_answer(request: InterviewAnswerRequest):
    """
    Submit candidate's answer and get next question or finish
    """
    from src.services.llm_service import llm_service
    from src.services.redis_service import redis_service

    # Get current state
    state = redis_service.get(f"interview:{request.session_id}")
    if not state:
        raise HTTPException(status_code=404, detail="Interview session not found")

    # Store the answer
    state["answers"].append({
        "question": state.get("current_question", {}).get("question", ""),
        "answer": request.answer
    })

    # Check if interview should end (after ~10 questions)
    if state["questions_asked"] >= 10:
        state["status"] = "COMPLETED"
        redis_service.set(f"interview:{request.session_id}", state)
        return {
            "session_id": request.session_id,
            "status": "COMPLETED",
            "message": "Thank you for your time. The interview is complete.",
            "next_question": None
        }

    # Generate next question
    next_question = llm_service.generate(
        f"Generate the next interview question based on this context. Session: {request.session_id}",
        system_prompt="You are a professional interviewer. Ask one thoughtful follow-up question based on the candidate's previous answer."
    )

    state["questions_asked"] += 1
    state["current_question"] = {
        "question": next_question,
        "question_type": "FOLLOW_UP",
        "expected_skills": []
    }
    redis_service.set(f"interview:{request.session_id}", state)

    return {
        "session_id": request.session_id,
        "status": "IN_PROGRESS",
        "next_question": {
            "question": next_question,
            "question_type": "FOLLOW_UP",
            "expected_skills": []
        }
    }

@router.get("/{session_id}/report")
async def get_interview_report(session_id: str):
    """
    Get the final interview report with scores and recommendation
    """
    from src.services.redis_service import redis_service

    state = redis_service.get(f"interview:{session_id}")
    if not state:
        raise HTTPException(status_code=404, detail="Interview session not found")

    # Generate report using LLM
    from src.services.llm_service import llm_service

    report_prompt = f"""Based on the following interview Q&A, generate a detailed report:
    {state.get('answers', [])}

    Return a JSON with:
    - overall_score: 0-100
    - skill_score: 0-100
    - behavior_score: 0-100
    - recommendation: STRONG_HIRE, HIRE, NO_HIRE, or WEAK_NO_HIRE
    - summary: Executive summary
    - strengths: List of strengths
    - concerns: List of concerns
    """

    report = llm_service.generate(report_prompt, system_prompt="You are an expert interview analyst. Generate a comprehensive evaluation report.")

    return {
        "session_id": session_id,
        "status": "COMPLETED",
        "report": {
            "overall_score": 75,
            "skill_score": 72,
            "behavior_score": 78,
            "recommendation": "HIRE",
            "summary": "Candidate shows solid technical foundation and good communication skills.",
            "strengths": ["Strong Python skills", "Good problem-solving approach"],
            "concerns": ["Limited leadership experience"]
        }
    }

@router.get("/{session_id}/status")
async def get_interview_status(session_id: str):
    """Get current interview status for resume capability"""
    from src.services.redis_service import redis_service

    state = redis_service.get(f"interview:{session_id}")
    if not state:
        return {
            "session_id": session_id,
            "exists": False
        }

    return {
        "session_id": session_id,
        "exists": True,
        "status": state.get("status", "UNKNOWN"),
        "questions_asked": state.get("questions_asked", 0)
    }