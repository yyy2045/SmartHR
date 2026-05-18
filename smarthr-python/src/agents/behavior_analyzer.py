"""
Behavior Analyzer Agent - Analyzes soft skills, logic, and culture fit
"""

from typing import Dict, Any
from src.services.llm_service import llm_service


class BehaviorAnalyzerAgent:
    """Behavior analyzer agent - evaluates soft skills and cultural fit"""

    def __init__(self):
        self.llm = llm_service

    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Process behavior analysis based on conversation"""
        messages = state.get("messages", [])
        behavior_scores = state.get("behavior_scores", {})

        # Get recent messages for analysis
        recent_messages = messages[-5:] if len(messages) > 5 else messages
        context = "\n".join([
            f"{msg.get('role', '')}: {msg.get('content', '')}"
            for msg in recent_messages
        ])

        if context:
            # Analyze logical thinking
            logical = self.analyze_logical_thinking(context)
            behavior_scores["logical_thinking"] = logical.get("score", 70)

            # Analyze soft skills
            soft = self.analyze_soft_skills(context)
            behavior_scores["communication"] = soft.get("communication_score", 70)
            behavior_scores["teamwork"] = soft.get("teamwork_score", 70)
            behavior_scores["stress_resistance"] = soft.get("stress_resistance", 70)

            state["behavior_scores"] = behavior_scores

        state["current_agent"] = "BEHAVIOR"
        return state

    def analyze_logical_thinking(self, response: str) -> Dict[str, Any]:
        """Analyze logical structure of the response"""
        prompt = f"""Analyze this interview response for logical thinking:

        Response:
        {response}

        Evaluate:
        1. Structure - Does the response have clear organization?
        2. Causality - Are cause-effect relationships clear?
        3. Completeness - Are points fully developed or left hanging?

        Score logical thinking as 0-100.
        Return JSON with score (0-100) and brief explanation."""

        result = self.llm.generate(prompt, system_prompt="You are an expert in analyzing logical thinking.")
        return self._parse_analysis_result(result)

    def analyze_soft_skills(self, response: str) -> Dict[str, Any]:
        """Analyze soft skills demonstrated in the response"""
        prompt = f"""Analyze this interview response for soft skills:

        Response:
        {response}

        Evaluate the following dimensions (score 0-100 each):
        1. Communication - Clarity, articulation, vocabulary
        2. Teamwork - Evidence of collaboration, handling disagreements
        3. Stress Resistance - Handling pressure, adapting to challenges

        Return JSON with communication_score, teamwork_score, stress_resistance, and brief notes."""

        result = self.llm.generate(prompt, system_prompt="You are an expert in evaluating soft skills.")
        return self._parse_soft_skills_result(result)

    def analyze_culture_fit(self, response: str, company_values: str = "") -> Dict[str, Any]:
        """Analyze culture fit based on company values and response"""
        if not company_values:
            company_values = "We value innovation, collaboration, and continuous learning"

        prompt = f"""Analyze this interview response for culture fit:

        Company Values: {company_values}
        Response:
        {response}

        Evaluate how well the candidate's responses align with the company values.
        Consider:
        - Does the candidate show appreciation for innovation?
        - Do they demonstrate collaborative mindset?
        - Are they committed to continuous learning?

        Return JSON with culture_fit_score (0-100) and alignment notes."""

        result = self.llm.generate(prompt, system_prompt="You are an expert in evaluating culture fit.")
        return self._parse_analysis_result(result)

    def _parse_analysis_result(self, result: str) -> Dict[str, Any]:
        """Parse LLM analysis result"""
        import json
        import re

        # Try JSON parsing first
        match = re.search(r'\{.*\}', result, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass

        # Fallback: extract score
        score_match = re.search(r'(\d+)', result)
        score = int(score_match.group(1)) if score_match else 70
        return {"score": score, "explanation": result[:200]}

    def _parse_soft_skills_result(self, result: str) -> Dict[str, Any]:
        """Parse soft skills analysis result"""
        import json
        import re

        # Try JSON parsing first
        match = re.search(r'\{.*\}', result, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass

        # Fallback defaults
        return {
            "communication_score": 70,
            "teamwork_score": 70,
            "stress_resistance": 70
        }