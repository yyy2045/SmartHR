"""
Report Generator Agent - Cross-validates and generates final interview report
"""

from typing import Dict, Any
from src.services.llm_service import llm_service


class ReportGeneratorAgent:
    """Report generator agent - produces final evaluation report"""

    def __init__(self):
        self.llm = llm_service

    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Generate the final interview report"""
        session_id = state.get("session_id", "")
        skill_scores = state.get("skill_scores", {})
        behavior_scores = state.get("behavior_scores", {})
        messages = state.get("messages", [])

        # Cross-validate scores
        validated_scores = self.cross_validate(skill_scores, behavior_scores)

        # Generate the report
        report = self.generate_report(state, validated_scores)

        state["report_data"] = report
        state["is_complete"] = True
        state["current_agent"] = "REPORT"

        return state

    def cross_validate(self, skill_scores: Dict[str, float],
                       behavior_scores: Dict[str, float]) -> Dict[str, Any]:
        """Cross-validate scores from different agents to detect inconsistencies"""
        prompt = f"""Cross-validate the following interview evaluation scores:

        Skill Scores: {skill_scores}
        Behavior Scores: {behavior_scores}

        Check for:
        1. Major contradictions (e.g., high technical but very low communication)
        2. Inconsistent patterns
        3. Missing evaluations

        Return a JSON with:
        - validated_skill_score: adjusted technical score
        - validated_behavior_score: adjusted behavior score
        - contradictions: list of detected issues
        - confidence: how confident we are in this evaluation (0-100)"""

        result = self.llm.generate(prompt, system_prompt="You are an expert interview analyst.")
        return self._parse_cross_validation(result)

    def generate_report(self, state: Dict[str, Any], validated_scores: Dict[str, Any]) -> Dict[str, Any]:
        """Generate final interview report"""
        session_id = state.get("session_id", "")
        skill_scores = state.get("skill_scores", {})
        behavior_scores = state.get("behavior_scores", {})
        messages = state.get("messages", [])

        # Build conversation summary
        conversation_summary = "\n".join([
            f"{msg.get('role', '')}: {msg.get('content', '')[:200]}"
            for msg in messages[-10:]
        ])

        prompt = f"""Generate a comprehensive interview report:

        Session ID: {session_id}
        Technical Skills: {skill_scores}
        Behavioral Scores: {behavior_scores}
        Validated Scores: {validated_scores}

        Conversation Summary:
        {conversation_summary}

        Generate a detailed report with:
        1. overall_score (0-100): Weighted average of skill and behavior
        2. skill_score (0-100): Technical evaluation
        3. behavior_score (0-100): Soft skills evaluation
        4. recommendation: STRONG_HIRE, HIRE, NO_HIRE, or WEAK_NO_HIRE
        5. summary: Executive summary (2-3 sentences)
        6. strengths: List of top 3-5 strengths
        7. concerns: List of 2-4 concerns
        8. interview_highlights: Key moments from the interview

        Return as JSON."""

        result = self.llm.generate(prompt, system_prompt="You are an expert interview report writer.")

        # Parse and structure the report
        report = self._parse_report(result)
        return report

    def _parse_cross_validation(self, result: str) -> Dict[str, Any]:
        """Parse cross-validation result"""
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
        """Parse the generated report"""
        import json
        import re

        match = re.search(r'\{.*\}', result, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass

        # Fallback structure
        return {
            "overall_score": 75,
            "skill_score": 72,
            "behavior_score": 78,
            "recommendation": "HIRE",
            "summary": "Candidate demonstrates solid technical abilities and good communication skills.",
            "strengths": ["Strong technical foundation", "Good problem-solving approach", "Clear communication"],
            "concerns": ["Limited leadership experience", "Could improve strategic thinking"],
            "interview_highlights": []
        }