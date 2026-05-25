"""
行为分析智能体 - 分析软技能、逻辑思维和文化契合度
"""

from typing import Dict, Any
from src.services.llm_service import llm_service
from src.services.knowledge_retriever import knowledge_retriever


class BehaviorAnalyzerAgent:
    """行为分析智能体 - 评估软技能和文化契合度"""

    def __init__(self):
        self.llm = llm_service

    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """基于对话处理行为分析"""
        messages = state.get("messages", [])
        behavior_scores = state.get("behavior_scores", {})
        company_id = state.get("company_id", "")

        # 检索文化评估相关的知识库上下文
        knowledge_context = ""
        if company_id:
            try:
                import asyncio
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # 在已运行的 loop 中，使用 asyncio.ensure_future + callback 或直接跳过
                        knowledge_context = ""
                    else:
                        knowledge_context = asyncio.run(
                            knowledge_retriever.get_context_for_agent(
                                agent_type="BEHAVIOR",
                                query="company culture teamwork",
                                company_id=str(company_id)
                            )
                        )
                except RuntimeError:
                    knowledge_context = ""
            except Exception as e:
                print(f"警告: 获取知识上下文失败: {e}")

        # 获取近期的消息进行分析
        recent_messages = messages[-5:] if len(messages) > 5 else messages
        context = "\n".join([
            f"{msg.get('role', '')}: {msg.get('content', '')}"
            for msg in recent_messages
        ])

        if context:
            # 分析逻辑思维
            logical = self.analyze_logical_thinking(context)
            behavior_scores["logical_thinking"] = logical.get("score", 70)

            # 使用公司知识上下文分析软技能
            soft = self.analyze_soft_skills(context, knowledge_context)
            behavior_scores["communication"] = soft.get("communication_score", 70)
            behavior_scores["teamwork"] = soft.get("teamwork_score", 70)
            behavior_scores["stress_resistance"] = soft.get("stress_resistance", 70)

            state["behavior_scores"] = behavior_scores

        state["current_agent"] = "BEHAVIOR"
        return state

    def analyze_logical_thinking(self, response: str) -> Dict[str, Any]:
        """分析回答的逻辑结构"""
        prompt = f"""分析这个面试回答的逻辑思维：

回答:
{response}

请评估：
1. 结构 - 回答是否有清晰的组织？
2. 因果关系 - 因果关系是否清晰？
3. 完整性 - 要点是否充分展开还是有遗留？

将逻辑思维打分（0-100）。
返回包含分数（0-100）和简要解释的 JSON。"""

        result = self.llm.generate(prompt, system_prompt="你是一个分析逻辑思维的专家。")
        return self._parse_analysis_result(result)

    def analyze_soft_skills(self, response: str, knowledge_context: str = "") -> Dict[str, Any]:
        """分析回答中展示的软技能"""
        context_section = f"\n\n公司文化上下文:\n{knowledge_context}" if knowledge_context else ""
        prompt = f"""分析这个面试回答的软技能：

回答:
{response}{context_section}

请评估以下维度（每个 0-100 分）：
1. 沟通能力 - 清晰度、表达方式、词汇量
2. 团队协作 - 协作证据、处理分歧的方式
3. 抗压能力 - 处理压力、适应挑战的能力

返回包含 communication_score、teamwork_score、stress_resistance 和简要笔记的 JSON。"""

        result = self.llm.generate(prompt, system_prompt="你是一个评估软技能的专家。")
        return self._parse_soft_skills_result(result)

    def analyze_culture_fit(self, response: str, company_values: str = "") -> Dict[str, Any]:
        """基于公司价值观分析文化契合度"""
        if not company_values:
            company_values = "我们重视创新、协作和持续学习"

        prompt = f"""分析这个面试回答的文化契合度：

公司价值观: {company_values}
回答:
{response}

评估候选人的回答与公司价值观的契合程度。
考虑：
- 候选人是否表现出对创新的欣赏？
- 是否表现出协作心态？
- 是否致力于持续学习？

返回包含 culture_fit_score（0-100）和契合度笔记的 JSON。"""

        result = self.llm.generate(prompt, system_prompt="你是一个评估文化契合度的专家。")
        return self._parse_analysis_result(result)

    def _parse_analysis_result(self, result: str) -> Dict[str, Any]:
        """解析 LLM 分析结果"""
        import json
        import re

        # 先尝试 JSON 解析
        match = re.search(r'\{.*\}', result, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass

        # 降级方案：提取分数
        score_match = re.search(r'(\d+)', result)
        score = int(score_match.group(1)) if score_match else 70
        return {"score": score, "explanation": result[:200]}

    def _parse_soft_skills_result(self, result: str) -> Dict[str, Any]:
        """解析软技能分析结果"""
        import json
        import re

        # 先尝试 JSON 解析
        match = re.search(r'\{.*\}', result, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass

        # 降级默认值
        return {
            "communication_score": 70,
            "teamwork_score": 70,
            "stress_resistance": 70
        }