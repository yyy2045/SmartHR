"""
面试 API - 基于 LangGraph 的多智能体面试系统
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import uuid
import json

from src.agents.interview_graph import get_interview_graph
from src.services.interview_state_manager import interview_state_manager
from src.services.llm_service import llm_service
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
    result = []
    for item in evidence_items or []:
        if hasattr(item, "model_dump"):
            result.append(item.model_dump())
        elif isinstance(item, dict):
            result.append(item)
    return result


def _format_evidence_context(evidence: List[Dict[str, Any]], limit: int = 4) -> str:
    lines = []
    for idx, item in enumerate((evidence or [])[:limit], start=1):
        source = item.get("title") or item.get("sourceId") or item.get("sourceType") or "来源"
        text = item.get("highlight") or item.get("text") or ""
        if text:
            lines.append(f"[证据{idx}｜{source}] {text[:260]}")
    return "\n".join(lines)


async def _prepare_session_evidence(request: CreateSessionRequest) -> Dict[str, Any]:
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
        result["evidence"] = _evidence_to_dicts(search_response.evidence)
        result["traceId"] = search_response.traceId
        result["retrievalScores"] = search_response.retrievalScores
        result["rankScores"] = search_response.rankScores
    except Exception as e:
        print(f"[interview] prepare evidence failed: {e}")
    return result


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
        "report_data": None
    }

    # 保存初始状态到 Redis（容错：Redis 不可用不阻塞会话创建）
    try:
        await interview_state_manager.save_state(session_id, initial_state)
    except Exception as e:
        print(f"[interview] save initial state failed: {e}")

    # 创建首问：直接调用 LLM 生成（不跑完整 LangGraph 图，避免额外节点拖慢首响）
    # LLM 调用是同步的，在异步线程池中执行避免阻塞事件循环
    import asyncio
    first_question = None
    try:
        from src.services.llm_service import llm_service
        evidence_context = _format_evidence_context(session_evidence)
        prompt = (
            f"请用中文为以下岗位生成一个面试的开场问题，要求友好、开放式，邀请候选人自我介绍。\n"
            f"岗位描述：{(request.job_description or '通用岗位')[:500]}\n"
            f"可参考证据：\n{evidence_context}\n"
            f"只返回问题文本，不要任何其他内容。"
        )
        opening = await asyncio.wait_for(
            asyncio.to_thread(
                llm_service.generate,
                prompt,
                "你是一位专业的面试官。"
            ),
            timeout=60.0
        )
        first_question = {
            "question": (opening or "").strip() or "请先做一下自我介绍。",
            "question_type": "OPENING",
            "expected_skills": [],
            "competency": "自我介绍与求职动机",
            "basisEvidence": session_evidence,
            "traceId": evidence_bundle.get("traceId"),
        }
    except Exception as e:
        print(f"[interview] LLM opening generation failed: {e}")
        first_question = {
            "question": "你好，很高兴和你交流。请先做一下自我介绍，谈谈你的背景和求职动机。",
            "question_type": "OPENING",
            "expected_skills": [],
            "competency": "自我介绍与求职动机",
            "basisEvidence": session_evidence,
            "traceId": evidence_bundle.get("traceId"),
        }

    final_state = dict(initial_state)
    final_state["current_question"] = first_question
    try:
        await interview_state_manager.append_message(
            session_id,
            role="interviewer",
            content=first_question.get("question", ""),
            metadata={
                "question_type": first_question.get("question_type", "OPENING"),
                "competency": first_question.get("competency", ""),
                "basisEvidence": first_question.get("basisEvidence", []),
                "traceId": first_question.get("traceId"),
            }
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


@router.post("/sessions/{session_id}/message", response_model=QuestionResponse)
async def send_message(session_id: str, request: SendMessageRequest):
    """
    发送候选人消息并获取下一个问题或结束面试
    """
    import asyncio

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

    # 评估候选人的回答并更新技能/行为评分
    if questions_asked >= 0 and request.message:
        eval_type = "TECHNICAL" if questions_asked < 2 else ("BEHAVIORAL" if questions_asked < 4 else "EXPERIENCE")
        try:
            await evaluate_answer(state, request.message, eval_type)
        except Exception as e:
            print(f"[interview] evaluate_answer failed: {e}")
        # 评估后重新加载 state（evaluate_answer 内部已保存，但确保引用一致）
        state = await interview_state_manager.load_state(session_id) or state
        # 同步 Redis 中的实时分数（evaluate_answer 写入了独立 key）
        state["skill_scores"] = await interview_state_manager.get_skill_scores(session_id)
        state["behavior_scores"] = await interview_state_manager.get_behavior_scores(session_id)

    # 10 题封顶，直接结束面试
    if questions_asked >= 10:
        state["is_complete"] = True
        # 从 Redis 同步最新的技能/行为分数
        state["skill_scores"] = await interview_state_manager.get_skill_scores(session_id)
        state["behavior_scores"] = await interview_state_manager.get_behavior_scores(session_id)
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

    # 通过 LLM 直接生成下一个问题（跳过 LangGraph 以稳定首响并避开节点链路异常）
    next_question_text = None
    evidence_context = ""
    basis_evidence: List[Dict[str, Any]] = []
    evidence_trace_id = None
    rank_scores: List[Dict[str, Any]] = []
    qtype = "OPEN"
    try:
        from src.services.llm_service import llm_service
        if questions_asked < 2:
            topic = "技术能力（项目实战、技术栈细节）"
            qtype = "TECHNICAL"
        elif questions_asked < 4:
            topic = "问题解决与协作（行为面试题）"
            qtype = "BEHAVIORAL"
        else:
            topic = "过往成就与成长经历"
            qtype = "EXPERIENCE"

        try:
            extracted_info = state.get("extracted_info", {})
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
            basis_evidence = _evidence_to_dicts(search_response.evidence)
            evidence_trace_id = search_response.traceId
            rank_scores = search_response.rankScores
            evidence_context = _format_evidence_context(basis_evidence)
            extracted_info["last_question_evidence"] = basis_evidence
            extracted_info["last_question_trace_id"] = evidence_trace_id
            extracted_info["last_rank_scores"] = rank_scores
            state["extracted_info"] = extracted_info
        except Exception as e:
            print(f"[interview] evidence retrieval failed: {e}")

        # 最近3轮对话历史（窗口记忆）
        history_context = ""
        if history and len(history) >= 2:
            recent = history[-6:]  # 最近3轮 = 6条消息（Q,A,Q,A,Q,A）
            qa_pairs = []
            for i in range(0, len(recent), 2):
                if i + 1 < len(recent):
                    q = recent[i].get("content", "")[:200] if isinstance(recent[i], dict) else str(recent[i])
                    a = recent[i + 1].get("content", "")[:300] if isinstance(recent[i + 1], dict) else str(recent[i + 1])
                    qa_pairs.append(f"问：{q}\n答：{a}")
            if qa_pairs:
                history_context = "\n\n".join(qa_pairs[-3:])  # 最多3轮

        prompt = (
            f"你是面试官，请根据岗位描述和对话历史，提出一个新的{topic}相关的中文面试问题。\n\n"
            f"岗位描述：{(job_description or '通用岗位')[:400]}\n"
        )
        if evidence_context:
            prompt += f"可引用证据：\n{evidence_context}\n"
        if history_context:
            prompt += f"最近对话历史：\n{history_context}\n\n"
        prompt += (
            f"最新回答：{(request.message or '')[:600]}\n\n"
            f"只返回问题本身，不要任何前缀、说明或额外内容。"
        )
        next_question_text = await asyncio.wait_for(
            asyncio.to_thread(llm_service.generate, prompt, "你是一位资深面试官。"),
            timeout=60.0
        )
    except Exception as e:
        print(f"[interview] LLM next question failed: {e}")

    if not next_question_text or not next_question_text.strip():
        fallbacks = [
            "可以详细讲讲你最近一个有挑战的项目吗？你在其中具体负责什么？",
            "在团队协作中，你遇到过最棘手的冲突是什么？是怎么处理的？",
            "你曾经做过的最复杂的技术决策是什么？为什么这样选？",
            "请举一个你主动学习新技术或解决新问题的例子。",
            "你认为你最近 1 年内最大的成长是什么？",
        ]
        next_question_text = fallbacks[questions_asked % len(fallbacks)]

    next_question = {
        "question": next_question_text.strip(),
        "question_type": qtype if next_question_text else "OPEN",
        "expected_skills": [],
        "competency": {
            "TECHNICAL": "技术能力",
            "BEHAVIORAL": "协作与问题解决",
            "EXPERIENCE": "项目经验与成长",
        }.get(qtype, "综合能力"),
        "basisEvidence": basis_evidence,
        "traceId": evidence_trace_id,
        "rankScores": rank_scores,
    }

    state["current_question"] = next_question
    state["questions_asked"] = questions_asked + 1
    state["is_complete"] = False

    try:
        await interview_state_manager.append_message(
            session_id,
            role="interviewer",
            content=next_question.get("question", ""),
            metadata={
                "question_type": next_question.get("question_type", "OPEN"),
                "competency": next_question.get("competency", ""),
                "basisEvidence": next_question.get("basisEvidence", []),
                "traceId": next_question.get("traceId"),
            }
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

    # 标记为完成
    state["is_complete"] = True

    # 运行报告生成器
    from src.agents.report_generator import ReportGeneratorAgent
    agent = ReportGeneratorAgent()
    result = agent.process(state)

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


async def evaluate_answer(state: Dict, answer: str, eval_type: str):
    """
    根据候选人的回答评估技能/行为分数并存入 state
    eval_type: TECHNICAL | BEHAVIORAL | EXPERIENCE
    """
    import asyncio

    # 评分标准 rubric
    rubric = {
        "TECHNICAL": """技术能力评分标准（0-100）：
- 90-100：回答准确具体，能说出技术细节、工具名称、框架、代码逻辑，有实战经验佐证
- 70-89：回答基本正确，有一定技术深度，但缺乏具体细节或实战验证
- 50-69：回答模糊，技术概念不准确，或只停留在表面理解
- 30-49：回答错误明显，对技术原理理解不正确
- 0-29：完全不会或回避问题""",
        "BEHAVIORAL": """行为面试评分标准（0-100）：
- 90-100：STAR 完整（ Situation-Task-Action-Result ），故事具体、数据清晰、结果可量化
- 70-89：STAR 基本完整，但结果数据不具体或量化不明显
- 50-69：故事笼统，缺乏具体行动和可衡量结果
- 30-49：故事平淡或与问题不相关
- 0-29：编造故事或无法提供任何实际例子""",
        "EXPERIENCE": """经验与成长评分标准（0-100）：
- 90-100：成就突出，有具体数据（如性能提升 X%、用户增长 X），展现了主动性和成长性
- 70-89：有一定成就，但数据不够具体或影响力有限
- 50-69：经历平淡，没有突出贡献
- 30-49：无法清晰描述自己的贡献
- 0-29：没有有价值的工作经历"""
    }

    prompt = (
        f"你是一位面试评估专家。请严格根据评分标准评估候选人的回答。\n\n"
        f"评分标准：\n{rubric.get(eval_type, rubric['TECHNICAL'])}\n\n"
        f"问题类型：{eval_type}\n"
        f"候选人回答：{answer[:800]}\n\n"
        f"请返回严格 JSON（必须包含 score 和 category 两个字段）：\n"
        '{"score": 0-100整数, "category": "技术能力|沟通表达|问题解决|协作能力|学习成长"}'
    )

    try:
        result = await asyncio.wait_for(
            asyncio.to_thread(llm_service.generate, prompt, "你是一位专业的面试评估专家。"),
            timeout=30.0
        )
        parsed = _parse_eval_result(result)
        if parsed and "score" in parsed:
            category = parsed.get("category", "技术能力")
            score = int(parsed["score"])
            if eval_type == "TECHNICAL":
                existing_skills = await interview_state_manager.get_skill_scores(state["session_id"])
                await interview_state_manager.update_skill_scores(state["session_id"], {category: score})
                state["skill_scores"] = {**existing_skills, category: score}
            else:
                existing_behaviors = await interview_state_manager.get_behavior_scores(state["session_id"])
                await interview_state_manager.update_behavior_scores(state["session_id"], {category: score})
                state["behavior_scores"] = {**existing_behaviors, category: score}
            await interview_state_manager.save_state(state["session_id"], state)
    except Exception as e:
        print(f"[interview] evaluate_answer failed: {e}")


def _parse_eval_result(text: str) -> Dict:
    import json, re
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except Exception:
            pass
    return {}
