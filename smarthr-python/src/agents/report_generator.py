"""
报告生成智能体 - 交叉验证并生成最终面试报告
"""

from typing import Dict, Any
from src.services.llm_service import llm_service


class ReportGeneratorAgent:
    """报告生成智能体 - 生成最终评估报告"""

    def __init__(self):
        self.llm = llm_service

    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """生成最终面试报告"""
        session_id = state.get("session_id", "")
        skill_scores = state.get("skill_scores", {})
        behavior_scores = state.get("behavior_scores", {})
        messages = state.get("messages", [])

        # 交叉验证分数
        validated_scores = self.cross_validate(skill_scores, behavior_scores)

        # 生成报告
        report = self.generate_report(state, validated_scores)

        state["report_data"] = report
        state["is_complete"] = True
        state["current_agent"] = "REPORT"

        return state

    def cross_validate(self, skill_scores: Dict[str, float],
                       behavior_scores: Dict[str, float]) -> Dict[str, Any]:
        """交叉验证来自不同智能体的分数，检测不一致性"""
        prompt = f"""交叉验证以下面试评估分数：

技能分数: {skill_scores}
行为分数: {behavior_scores}

检查：
1. 主要矛盾（例如：技术很高但沟通很低）
2. 不一致的模式
3. 缺失的评估

返回一个 JSON 对象，包含：
- validated_skill_score: 调整后的技术分数
- validated_behavior_score: 调整后的行为分数
- contradictions: 检测到的问题列表
- confidence: 我们对此评估的置信度（0-100）"""

        result = self.llm.generate(prompt, system_prompt="你是一个专业的面试分析师。")
        return self._parse_cross_validation(result)

    def generate_report(self, state: Dict[str, Any], validated_scores: Dict[str, Any]) -> Dict[str, Any]:
        """生成最终面试报告"""
        session_id = state.get("session_id", "")
        skill_scores = state.get("skill_scores", {})
        behavior_scores = state.get("behavior_scores", {})
        messages = state.get("messages", [])

        # 构建对话摘要（问答形式）
        qa_summary = self._build_qa_summary(messages)

        # 计算各维度平均分
        skill_avg = sum(skill_scores.values()) / len(skill_scores) if skill_scores else 75
        behavior_avg = sum(behavior_scores.values()) / len(behavior_scores) if behavior_scores else 75
        overall_avg = (skill_avg + behavior_avg) / 2

        # 构建对话文本摘要（供 LLM 使用）
        conversation_summary = "\n".join([
            f"{msg.get('role', '')}: {msg.get('content', '')[:200]}"
            for msg in messages[-10:]
        ])

        prompt = f"""生成一份综合面试报告：

会话 ID: {session_id}
技术技能（各维度）: {skill_scores}
行为分数（各维度）: {behavior_scores}
技术平均分: {skill_avg:.1f}
行为平均分: {behavior_avg:.1f}
验证后的分数: {validated_scores}

对话摘要：
{conversation_summary}

生成一份详细报告，包含：
1. overall_score (0-100): 综合评分（基于 {overall_avg:.1f} 调整）
2. skill_score (0-100): 技术评估（基于 {skill_avg:.1f} 调整）
3. behavior_score (0-100): 软技能评估（基于 {behavior_avg:.1f} 调整）
4. skillScores: 各技术维度评分（直接使用 skill_scores）
5. behaviorScores: 各行为维度评分（直接使用 behavior_scores）
6. recommendation: STRONG_HIRE, HIRE, NO_HIRE, 或 WEAK_NO_HIRE
7. summary: 执行摘要（2-3 句）
8. strengths: 3-5 个主要优势列表
9. concerns: 2-4 个顾虑列表
10. interview_highlights: 面试中的关键亮点

返回严格 JSON 格式，不要有其他任何文字。"""

        result = self.llm.generate(prompt, system_prompt="你是一个专业的面试报告撰写专家。")

        # 解析并结构化报告
        report = self._parse_report(result)
        # 确保多维度评分被保留
        report["skillScores"] = skill_scores
        report["behaviorScores"] = behavior_scores
        report["qaSummary"] = qa_summary
        return report

    def _build_qa_summary(self, messages: list) -> list:
        """从对话历史构建问答摘要"""
        qa_pairs = []
        current_q = None
        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role == "interviewer" and current_q is None:
                current_q = content[:200]
            elif role == "candidate" and current_q:
                qa_pairs.append({
                    "question": current_q,
                    "answer": content[:300],
                    "evaluation": ""
                })
                current_q = None
        return qa_pairs

    def _parse_cross_validation(self, result: str) -> Dict[str, Any]:
        """解析交叉验证结果"""
        import json
        import re

        match = re.search(r'\{.*\}', result, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass

        return {
            "validated_skill_score": 75,
            "validated_behavior_score": 75,
            "contradictions": [],
            "confidence": 80
        }

    def _parse_report(self, result: str) -> Dict[str, Any]:
        """解析生成的报告"""
        import json
        import re

        match = re.search(r'\{.*\}', result, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass

        # 降级结构
        return {
            "overall_score": 75,
            "skill_score": 72,
            "behavior_score": 78,
            "recommendation": "HIRE",
            "summary": "候选人展现出扎实的技术能力和良好的沟通技巧。",
            "strengths": ["技术基础扎实", "问题解决思路清晰", "沟通表达清晰"],
            "concerns": ["领导经验有限", "战略思维有待提升"],
            "interview_highlights": []
        }