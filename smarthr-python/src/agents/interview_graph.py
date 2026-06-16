"""
面试状态机 - 基于 LangGraph 的多智能体面试编排
"""

import json
import re
from typing import Any, Dict, List, Optional, TypedDict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from src.services.llm_service import llm_service


class InterviewState(TypedDict, total=False):
    """面试对话共享状态"""

    session_id: str
    job_id: str
    resume_id: str
    company_id: Optional[str]
    status: str
    current_agent: str
    messages: List[Dict[str, Any]]
    skill_scores: Dict[str, float]
    behavior_scores: Dict[str, float]
    extracted_info: Dict[str, Any]
    current_question: Optional[Dict[str, Any]]
    questions_asked: int
    is_complete: bool
    report_data: Optional[Dict[str, Any]]
    graph_action: str
    candidate_message: str
    previous_question_text: str
    turn_eval_type: str


def create_interview_graph():
    """创建并编译面试状态机"""
    workflow = StateGraph(InterviewState)

    workflow.add_node("route", _route_node)
    workflow.add_node("main_interviewer", _main_interviewer_node)
    workflow.add_node("skill_evaluator", _skill_evaluator_node)
    workflow.add_node("behavior_analyzer", _behavior_analyzer_node)
    workflow.add_node("report_generator", _report_generator_node)

    workflow.set_entry_point("route")

    workflow.add_conditional_edges(
        "route",
        _route_next_node,
        {
            "main_interviewer": "main_interviewer",
            "skill_evaluator": "skill_evaluator",
            "behavior_analyzer": "behavior_analyzer",
            "report_generator": "report_generator",
        },
    )
    workflow.add_edge("skill_evaluator", "main_interviewer")
    workflow.add_edge("behavior_analyzer", "main_interviewer")
    workflow.add_edge("main_interviewer", END)
    workflow.add_edge("report_generator", END)

    checkpointer = MemorySaver()
    return workflow.compile(checkpointer=checkpointer)


def _route_node(state: InterviewState) -> InterviewState:
    """为本次 API 请求计算图路由所需的阶段信息"""
    action = (state.get("graph_action") or "message").lower()
    state["graph_action"] = action
    state["turn_eval_type"] = _eval_type_for_questions(state.get("questions_asked", 0))
    return state


def _route_next_node(state: InterviewState) -> str:
    """根据本次请求阶段选择下一个智能体节点"""
    action = (state.get("graph_action") or "message").lower()
    if action == "create":
        return "main_interviewer"
    if action == "end":
        return "report_generator"
    if state.get("turn_eval_type") == "TECHNICAL":
        return "skill_evaluator"
    return "behavior_analyzer"


def _main_interviewer_node(state: InterviewState) -> InterviewState:
    """主面试官节点：生成首问或下一轮问题"""
    action = (state.get("graph_action") or "message").lower()
    state["current_agent"] = "MAIN"
    state["status"] = "IN_PROGRESS"

    if action == "create":
        return _generate_opening_question(state)

    if int(state.get("questions_asked", 0) or 0) >= 10:
        state["is_complete"] = True
        state["status"] = "COMPLETED"
        return state

    return _generate_next_question(state)


def _skill_evaluator_node(state: InterviewState) -> InterviewState:
    """技能评估节点：根据候选人最新回答更新技术评分"""
    _evaluate_answer_into_state(state, "TECHNICAL")
    state["current_agent"] = "SKILL"
    return state


def _behavior_analyzer_node(state: InterviewState) -> InterviewState:
    """行为分析节点：根据候选人最新回答更新行为/经验评分"""
    eval_type = state.get("turn_eval_type") or "BEHAVIORAL"
    _evaluate_answer_into_state(state, eval_type if eval_type != "TECHNICAL" else "BEHAVIORAL")
    state["current_agent"] = "BEHAVIOR"
    return state


def _report_generator_node(state: InterviewState) -> InterviewState:
    """报告生成节点：交叉验证并生成最终报告"""
    from src.agents.report_generator import ReportGeneratorAgent

    agent = ReportGeneratorAgent()
    result = agent.process(state)
    result["status"] = "COMPLETED"
    result["graph_action"] = "end"
    return result


def _generate_opening_question(state: InterviewState) -> InterviewState:
    extracted_info = state.get("extracted_info", {}) or {}
    evidence = _evidence_to_dicts(extracted_info.get("match_evidence", []))
    evidence_context = _format_evidence_context(evidence)
    job_description = extracted_info.get("job_description") or "通用岗位"

    prompt = (
        "请用中文为以下岗位生成一个面试的开场问题，要求友好、开放式，邀请候选人自我介绍。\n"
        f"岗位描述：{job_description[:500]}\n"
        f"可参考证据：\n{evidence_context}\n"
        "只返回问题文本，不要任何其他内容。"
    )
    try:
        opening = llm_service.generate(prompt, "你是一位专业的面试官。")
    except Exception as exc:
        print(f"[interview_graph] opening generation failed: {exc}")
        opening = ""

    state["current_question"] = {
        "question": (opening or "").strip() or "你好，很高兴和你交流。请先做一下自我介绍，谈谈你的背景和求职动机。",
        "question_type": "OPENING",
        "expected_skills": [],
        "competency": "自我介绍与求职动机",
        "basisEvidence": evidence,
        "traceId": extracted_info.get("match_trace_id"),
    }
    state["is_complete"] = False
    return state


def _generate_next_question(state: InterviewState) -> InterviewState:
    questions_asked = int(state.get("questions_asked", 0) or 0)
    extracted_info = state.get("extracted_info", {}) or {}
    job_description = extracted_info.get("job_description") or "通用岗位"
    basis_evidence = _evidence_to_dicts(extracted_info.get("last_question_evidence", []))
    evidence_context = _format_evidence_context(basis_evidence)
    evidence_trace_id = extracted_info.get("last_question_trace_id")
    rank_scores = extracted_info.get("last_rank_scores", [])
    candidate_message = state.get("candidate_message") or ""
    previous_q_text = state.get("previous_question_text") or ""

    qtype, topic = _question_type_and_topic(questions_asked)
    history_context = _format_recent_history(state.get("messages", []))

    prompt = (
        f"你是面试官，请根据岗位描述和对话历史，提出一个新的{topic}相关的中文面试问题。\n\n"
        f"岗位描述：{job_description[:400]}\n"
    )
    if evidence_context:
        prompt += f"可引用证据：\n{evidence_context}\n"
    if history_context:
        prompt += f"最近对话历史：\n{history_context}\n\n"
    if previous_q_text:
        prompt += f"上一题：{previous_q_text[:300]}\n"
    prompt += (
        f"最新回答：{candidate_message[:600]}\n\n"
        "只返回问题本身，不要任何前缀、说明或额外内容。"
    )

    try:
        question_text = llm_service.generate(prompt, "你是一位资深面试官。")
    except Exception as exc:
        print(f"[interview_graph] next question generation failed: {exc}")
        question_text = ""

    if not question_text or not question_text.strip():
        fallbacks = [
            "可以详细讲讲你最近一个有挑战的项目吗？你在其中具体负责什么？",
            "在团队协作中，你遇到过最棘手的冲突是什么？是怎么处理的？",
            "你曾经做过的最复杂的技术决策是什么？为什么这样选？",
            "请举一个你主动学习新技术或解决新问题的例子。",
            "你认为你最近 1 年内最大的成长是什么？",
        ]
        question_text = fallbacks[questions_asked % len(fallbacks)]

    state["current_question"] = {
        "question": question_text.strip(),
        "question_type": qtype,
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
    state["questions_asked"] = questions_asked + 1
    state["is_complete"] = False
    return state


def _evaluate_answer_into_state(state: InterviewState, eval_type: str) -> None:
    answer = state.get("candidate_message") or ""
    if not answer:
        return

    rubric = {
        "TECHNICAL": """技术能力评分标准（0-100）：
- 90-100：回答准确具体，能说出技术细节、工具名称、框架、代码逻辑，有实战经验佐证
- 70-89：回答基本正确，有一定技术深度，但缺乏具体细节或实战验证
- 50-69：回答模糊，技术概念不准确，或只停留在表面理解
- 30-49：回答错误明显，对技术原理理解不正确
- 0-29：完全不会或回避问题""",
        "BEHAVIORAL": """行为面试评分标准（0-100）：
- 90-100：STAR 完整（Situation-Task-Action-Result），故事具体、数据清晰、结果可量化
- 70-89：STAR 基本完整，但结果数据不具体或量化不明显
- 50-69：故事笼统，缺乏具体行动和可衡量结果
- 30-49：故事平淡或与问题不相关
- 0-29：编造故事或无法提供任何实际例子""",
        "EXPERIENCE": """经验与成长评分标准（0-100）：
- 90-100：成就突出，有具体数据（如性能提升 X%、用户增长 X），展现了主动性和成长性
- 70-89：有一定成就，但数据不够具体或影响力有限
- 50-69：经历平淡，没有突出贡献
- 30-49：无法清晰描述自己的贡献
- 0-29：没有有价值的工作经历""",
    }
    prompt = (
        "你是一位面试评估专家。请严格根据评分标准评估候选人的回答。\n\n"
        f"评分标准：\n{rubric.get(eval_type, rubric['TECHNICAL'])}\n\n"
        f"问题类型：{eval_type}\n"
        f"候选人回答：{answer[:800]}\n\n"
        "请返回严格 JSON（必须包含 score 和 category 两个字段）：\n"
        '{"score": 0-100整数, "category": "技术能力|沟通表达|问题解决|协作能力|学习成长"}'
    )

    try:
        result = llm_service.generate(prompt, "你是一位专业的面试评估专家。")
        parsed = _parse_eval_result(result)
        score = int(parsed.get("score")) if parsed and "score" in parsed else None
    except Exception as exc:
        print(f"[interview_graph] answer evaluation failed: {exc}")
        score = None
        parsed = {}

    if score is None:
        return

    category = str(parsed.get("category") or ("技术能力" if eval_type == "TECHNICAL" else "沟通表达"))
    score = max(0, min(100, score))
    if eval_type == "TECHNICAL":
        skill_scores = dict(state.get("skill_scores", {}) or {})
        skill_scores[category] = score
        state["skill_scores"] = skill_scores
    else:
        behavior_scores = dict(state.get("behavior_scores", {}) or {})
        behavior_scores[category] = score
        state["behavior_scores"] = behavior_scores


def _eval_type_for_questions(questions_asked: Any) -> str:
    count = int(questions_asked or 0)
    if count < 2:
        return "TECHNICAL"
    if count < 4:
        return "BEHAVIORAL"
    return "EXPERIENCE"


def _question_type_and_topic(questions_asked: int) -> tuple[str, str]:
    if questions_asked < 2:
        return "TECHNICAL", "技术能力（项目实战、技术栈细节）"
    if questions_asked < 4:
        return "BEHAVIORAL", "问题解决与协作（行为面试题）"
    return "EXPERIENCE", "过往成就与成长经历"


def _format_recent_history(history: List[Dict[str, Any]]) -> str:
    if not history or len(history) < 2:
        return ""
    recent = history[-6:]
    qa_pairs = []
    for index in range(0, len(recent), 2):
        if index + 1 >= len(recent):
            continue
        question = recent[index].get("content", "")[:200] if isinstance(recent[index], dict) else str(recent[index])
        answer = recent[index + 1].get("content", "")[:300] if isinstance(recent[index + 1], dict) else str(recent[index + 1])
        qa_pairs.append(f"问：{question}\n答：{answer}")
    return "\n\n".join(qa_pairs[-3:])


def _format_evidence_context(evidence: List[Dict[str, Any]], limit: int = 4) -> str:
    lines = []
    for idx, item in enumerate((evidence or [])[:limit], start=1):
        source = item.get("title") or item.get("sourceId") or item.get("sourceType") or "来源"
        text = item.get("highlight") or item.get("text") or ""
        if text:
            lines.append(f"[证据{idx}｜{source}] {text[:260]}")
    return "\n".join(lines)


def _evidence_to_dicts(evidence_items: List[Any]) -> List[Dict[str, Any]]:
    result = []
    for item in evidence_items or []:
        if hasattr(item, "model_dump"):
            result.append(item.model_dump())
        elif isinstance(item, dict):
            result.append(item)
    return result


def _parse_eval_result(text: str) -> Dict[str, Any]:
    match = re.search(r"\{.*\}", text or "", re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except Exception:
            pass
    return {}


_interview_graph = None


def get_interview_graph():
    """获取或创建全局面试图实例"""
    global _interview_graph
    if _interview_graph is None:
        _interview_graph = create_interview_graph()
    return _interview_graph
