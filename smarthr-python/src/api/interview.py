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
    session_id: str
    status: str
    question: Optional[Dict[str, Any]] = None
    is_complete: bool = False
    message: Optional[str] = None
    skillScores: Optional[Dict[str, int]] = None
    behaviorScores: Optional[Dict[str, int]] = None


class ReportResponse(BaseModel):
    """报告响应"""
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
    创建新的面试会话并返回第一个问题
    """
    session_id = str(uuid.uuid4())

    # 初始化状态
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
        prompt = (
            f"请用中文为以下岗位生成一个面试的开场问题，要求友好、开放式，邀请候选人自我介绍。\n"
            f"岗位描述：{(request.job_description or '通用岗位')[:500]}\n"
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
            "expected_skills": []
        }
    except Exception as e:
        print(f"[interview] LLM opening generation failed: {e}")
        first_question = {
            "question": "你好，很高兴和你交流。请先做一下自我介绍，谈谈你的背景和求职动机。",
            "question_type": "OPENING",
            "expected_skills": []
        }

    final_state = dict(initial_state)
    final_state["current_question"] = first_question
    try:
        await interview_state_manager.save_state(session_id, final_state)
    except Exception as e:
        print(f"[interview] save final state failed: {e}")

    return QuestionResponse(
        session_id=session_id,
        status="IN_PROGRESS",
        question=first_question,
        is_complete=False
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
    发送候选人消息并获取下一个问题或结束面试
    """
    import asyncio

    # 加载当前状态
    state = await interview_state_manager.load_state(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="未找到面试会话")

    if state.get("is_complete"):
        return QuestionResponse(
            session_id=session_id,
            status="COMPLETED",
            message="面试已完成",
            is_complete=True
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
    if questions_asked >= 9:
        state["is_complete"] = True
        # 从 Redis 同步最新的技能/行为分数
        state["skill_scores"] = await interview_state_manager.get_skill_scores(session_id)
        state["behavior_scores"] = await interview_state_manager.get_behavior_scores(session_id)
        try:
            await interview_state_manager.save_state(session_id, state)
        except Exception as e:
            print(f"[interview] save state failed: {e}")
        return QuestionResponse(
            session_id=session_id,
            status="COMPLETED",
            message="面试已完成",
            is_complete=True,
            skillScores=state.get("skill_scores", {}),
            behaviorScores=state.get("behavior_scores", {})
        )

    # 通过 LLM 直接生成下一个问题（跳过 LangGraph 以稳定首响并避开节点链路异常）
    next_question_text = None
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

        prompt = (
            f"你是面试官，请根据上一轮的提问和候选人的回答，提出一个新的{topic}相关的中文面试问题。\n\n"
            f"岗位描述：{(job_description or '通用岗位')[:400]}\n"
            f"上一题：{previous_q_text[:300]}\n"
            f"候选人回答：{(request.message or '')[:600]}\n\n"
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
        "expected_skills": []
    }

    state["current_question"] = next_question
    state["questions_asked"] = questions_asked + 1
    state["is_complete"] = False

    try:
        await interview_state_manager.save_state(session_id, state)
    except Exception as e:
        print(f"[interview] save state failed: {e}")

    return QuestionResponse(
        session_id=session_id,
        status="IN_PROGRESS",
        question=next_question,
        is_complete=False,
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
        "session_id": session_id,
        "status": "COMPLETED",
        "report": {
            "overall_score": report_data.get("overall_score", 75),
            "skill_score": report_data.get("skill_score", 75),
            "behavior_score": report_data.get("behavior_score", 75),
            "skillScores": report_data.get("skillScores", {}),
            "behaviorScores": report_data.get("behaviorScores", {}),
            "recommendation": report_data.get("recommendation", "HIRE"),
            "summary": report_data.get("summary", ""),
            "strengths": report_data.get("strengths", []),
            "concerns": report_data.get("concerns", []),
            "interview_highlights": report_data.get("interview_highlights", []),
            "qaSummary": report_data.get("qaSummary", [])
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
        "session_id": session_id,
        "overall_score": report.get("overall_score", 0),
        "skill_score": report.get("skill_score", 0),
        "behavior_score": report.get("behavior_score", 0),
        "skillScores": skill_scores,
        "behaviorScores": behavior_scores,
        "recommendation": report.get("recommendation", "UNKNOWN"),
        "summary": report.get("summary", ""),
        "strengths": report.get("strengths", []),
        "concerns": report.get("concerns", []),
        "interview_highlights": report.get("interview_highlights", []),
        "qaSummary": report.get("qaSummary", [])
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
            "session_id": session_id,
            "status": "ALREADY_COMPLETED",
            "message": "此面试已完成"
        }

    # 获取最后一个问题以便继续
    current_question = state.get("current_question")
    questions_asked = state.get("questions_asked", 0)

    return {
        "session_id": session_id,
        "status": "READY_TO_RESUME",
        "current_question": current_question,
        "questions_asked": questions_asked,
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


async def evaluate_answer(state: Dict, answer: str, eval_type: str):
    """
    根据候选人的回答评估技能/行为分数并存入 state
    eval_type: TECHNICAL | BEHAVIORAL | EXPERIENCE
    """
    import asyncio

    prompt = (
        f"你是一位面试评估专家。请评估候选人在以下面试问题中的回答表现，并给出评分。\n\n"
        f"问题类型：{eval_type}\n"
        f"候选人回答：{answer[:800]}\n\n"
        f"请返回严格 JSON：\n"
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