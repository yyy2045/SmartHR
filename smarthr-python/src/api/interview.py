"""
面试 API - 基于 LangGraph 的多智能体面试系统
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import asyncio
import uuid

from src.agents.interview_graph import get_interview_graph
from src.services.interview_state_manager import interview_state_manager
from src.services.rag.evidence_service import rag_evidence_service

router = APIRouter(prefix="/api/interview", tags=["面试"])

# 请求/响应模型
class CreateSessionRequest(BaseModel):
    """创建面试会话请求"""
    job_id: str
    resume_id: str
    company_id: Optional[str] = None
    job_description: Optional[str] = None
    resume_text: Optional[str] = None

class SendMessageRequest(BaseModel):
    """发送消息请求"""
    message: str

class QuestionResponse(BaseModel):
    """问题响应"""
    sessionId: str
    status: str
    currentQuestion: Optional[Dict[str, Any]] = None
    isComplete: bool = False
    message: Optional[str] = None
    skillScores: Optional[Dict[str, int]] = None
    behaviorScores: Optional[Dict[str, int]] = None

class ReportResponse(BaseModel):
    """报告响应"""
    sessionId: str
    overallScore: float
    skillScore: float
    behaviorScore: float
    recommendation: str
    summary: str
    strengths: List[str]
    concerns: List[str]
    interviewHighlights: List[str]

def _evidence_to_dicts(evidence_items: List[Any]) -> List[Dict[str, Any]]:
    """将证据对象统一转为字典列表"""
    result = []
    for item in evidence_items or []:
        if hasattr(item, "model_dump"):
            result.append(item.model_dump())
        elif isinstance(item, dict):
            result.append(item)
    return result

def _filter_session_evidence(
    evidence: List[Dict[str, Any]],
    *,
    job_id: Optional[str] = None,
    resume_id: Optional[str] = None,
    session_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """过滤掉当前面试上下文之外的岗位/简历/面试记录证据"""
    filtered = []
    current_job_id = str(job_id) if job_id is not None else None
    current_resume_id = str(resume_id) if resume_id is not None else None
    current_session_id = str(session_id) if session_id is not None else None

    for item in evidence or []:
        source_type = str(item.get("sourceType") or item.get("source_type") or "")
        source_id = str(item.get("sourceId") or item.get("source_id") or "")
        metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}

        if source_type == "job":
            if current_job_id and source_id == current_job_id:
                filtered.append(item)
            continue
        if source_type == "resume":
            if current_resume_id and source_id == current_resume_id:
                filtered.append(item)
            continue
        if source_type == "interview":
            evidence_session_id = str(metadata.get("session_id") or "")
            if current_session_id and (
                evidence_session_id == current_session_id or source_id.startswith(f"{current_session_id}:")
            ):
                filtered.append(item)
            continue

        filtered.append(item)
    return filtered

async def _prepare_session_evidence(request: CreateSessionRequest) -> Dict[str, Any]:
    """会话创建前准备 RAG 索引与匹配证据"""
    company_id = request.company_id or "default"
    job_text = request.job_description or ""
    resume_text = request.resume_text or ""
    result = {
        "indexed": {"job": [], "resume": []},
        "evidence": [],
        "traceId": None,
        "retrievalScores": {},
        "rankScores": [],
    }
    try:
        result["indexed"] = await rag_evidence_service.ensure_job_resume_index(
            job_id=request.job_id,
            resume_id=request.resume_id,
            job_text=job_text,
            resume_text=resume_text,
            company_id=company_id,
        )
        search_response = await rag_evidence_service.search_evidence(
            query=rag_evidence_service.build_match_query(
                job_text=job_text,
                resume_text=resume_text,
            ),
            company_id=company_id,
            source_types=["job", "resume", "knowledge"],
            top_k=6,
        )
        result["evidence"] = _filter_session_evidence(
            _evidence_to_dicts(search_response.evidence),
            job_id=request.job_id,
            resume_id=request.resume_id,
        )
        result["traceId"] = search_response.traceId
        result["retrievalScores"] = search_response.retrievalScores
        result["rankScores"] = search_response.rankScores
    except Exception as e:
        print(f"[interview] prepare evidence failed: {e}")
    return result


async def _run_interview_graph(state: Dict[str, Any]) -> Dict[str, Any]:
    """在线程池中执行同步 LangGraph，避免阻塞 FastAPI 事件循环"""
    graph = get_interview_graph()
    session_id = str(state.get("session_id") or "default")
    config = {
        "configurable": {"thread_id": session_id},
        "recursion_limit": 8,
    }
    return await asyncio.wait_for(
        asyncio.to_thread(lambda: graph.invoke(state, config=config)),
        timeout=180.0,
    )


def _question_metadata(question: Dict[str, Any]) -> Dict[str, Any]:
    """抽取面试问题需要写入历史记录的元数据"""
    return {
        "question_type": question.get("question_type", "OPEN"),
        "competency": question.get("competency", ""),
        "basisEvidence": question.get("basisEvidence", []),
        "traceId": question.get("traceId"),
    }


async def _persist_graph_scores(session_id: str, state: Dict[str, Any]) -> Dict[str, Any]:
    """将图节点产生的评分同步到 Redis 独立评分 key"""
    skill_scores = state.get("skill_scores", {}) or {}
    behavior_scores = state.get("behavior_scores", {}) or {}
    if skill_scores:
        await interview_state_manager.update_skill_scores(session_id, skill_scores)
    if behavior_scores:
        await interview_state_manager.update_behavior_scores(session_id, behavior_scores)
    state["skill_scores"] = await interview_state_manager.get_skill_scores(session_id)
    state["behavior_scores"] = await interview_state_manager.get_behavior_scores(session_id)
    return state

# 创建新的面试会话并返回第一个问题?
@router.post("/sessions", response_model=QuestionResponse)
async def create_session(request: CreateSessionRequest):
    """
    创建新的面试会话并返回第一个问题
    """
    session_id = str(uuid.uuid4())
    evidence_bundle = await _prepare_session_evidence(request)
    session_evidence = evidence_bundle.get("evidence", [])

    # 初始化状态
    initial_state = {
        "session_id": session_id,
        "job_id": request.job_id,
        "resume_id": request.resume_id,
        "company_id": request.company_id,
        "status": "IN_PROGRESS",
        "current_agent": "MAIN",
        "messages": [],
        "skill_scores": {},
        "behavior_scores": {},
        "extracted_info": {
            "job_description": request.job_description or "",
            "resume_text": request.resume_text or "",
            "match_evidence": session_evidence,
            "match_trace_id": evidence_bundle.get("traceId"),
            "retrieval_scores": evidence_bundle.get("retrievalScores", {}),
            "rank_scores": evidence_bundle.get("rankScores", {}),
        },
        "current_question": None,
        "questions_asked": 0,
        "is_complete": False,
        "report_data": None,
        "graph_action": "create"
    }

    # 保存初始状态到 Redis（容错：Redis 不可用不阻塞会话创建）
    try:
        await interview_state_manager.save_state(session_id, initial_state)
    except Exception as e:
        print(f"[interview] save initial state failed: {e}")

    try:
        final_state = await _run_interview_graph(initial_state)
    except Exception as e:
        print(f"[interview] LangGraph opening generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"LangGraph 首问生成失败: {str(e)}")

    first_question = final_state.get("current_question") or {}
    if not first_question.get("question"):
        raise HTTPException(status_code=500, detail="LangGraph 未返回首问")

    try:
        await interview_state_manager.append_message(
            session_id,
            role="interviewer",
            content=first_question.get("question", ""),
            metadata=_question_metadata(first_question)
        )
        final_state["messages"] = await interview_state_manager.get_history(session_id)
        await interview_state_manager.save_state(session_id, final_state)
    except Exception as e:
        print(f"[interview] save final state failed: {e}")

    return QuestionResponse(
        sessionId=session_id,
        status="IN_PROGRESS",
        currentQuestion=first_question,
        isComplete=False
    )

# 获取当前面试会话状态和历史记录?
@router.get("/sessions/{session_id}", response_model=Dict[str, Any])
async def get_session(session_id: str):
    """
    获取当前面试会话状态和历史记录
    """
    state = await interview_state_manager.load_state(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="未找到面试会话")

    history = await interview_state_manager.get_history(session_id)

    return {
        "sessionId": session_id,
        "status": state.get("status", "UNKNOWN"),
        "currentAgent": state.get("current_agent", "MAIN"),
        "questionsAsked": state.get("questions_asked", 0),
        "isComplete": state.get("is_complete", False),
        "currentQuestion": state.get("current_question"),
        "history": history,
        "skillScores": state.get("skill_scores", {}),
        "behaviorScores": state.get("behavior_scores", {})
    }

# 发送候选人消息并获取下一个问题或结束面试?
@router.post("/sessions/{session_id}/message", response_model=QuestionResponse)
async def send_message(session_id: str, request: SendMessageRequest):
    """
    发送候选人消息并获取下一个问题或结束面试
    """
    # 加载当前状态
    state = await interview_state_manager.load_state(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="未找到面试会话")

    if state.get("is_complete"):
        return QuestionResponse(
            sessionId=session_id,
            status="COMPLETED",
            message="面试已完成",
            isComplete=True
        )

    # 将候选人消息追加到历史（容错）
    try:
        await interview_state_manager.append_message(
            session_id,
            role="candidate",
            content=request.message
        )
    except Exception as e:
        print(f"[interview] append_message failed: {e}")

    # 同步消息到 state（供报告生成使用）
    try:
        history = await interview_state_manager.get_history(session_id)
        state["messages"] = history
    except Exception as e:
        print(f"[interview] get_history failed: {e}")

    questions_asked = int(state.get("questions_asked", 0) or 0)
    job_description = state.get("extracted_info", {}).get("job_description", "")
    previous_q = state.get("current_question") or {}
    previous_q_text = previous_q.get("question", "") if isinstance(previous_q, dict) else str(previous_q)
    company_id = state.get("company_id") or "default"

    try:
        await rag_evidence_service.index_interview_turn(
            session_id=session_id,
            turn_id=str(questions_asked + 1),
            question=previous_q_text,
            answer=request.message,
            company_id=str(company_id),
            metadata={
                "question_type": previous_q.get("question_type", "") if isinstance(previous_q, dict) else "",
                "competency": previous_q.get("competency", "") if isinstance(previous_q, dict) else "",
                "traceId": previous_q.get("traceId") if isinstance(previous_q, dict) else None,
            },
        )
    except Exception as e:
        print(f"[interview] index interview turn failed: {e}")

    basis_evidence: List[Dict[str, Any]] = []
    evidence_trace_id = None
    rank_scores: List[Dict[str, Any]] = []
    try:
        if questions_asked < 2:
            topic = "技术能力（项目实战、技术栈细节）"
        elif questions_asked < 4:
            topic = "问题解决与协作（行为面试题）"
        else:
            topic = "过往成就与成长经历"

        extracted_info = state.get("extracted_info", {}) or {}
        search_response = await rag_evidence_service.search_evidence(
            query=(
                f"{topic}\n岗位：{job_description[:600]}\n"
                f"上一题：{previous_q_text[:300]}\n"
                f"候选人回答：{(request.message or '')[:600]}"
            ),
            company_id=str(company_id),
            source_types=["job", "resume", "knowledge", "interview"],
            top_k=6,
        )
        basis_evidence = _filter_session_evidence(
            _evidence_to_dicts(search_response.evidence),
            job_id=state.get("job_id"),
            resume_id=state.get("resume_id"),
            session_id=session_id,
        )
        evidence_trace_id = search_response.traceId
        rank_scores = search_response.rankScores
        extracted_info["last_question_evidence"] = basis_evidence
        extracted_info["last_question_trace_id"] = evidence_trace_id
        extracted_info["last_rank_scores"] = rank_scores
        state["extracted_info"] = extracted_info
    except Exception as e:
        print(f"[interview] evidence retrieval failed: {e}")

    state["graph_action"] = "message"
    state["candidate_message"] = request.message
    state["previous_question_text"] = previous_q_text
    state["skill_scores"] = await interview_state_manager.get_skill_scores(session_id)
    state["behavior_scores"] = await interview_state_manager.get_behavior_scores(session_id)

    try:
        state = await _run_interview_graph(state)
        state = await _persist_graph_scores(session_id, state)
    except Exception as e:
        print(f"[interview] LangGraph message turn failed: {e}")
        raise HTTPException(status_code=500, detail=f"LangGraph 面试轮次执行失败: {str(e)}")

    if state.get("is_complete"):
        try:
            await interview_state_manager.save_state(session_id, state)
        except Exception as e:
            print(f"[interview] save state failed: {e}")
        return QuestionResponse(
            sessionId=session_id,
            status="COMPLETED",
            message="面试已完成",
            isComplete=True,
            skillScores=state.get("skill_scores", {}),
            behaviorScores=state.get("behavior_scores", {})
        )

    next_question = state.get("current_question") or {}
    if not next_question.get("question"):
        raise HTTPException(status_code=500, detail="LangGraph 未返回下一题")

    try:
        await interview_state_manager.append_message(
            session_id,
            role="interviewer",
            content=next_question.get("question", ""),
            metadata=_question_metadata(next_question)
        )
        state["messages"] = await interview_state_manager.get_history(session_id)
        await interview_state_manager.save_state(session_id, state)
    except Exception as e:
        print(f"[interview] save state failed: {e}")

    return QuestionResponse(
        sessionId=session_id,
        status="IN_PROGRESS",
        currentQuestion=next_question,
        isComplete=False,
        skillScores=state.get("skill_scores", {}),
        behaviorScores=state.get("behavior_scores", {})
    )

# 结束面试并生成最终报告?
@router.post("/sessions/{session_id}/end")
async def end_session(session_id: str):
    """
    结束面试并生成最终报告
    """
    state = await interview_state_manager.load_state(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="未找到面试会话")

    # 确保消息历史是最新的
    try:
        history = await interview_state_manager.get_history(session_id)
        state["messages"] = history
        state["skill_scores"] = await interview_state_manager.get_skill_scores(session_id)
        state["behavior_scores"] = await interview_state_manager.get_behavior_scores(session_id)
    except Exception as e:
        print(f"[interview] sync state before report failed: {e}")

    state["graph_action"] = "end"
    state["is_complete"] = True

    try:
        result = await _run_interview_graph(state)
    except Exception as e:
        print(f"[interview] LangGraph report generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"LangGraph 报告生成失败: {str(e)}")

    # 保存最终状态和报告
    await interview_state_manager.save_state(session_id, result)
    await interview_state_manager.save_report(session_id, result.get("report_data", {}))

    report_data = result.get("report_data", {})

    return {
        "sessionId": session_id,
        "status": "COMPLETED",
        "report": {
            "overallScore": report_data.get("overall_score", 75),
            "skillScore": report_data.get("skill_score", 75),
            "behaviorScore": report_data.get("behavior_score", 75),
            "skillScores": report_data.get("skillScores", {}),
            "behaviorScores": report_data.get("behaviorScores", {}),
            "recommendation": report_data.get("recommendation", "HIRE"),
            "summary": report_data.get("summary", ""),
            "strengths": report_data.get("strengths", []),
            "concerns": report_data.get("concerns", []),
            "interviewHighlights": report_data.get("interview_highlights", []),
            "qaSummary": report_data.get("qaSummary", []),
            "risks": report_data.get("risks", []),
            "evidence": report_data.get("evidence", []),
            "conclusionEvidence": report_data.get("conclusionEvidence", []),
            "followUpBasis": report_data.get("followUpBasis", [])
        }
    }

# 获取面试会话的报告?
@router.get("/sessions/{session_id}/report", response_model=Dict[str, Any])
async def get_report(session_id: str):
    """
    获取面试会话的报告
    """
    # 尝试从 Redis 获取
    report = await interview_state_manager.get_report(session_id)
    if not report:
        # 尝试从保存的状态获取
        state = await interview_state_manager.load_state(session_id)
        if state:
            report = state.get("report_data", {})

    if not report:
        raise HTTPException(status_code=404, detail="未找到面试报告")

    # 同时返回各维度评分（直接从 Redis 独立 key 读取，不依赖 state）
    skill_scores = await interview_state_manager.get_skill_scores(session_id)
    behavior_scores = await interview_state_manager.get_behavior_scores(session_id)

    return {
        "sessionId": session_id,
        "overallScore": report.get("overall_score", 0),
        "skillScore": report.get("skill_score", 0),
        "behaviorScore": report.get("behavior_score", 0),
        "skillScores": skill_scores,
        "behaviorScores": behavior_scores,
        "recommendation": report.get("recommendation", "UNKNOWN"),
        "summary": report.get("summary", ""),
        "strengths": report.get("strengths", []),
        "concerns": report.get("concerns", []),
        "interviewHighlights": report.get("interview_highlights", []),
        "qaSummary": report.get("qaSummary", []),
        "risks": report.get("risks", []),
        "evidence": report.get("evidence", []),
        "conclusionEvidence": report.get("conclusionEvidence", []),
        "followUpBasis": report.get("followUpBasis", [])
    }

# 恢复中断的面试会话?
@router.post("/sessions/{session_id}/resume")
async def resume_session(session_id: str):
    """
    恢复中断的面试会话
    """
    state = await interview_state_manager.load_state(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="未找到面试会话")

    if state.get("is_complete"):
        return {
            "sessionId": session_id,
            "status": "ALREADY_COMPLETED",
            "message": "此面试已完成"
        }

    # 获取最后一个问题以便继续
    current_question = state.get("current_question")
    questions_asked = state.get("questions_asked", 0)

    return {
        "sessionId": session_id,
        "status": "READY_TO_RESUME",
        "currentQuestion": current_question,
        "questionsAsked": questions_asked,
        "message": "会话已恢复，请从上次中断处继续"
    }

# 获取面试会话状态，用于恢复功能?
@router.get("/sessions/{session_id}/status")
async def get_session_status(session_id: str):
    """
    获取面试会话状态，用于恢复功能
    """
    state = await interview_state_manager.load_state(session_id)
    if not state:
        return {
            "sessionId": session_id,
            "exists": False
        }

    return {
        "sessionId": session_id,
        "exists": True,
        "status": state.get("status", "UNKNOWN"),
        "isComplete": state.get("is_complete", False),
        "questionsAsked": state.get("questions_asked", 0),
        "currentAgent": state.get("current_agent", "MAIN")
    }

