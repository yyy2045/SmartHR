"""
技能评估智能体 - 评估技术深度并核验事实
"""

from typing import Dict, Any, List
from src.services.llm_service import llm_service
from src.services.knowledge_retriever import knowledge_retriever


class SkillEvaluatorAgent:
    """技能评估智能体 - 深度评估技术能力"""

    def __init__(self):
        self.llm = llm_service

    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """基于最新回答处理技能评估"""
        messages = state.get("messages", [])
        skill_scores = state.get("skill_scores", {})
        current_question = state.get("current_question", {})
        company_id = state.get("company_id", "")

        # 检索技术核验相关的知识库上下文
        knowledge_context = ""
        if company_id:
            try:
                import asyncio
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        knowledge_context = ""
                    else:
                        knowledge_context = loop.run_until_complete(
                            knowledge_retriever.get_context_for_agent(
                                agent_type="SKILL",
                                query="technical requirements skills",
                                company_id=str(company_id)
                            )
                        )
                except RuntimeError:
                    knowledge_context = ""
            except Exception as e:
                print(f"警告: 获取知识上下文失败: {e}")

        # 获取最新候选人回答
        latest_response = None
        for msg in reversed(messages):
            if msg.get("role") == "candidate":
                latest_response = msg.get("content", "")
                break

        if latest_response:
            # 从回答中提取技术声明
            claims = self.extract_claims(latest_response)

            # 为每个声明的技能打分
            for claim in claims:
                score = self.score_skill(claim, latest_response, knowledge_context)
                skill_name = self._extract_skill_name(claim)
                skill_scores[skill_name] = score

            state["skill_scores"] = skill_scores

        state["current_agent"] = "SKILL"
        return state

    def extract_claims(self, message: str) -> List[str]:
        """从回答中提取技术声明"""
        prompt = f"""从以下面试回答中，提取候选人声明的所有技术技能。

回答: {message}

提取类似以下的声明：
- "我有 5 年 Python 经验"
- "精通 Spring Boot"
- "领导过 10 人工程师团队"
- "有微服务经验"

返回一个 JSON 数组的声明。如果没有找到技术声明，返回空数组。"""

        result = self.llm.generate(prompt, system_prompt="你是一个技术技能分析师。")
        return self._parse_claims(result)

    def verify_claim(self, claim: str, resume_text: str) -> bool:
        """验证声明是否与简历一致"""
        prompt = f"""将此面试声明与候选人的简历进行对比：

声明: {claim}
简历: {resume_text}

声明是否被简历支持？回答是或否，并简要解释。"""

        result = self.llm.generate(prompt, system_prompt="你验证简历中的技术声明。")
        return "是" in result.upper() or "YES" in result.upper()

    def score_skill(self, skill: str, response: str, knowledge_context: str = "") -> float:
        """基于回答深度为技术技能打分"""
        context_section = f"\n\n公司知识库上下文:\n{knowledge_context}" if knowledge_context else ""
        prompt = f"""评估这个面试回答的技术深度：

技能声明: {skill}
回答: {response}{context_section}

根据以下标准为技术深度打分（0-100）：
- 0-30: 模糊或表面的声明，没有具体例子
- 31-60: 有一定细节但缺乏深度或具体成就
- 61-85: 有具体例子、可量化的成果提及
- 86-100: 深入的技术知识、详细的例子、指标、影响

只返回一个 0-100 的数字。"""

        result = self.llm.generate(prompt, system_prompt="你是一个技术面试评估专家。")
        try:
            return float(result.strip())
        except ValueError:
            return 50.0

    def _extract_skill_name(self, claim: str) -> str:
        """从声明中提取技能名称"""
        # 简单提取 - 生产环境需要更复杂的 NLP
        keywords = ["python", "java", "spring", "kubernetes", "docker", "aws", "sql", "javascript", "react", "node"]
        claim_lower = claim.lower()

        for keyword in keywords:
            if keyword in claim_lower:
                return keyword

        return "general"

    def _parse_claims(self, result: str) -> List[str]:
        """将 LLM 响应解析为声明列表"""
        # 简单 JSON 解析 - 生产环境需要更健壮的解析
        import json
        import re

        # 尝试在响应中找到 JSON 数组
        match = re.search(r'\[.*\]', result, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass

        # 降级方案：按行分割
        return [line.strip() for line in result.split("\n") if line.strip()]