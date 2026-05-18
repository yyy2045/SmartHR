"""
Interview State Machine - LangGraph StateGraph for multi-agent interview orchestration
"""

from typing import TypedDict, List, Dict, Any, Optional
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver


class InterviewState(TypedDict, total=False):
    """Shared state for the interview conversation"""
    session_id: str
    job_id: str
    resume_id: str
    company_id: Optional[str]
    current_agent: str  # MAIN, SKILL, BEHAVIOR, REPORT
    messages: List[Dict[str, Any]]  # conversation history
    skill_scores: Dict[str, float]  # skill -> score
    behavior_scores: Dict[str, float]  # behavior dimension -> score
    extracted_info: Dict[str, Any]  # extracted resume/jd info
    current_question: Optional[Dict[str, Any]]
    questions_asked: int
    is_complete: bool
    report_data: Optional[Dict[str, Any]]


def create_interview_graph():
    """Create and compile the interview state machine"""
    workflow = StateGraph(InterviewState)

    # Add nodes
    workflow.add_node("main_interviewer", _main_interviewer_node)
    workflow.add_node("skill_evaluator", _skill_evaluator_node)
    workflow.add_node("behavior_analyzer", _behavior_analyzer_node)
    workflow.add_node("report_generator", _report_generator_node)

    # Set entry point
    workflow.set_entry_point("main_interviewer")

    # Add edges
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

    # Compile with memory checkpointer for state persistence
    checkpointer = MemorySaver()
    return workflow.compile(checkpointer=checkpointer)


def _main_interviewer_node(state: InterviewState) -> InterviewState:
    """Main interviewer agent - generates questions and evaluates responses"""
    from src.agents.main_interviewer import MainInterviewerAgent

    agent = MainInterviewerAgent()
    return agent.process(state)


def _skill_evaluator_node(state: InterviewState) -> InterviewState:
    """Skill evaluator agent - assesses technical depth and verifies claims"""
    from src.agents.skill_evaluator import SkillEvaluatorAgent

    agent = SkillEvaluatorAgent()
    return agent.process(state)


def _behavior_analyzer_node(state: InterviewState) -> InterviewState:
    """Behavior analyzer agent - analyzes soft skills and culture fit"""
    from src.agents.behavior_analyzer import BehaviorAnalyzerAgent

    agent = BehaviorAnalyzerAgent()
    return agent.process(state)


def _report_generator_node(state: InterviewState) -> InterviewState:
    """Report generator agent - cross-validates and produces final report"""
    from src.agents.report_generator import ReportGeneratorAgent

    agent = ReportGeneratorAgent()
    return agent.process(state)


def _decide_next_agent(state: InterviewState) -> str:
    """Decision logic for routing after main interviewer"""
    messages = state.get("messages", [])
    questions_asked = state.get("questions_asked", 0)

    # End interview after ~10 questions
    if questions_asked >= 10:
        return "END"

    # Route based on current phase
    current_question = state.get("current_question", {})
    question_type = current_question.get("question_type", "")

    if question_type == "TECHNICAL":
        return "skill_evaluator"
    elif question_type == "BEHAVIORAL":
        return "behavior_analyzer"
    else:
        # Opening questions route to skill evaluation first
        return "skill_evaluator"


def _should_continue_to_behavior(state: InterviewState) -> str:
    """After skill evaluation, decide next step"""
    skill_scores = state.get("skill_scores", {})
    if len(skill_scores) >= 3:
        return "behavior_analyzer"
    return "main_interviewer"


def _should_continue_to_report(state: InterviewState) -> str:
    """After behavior analysis, decide if ready for report"""
    behavior_scores = state.get("behavior_scores", {})
    questions_asked = state.get("questions_asked", 0)

    if len(behavior_scores) >= 2 or questions_asked >= 10:
        return "report_generator"
    return "main_interviewer"


# Global compiled graph instance
_interview_graph = None


def get_interview_graph():
    """Get or create the global interview graph instance"""
    global _interview_graph
    if _interview_graph is None:
        _interview_graph = create_interview_graph()
    return _interview_graph