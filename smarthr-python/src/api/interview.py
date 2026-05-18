"""
Interview API - Multi-agent interview system with LangGraph
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import uuid
import json

from src.agents.interview_graph import get_interview_graph
from src.services.interview_state_manager import interview_state_manager

router = APIRouter(prefix="/interview", tags=["interview"])


# Request/Response Models
class CreateSessionRequest(BaseModel):
    job_id: str
    resume_id: str
    company_id: Optional[str] = None
    job_description: Optional[str] = None
    resume_text: Optional[str] = None


class SendMessageRequest(BaseModel):
    message: str


class QuestionResponse(BaseModel):
    session_id: str
    status: str
    question: Optional[Dict[str, Any]] = None
    is_complete: bool = False
    message: Optional[str] = None


class ReportResponse(BaseModel):
    session_id: str
    overall_score: float
    skill_score: float
    behavior_score: float
    recommendation: str
    summary: str
    strengths: List[str]
    concerns: List[str]
    interview_highlights: List[str]


@router.post("/sessions", response_model=QuestionResponse)
async def create_session(request: CreateSessionRequest):
    """
    Create a new interview session and return the first question.
    """
    session_id = str(uuid.uuid4())

    # Initialize state
    initial_state = {
        "session_id": session_id,
        "job_id": request.job_id,
        "resume_id": request.resume_id,
        "company_id": request.company_id,
        "current_agent": "MAIN",
        "messages": [],
        "skill_scores": {},
        "behavior_scores": {},
        "extracted_info": {
            "job_description": request.job_description or "",
            "resume_text": request.resume_text or ""
        },
        "current_question": None,
        "questions_asked": 0,
        "is_complete": False,
        "report_data": None
    }

    # Save initial state to Redis
    await interview_state_manager.save_state(session_id, initial_state)

    # Get the compiled graph
    graph = get_interview_graph()

    # Create config for checkpointer
    config = {"configurable": {"thread_id": session_id}}

    # Run the graph with initial state
    result = graph.invoke(initial_state, config)

    # Extract first question
    first_question = result.get("current_question", {})
    if not first_question:
        # Generate opening question via LLM if graph didn't
        from src.services.llm_service import llm_service
        opening = llm_service.generate(
            f"Generate an opening interview question. Job: {request.job_id}",
            system_prompt="You are a professional interviewer. Ask a warm opening question."
        )
        first_question = {
            "question": opening,
            "question_type": "OPENING",
            "expected_skills": []
        }

    # Save updated state
    await interview_state_manager.save_state(session_id, result)

    return QuestionResponse(
        session_id=session_id,
        status="IN_PROGRESS",
        question=first_question,
        is_complete=False
    )


@router.get("/sessions/{session_id}", response_model=Dict[str, Any])
async def get_session(session_id: str):
    """
    Get current interview session state and history.
    """
    state = await interview_state_manager.load_state(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Interview session not found")

    history = await interview_state_manager.get_history(session_id)

    return {
        "session_id": session_id,
        "status": state.get("status", "UNKNOWN"),
        "current_agent": state.get("current_agent", "MAIN"),
        "questions_asked": state.get("questions_asked", 0),
        "is_complete": state.get("is_complete", False),
        "current_question": state.get("current_question"),
        "history": history,
        "skill_scores": state.get("skill_scores", {}),
        "behavior_scores": state.get("behavior_scores", {})
    }


@router.post("/sessions/{session_id}/message", response_model=QuestionResponse)
async def send_message(session_id: str, request: SendMessageRequest):
    """
    Send a candidate message and get the next question or completion.
    """
    # Load current state
    state = await interview_state_manager.load_state(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Interview session not found")

    if state.get("is_complete"):
        return QuestionResponse(
            session_id=session_id,
            status="COMPLETED",
            message="Interview has already been completed",
            is_complete=True
        )

    # Append the candidate's message
    await interview_state_manager.append_message(
        session_id,
        role="candidate",
        content=request.message
    )

    # Update messages in state
    history = await interview_state_manager.get_history(session_id)
    state["messages"] = history

    # Run the graph
    graph = get_interview_graph()
    config = {"configurable": {"thread_id": session_id}}
    result = graph.invoke(state, config)

    # Save updated state
    await interview_state_manager.save_state(session_id, result)

    # Get the next question
    current_question = result.get("current_question")
    is_complete = result.get("is_complete", False)

    # If interview is complete, generate report
    if is_complete and not result.get("report_data"):
        from src.agents.report_generator import ReportGeneratorAgent
        agent = ReportGeneratorAgent()
        result = agent.process(result)
        await interview_state_manager.save_state(session_id, result)

    return QuestionResponse(
        session_id=session_id,
        status="COMPLETED" if is_complete else "IN_PROGRESS",
        question=current_question,
        is_complete=is_complete
    )


@router.post("/sessions/{session_id}/end")
async def end_session(session_id: str):
    """
    End the interview and generate final report.
    """
    state = await interview_state_manager.load_state(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Interview session not found")

    # Mark as complete
    state["is_complete"] = True

    # Run report generator
    from src.agents.report_generator import ReportGeneratorAgent
    agent = ReportGeneratorAgent()
    result = agent.process(state)

    # Save final state and report
    await interview_state_manager.save_state(session_id, result)
    await interview_state_manager.save_report(session_id, result.get("report_data", {}))

    report_data = result.get("report_data", {})

    return {
        "session_id": session_id,
        "status": "COMPLETED",
        "report": {
            "overall_score": report_data.get("overall_score", 75),
            "skill_score": report_data.get("skill_score", 75),
            "behavior_score": report_data.get("behavior_score", 75),
            "recommendation": report_data.get("recommendation", "HIRE"),
            "summary": report_data.get("summary", ""),
            "strengths": report_data.get("strengths", []),
            "concerns": report_data.get("concerns", []),
            "interview_highlights": report_data.get("interview_highlights", [])
        }
    }


@router.get("/sessions/{session_id}/report", response_model=Dict[str, Any])
async def get_report(session_id: str):
    """
    Get the interview report for a session.
    """
    # Try to get from Redis first
    report = await interview_state_manager.get_report(session_id)
    if not report:
        # Try to get from saved state
        state = await interview_state_manager.load_state(session_id)
        if state:
            report = state.get("report_data", {})

    if not report:
        raise HTTPException(status_code=404, detail="Interview report not found")

    return {
        "session_id": session_id,
        "overall_score": report.get("overall_score", 0),
        "skill_score": report.get("skill_score", 0),
        "behavior_score": report.get("behavior_score", 0),
        "recommendation": report.get("recommendation", "UNKNOWN"),
        "summary": report.get("summary", ""),
        "strengths": report.get("strengths", []),
        "concerns": report.get("concerns", []),
        "interview_highlights": report.get("interview_highlights", [])
    }


@router.post("/sessions/{session_id}/resume")
async def resume_session(session_id: str):
    """
    Resume an interrupted interview session.
    """
    state = await interview_state_manager.load_state(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Interview session not found")

    if state.get("is_complete"):
        return {
            "session_id": session_id,
            "status": "ALREADY_COMPLETED",
            "message": "This interview has already been completed"
        }

    # Get the last question to continue from
    current_question = state.get("current_question")
    questions_asked = state.get("questions_asked", 0)

    return {
        "session_id": session_id,
        "status": "READY_TO_RESUME",
        "current_question": current_question,
        "questions_asked": questions_asked,
        "message": "Session restored. Continue from where you left off."
    }


@router.get("/sessions/{session_id}/status")
async def get_session_status(session_id: str):
    """
    Get interview session status for resume capability.
    """
    state = await interview_state_manager.load_state(session_id)
    if not state:
        return {
            "session_id": session_id,
            "exists": False
        }

    return {
        "session_id": session_id,
        "exists": True,
        "status": state.get("status", "UNKNOWN"),
        "is_complete": state.get("is_complete", False),
        "questions_asked": state.get("questions_asked", 0),
        "current_agent": state.get("current_agent", "MAIN")
    }