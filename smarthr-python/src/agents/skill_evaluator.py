"""
Skill Evaluator Agent - Assesses technical depth and verifies claims
"""

from typing import Dict, Any, List
from src.services.llm_service import llm_service


class SkillEvaluatorAgent:
    """Skill evaluator agent - deep assessment of technical capabilities"""

    def __init__(self):
        self.llm = llm_service

    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Process skill evaluation based on the latest response"""
        messages = state.get("messages", [])
        skill_scores = state.get("skill_scores", {})
        current_question = state.get("current_question", {})

        # Get latest candidate response
        latest_response = None
        for msg in reversed(messages):
            if msg.get("role") == "candidate":
                latest_response = msg.get("content", "")
                break

        if latest_response:
            # Extract technical claims from response
            claims = self.extract_claims(latest_response)

            # Score each claimed skill
            for claim in claims:
                score = self.score_skill(claim, latest_response)
                skill_name = self._extract_skill_name(claim)
                skill_scores[skill_name] = score

            state["skill_scores"] = skill_scores

        state["current_agent"] = "SKILL"
        return state

    def extract_claims(self, message: str) -> List[str]:
        """Extract technical claims from the response"""
        prompt = f"""From the following interview response, extract all technical skill claims made by the candidate.

        Response: {message}

        Extract claims like:
        - "I have 5 years experience with Python"
        - "Proficient in Spring Boot"
        - "Led a team of 10 engineers"
        - "Experience with microservices"

        Return a JSON array of claims. If no technical claims found, return empty array."""

        result = self.llm.generate(prompt, system_prompt="You are a technical skills analyst.")
        return self._parse_claims(result)

    def verify_claim(self, claim: str, resume_text: str) -> bool:
        """Verify if a claim is consistent with the resume"""
        prompt = f"""Compare this interview claim with the candidate's resume:

        Claim: {claim}
        Resume: {resume_text}

        Is the claim supported by the resume? Answer YES or NO and explain briefly."""

        result = self.llm.generate(prompt, system_prompt="You verify technical claims against resumes.")
        return "YES" in result.upper()

    def score_skill(self, skill: str, response: str) -> float:
        """Score a technical skill based on the response depth"""
        prompt = f"""Evaluate this interview response for technical depth:

        Skill Claim: {skill}
        Response: {response}

        Score the technical depth of this response on a scale of 0-100:
        - 0-30: Vague or superficial claim, no specific examples
        - 31-60: Some detail but lacks depth or specific achievements
        - 61-85: Specific examples, quantifiable results mentioned
        - 86-100: Deep technical knowledge, detailed examples, metrics, impact

        Return only a number between 0-100."""

        result = self.llm.generate(prompt, system_prompt="You are a technical interview evaluator.")
        try:
            return float(result.strip())
        except ValueError:
            return 50.0

    def _extract_skill_name(self, claim: str) -> str:
        """Extract the skill name from a claim"""
        # Simple extraction - in production would use more sophisticated NLP
        keywords = ["python", "java", "spring", "kubernetes", "docker", "aws", "sql", "javascript", "react", "node"]
        claim_lower = claim.lower()

        for keyword in keywords:
            if keyword in claim_lower:
                return keyword

        return "general"

    def _parse_claims(self, result: str) -> List[str]:
        """Parse the LLM response into claims list"""
        # Simple JSON parsing - would need more robust parsing in production
        import json
        import re

        # Try to find JSON array in response
        match = re.search(r'\[.*\]', result, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass

        # Fallback: split by newlines
        return [line.strip() for line in result.split("\n") if line.strip()]