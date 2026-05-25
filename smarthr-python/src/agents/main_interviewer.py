"""
主面试官智能体 - 主导面试对话
"""

from typing import Dict, Any
from src.services.llm_service import llm_service


class MainInterviewerAgent:
    """主导面试官智能体，负责生成问题并评估回答"""

    def __init__(self):
        self.llm = llm_service

    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """处理当前状态并生成下一个动作"""
        session_id = state.get("session_id", "")
        messages = state.get("messages", [])
        questions_asked = state.get("questions_asked", 0)

        # 首次调用时初始化
        if questions_asked == 0:
            state["messages"] = []
            state["skill_scores"] = {}
            state["behavior_scores"] = {}
            state["current_agent"] = "MAIN"

            # 生成开场问题
            opening_question = self._generate_opening_question(state)
            state["current_question"] = {
                "question": opening_question,
                "question_type": "OPENING",
                "expected_skills": []
            }
            return state

        # 获取最新用户消息
        latest_message = messages[-1] if messages else None

        # 评估回答（如果有）
        if latest_message and latest_message.get("role") == "candidate":
            response_quality = self._evaluate_response(latest_message.get("content", ""), state)

            # 决定下一个问题或结束
            if questions_asked >= 10:
                state["is_complete"] = True
            else:
                next_question = self._generate_next_question(state)
                state["current_question"] = next_question
        state["questions_asked"] = questions_asked + 1

        return state

    def _get_knowledge_context(self, state: Dict[str, Any]) -> str:
        """
        获取面试相关的知识库上下文
        注意：完整的异步集成需要升级面试图
        目前仅记录上下文检索 - 实际检索发生在异步上下文中
        """
        company_id = str(state.get("company_id", ""))
        if not company_id:
            return ""
        # 占位符 - 完整集成需要异步面试图
        # 同时，skill_evaluator 和 behavior_analyzer 可以直接检索
        return ""

    def _generate_opening_question(self, state: Dict[str, Any]) -> str:
        """基于岗位和简历生成开场问题"""
        job_id = state.get("job_id", "")
        resume_id = state.get("resume_id", "")
        company_id = state.get("company_id", "")

        prompt = f"""你是一位专业的面试官，正在进行面试。
生成一个热情、友好的开场问题，让候选人有机会介绍自己。
问题应该是开放式的，邀请候选人分享他们的背景和动机。

公司 ID: {company_id}
岗位 ID: {job_id}
简历 ID: {resume_id}

只返回问题文本，不要添加其他评论。"""

        return self.llm.generate(prompt, system_prompt="你是一位专业的面试官。")

    def _evaluate_response(self, response: str, state: Dict[str, Any]) -> Dict[str, Any]:
        """评估候选人的回答质量"""
        prompt = f"""评估这个面试回答：

回答: {response}

请简要评估：
1. 沟通清晰度 (1-10)
2. 与职位的相关性 (1-10)
3. 整体印象 (1-10)

返回包含分数的 JSON。"""

        result = self.llm.generate(prompt, system_prompt="你是一位专业的面试分析师。")
        return {"response": response, "evaluation": result}

    def _generate_next_question(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """基于上下文生成下一个面试问题"""
        job_id = state.get("job_id", "")
        resume_id = state.get("resume_id", "")
        questions_asked = state.get("questions_asked", 0)
        current_question = state.get("current_question", {})
        messages = state.get("messages", [])

        # 从对话历史构建上下文
        context = "\n".join([
            f"{msg.get('role', '')}: {msg.get('content', '')}"
            for msg in messages[-5:]
        ])

        # 根据进度确定问题类型
        if questions_asked < 3:
            question_type = "TECHNICAL"
            topic = "技术技能和经验"
        elif questions_asked < 6:
            question_type = "BEHAVIORAL"
            topic = "问题解决和团队协作"
        else:
            question_type = "EXPERIENCE"
            topic = "过往成就和成长"

        prompt = f"""根据以下面试对话，生成下一个有意义的问题：

对话：
{context}

岗位 ID: {job_id}
简历 ID: {resume_id}
第 {questions_asked + 1} 个问题

生成一个关于 {topic} 的 {question_type.lower()} 问题。
问题应该根据候选人已经分享的内容进行深入探讨。

将问题以 JSON 格式返回，包含：question, question_type, expected_skills。"""

        result = self.llm.generate(prompt, system_prompt="你是一位专业的面试官。")
        return {
            "question": result,
            "question_type": question_type,
            "expected_skills": []
        }

    def decide_next_agent(self, state: Dict[str, Any]) -> str:
        """决定下一个路由到的智能体"""
        questions_asked = state.get("questions_asked", 0)
        current_question = state.get("current_question", {})
        question_type = current_question.get("question_type", "OPENING")

        if questions_asked >= 10:
            return "END"

        if question_type == "TECHNICAL":
            return "skill_evaluator"
        elif question_type == "BEHAVIORAL":
            return "behavior_analyzer"
        else:
            return "skill_evaluator"