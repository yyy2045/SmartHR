"""
面试状态机 - 基于 LangGraph 的多智能体面试编排
"""

from typing import TypedDict, List, Dict, Any, Optional
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver


class InterviewState(TypedDict, total=False):
    """面试对话共享状态"""
    session_id: str
    job_id: str
    resume_id: str
    company_id: Optional[str]
    current_agent: str  # MAIN, SKILL, BEHAVIOR, REPORT
    messages: List[Dict[str, Any]]  # 对话历史
    skill_scores: Dict[str, float]  # 技能 -> 分数
    behavior_scores: Dict[str, float]  # 行为维度 -> 分数
    extracted_info: Dict[str, Any]  # 提取的简历/JD 信息
    current_question: Optional[Dict[str, Any]]
    questions_asked: int
    is_complete: bool
    report_data: Optional[Dict[str, Any]]


def create_interview_graph():
    """创建并编译面试状态机"""
    workflow = StateGraph(InterviewState)

    # 添加节点
    workflow.add_node("main_interviewer", _main_interviewer_node)
    workflow.add_node("skill_evaluator", _skill_evaluator_node)
    workflow.add_node("behavior_analyzer", _behavior_analyzer_node)
    workflow.add_node("report_generator", _report_generator_node)

    # 设置入口点
    workflow.set_entry_point("main_interviewer")

    # 添加边
    workflow.add_conditional_edges(
        "main_interviewer",
        _decide_next_agent,
        {
            "skill_evaluator": "skill_evaluator",
            "behavior_analyzer": "behavior_analyzer",
            "END": END
        }
    )

    workflow.add_conditional_edges(
        "skill_evaluator",
        _should_continue_to_behavior,
        {
            "behavior_analyzer": "behavior_analyzer",
            "main_interviewer": "main_interviewer"
        }
    )

    workflow.add_conditional_edges(
        "behavior_analyzer",
        _should_continue_to_report,
        {
            "report_generator": "report_generator",
            "main_interviewer": "main_interviewer"
        }
    )

    workflow.add_edge("report_generator", END)

    # 使用内存检查点编译以支持状态持久化
    checkpointer = MemorySaver()
    return workflow.compile(checkpointer=checkpointer)


def _main_interviewer_node(state: InterviewState) -> InterviewState:
    """主面试官智能体 - 生成问题并评估回答"""
    from src.agents.main_interviewer import MainInterviewerAgent

    agent = MainInterviewerAgent()
    return agent.process(state)


def _skill_evaluator_node(state: InterviewState) -> InterviewState:
    """技能评估智能体 - 评估技术深度并核验事实"""
    from src.agents.skill_evaluator import SkillEvaluatorAgent

    agent = SkillEvaluatorAgent()
    return agent.process(state)


def _behavior_analyzer_node(state: InterviewState) -> InterviewState:
    """行为分析智能体 - 分析软技能和文化契合度"""
    from src.agents.behavior_analyzer import BehaviorAnalyzerAgent

    agent = BehaviorAnalyzerAgent()
    return agent.process(state)


def _report_generator_node(state: InterviewState) -> InterviewState:
    """报告生成智能体 - 交叉验证并生成最终报告"""
    from src.agents.report_generator import ReportGeneratorAgent

    agent = ReportGeneratorAgent()
    return agent.process(state)


def _decide_next_agent(state: InterviewState) -> str:
    """主面试官之后的路由决策逻辑"""
    messages = state.get("messages", [])
    questions_asked = state.get("questions_asked", 0)

    # 约 10 个问题后结束面试
    if questions_asked >= 10:
        return "END"

    # 根据当前阶段路由
    current_question = state.get("current_question", {})
    question_type = current_question.get("question_type", "")

    if question_type == "TECHNICAL":
        return "skill_evaluator"
    elif question_type == "BEHAVIORAL":
        return "behavior_analyzer"
    else:
        # 开场问题先路由到技能评估
        return "skill_evaluator"


def _should_continue_to_behavior(state: InterviewState) -> str:
    """技能评估后决定下一步"""
    skill_scores = state.get("skill_scores", {})
    if len(skill_scores) >= 3:
        return "behavior_analyzer"
    return "main_interviewer"


def _should_continue_to_report(state: InterviewState) -> str:
    """行为分析后决定是否准备生成报告"""
    behavior_scores = state.get("behavior_scores", {})
    questions_asked = state.get("questions_asked", 0)

    if len(behavior_scores) >= 2 or questions_asked >= 10:
        return "report_generator"
    return "main_interviewer"


# 全局编译后的图实例
_interview_graph = None


def get_interview_graph():
    """获取或创建全局面试图实例"""
    global _interview_graph
    if _interview_graph is None:
        _interview_graph = create_interview_graph()
    return _interview_graph