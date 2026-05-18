"""
Main Interviewer Agent - Leads the interview conversation
"""

from typing import Dict, Any
from src.services.llm_service import llm_service


class MainInterviewerAgent:
    """Main interviewer agent that generates questions and evaluates responses"""

    def __init__(self):
        self.llm = llm_service

    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Process the current state and generate next action"""
        session_id = state.get("session_id", "")
        messages = state.get("messages", [])
        questions_asked = state.get("questions_asked", 0)

        # Initialize if first call
        if questions_asked == 0:
            state["messages"] = []
            state["skill_scores"] = {}
            state["behavior_scores"] = {}
            state["current_agent"] = "MAIN"

            # Generate opening question
            opening_question = self._generate_opening_question(state)
            state["current_question"] = {
                "question": opening_question,
                "question_type": "OPENING",
                "expected_skills": []
            }
            return state

        # Get the latest user message
        latest_message = messages[-1] if messages else None

        # Evaluate the response if there is one
        if latest_message and latest_message.get("role") == "candidate":
            response_quality = self._evaluate_response(latest_message.get("content", ""), state)

            # Decide next question or end
            if questions_asked >= 10:
                state["is_complete"] = True
            else:
                next_question = self._generate_next_question(state)
                state["current_question"] = next_question
                state["questions_asked"] = questions_asked + 1

        return state

    def _generate_opening_question(self, state: Dict[str, Any]) -> str:
        """Generate opening question based on job and resume"""
        job_id = state.get("job_id", "")
        resume_id = state.get("resume_id", "")

        prompt = f"""You are a professional interviewer conducting an interview.
        Generate a warm, welcoming opening question that gives the candidate a chance to introduce themselves.
        The question should be open-ended and invite the candidate to share their background and motivation.

        Job ID: {job_id}
        Resume ID: {resume_id}

        Return only the question text, no additional commentary."""

        return self.llm.generate(prompt, system_prompt="You are a professional interviewer.")

    def _evaluate_response(self, response: str, state: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate candidate's response quality"""
        prompt = f"""Evaluate this interview response:

        Response: {response}

        Provide a brief assessment of:
        1. Communication clarity (1-10)
        2. Relevance to position (1-10)
        3. Overall impression (1-10)

        Return a JSON with scores."""

        result = self.llm.generate(prompt, system_prompt="You are an expert interviewer analyst.")
        return {"response": response, "evaluation": result}

    def _generate_next_question(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Generate next interview question based on context"""
        job_id = state.get("job_id", "")
        resume_id = state.get("resume_id", "")
        questions_asked = state.get("questions_asked", 0)
        current_question = state.get("current_question", {})
        messages = state.get("messages", [])

        # Build context from conversation history
        context = "\n".join([
            f"{msg.get('role', '')}: {msg.get('content', '')}"
            for msg in messages[-5:]
        ])

        # Determine question type based on progress
        if questions_asked < 3:
            question_type = "TECHNICAL"
            topic = "technical skills and experience"
        elif questions_asked < 6:
            question_type = "BEHAVIORAL"
            topic = "problem-solving and teamwork"
        else:
            question_type = "EXPERIENCE"
            topic = "past accomplishments and growth"

        prompt = f"""Based on the following interview conversation, generate the next thoughtful question:

        Conversation:
        {context}

        Job ID: {job_id}
        Resume ID: {resume_id}
        Question #{questions_asked + 1}

        Generate a {question_type.lower()} question about {topic}.
        The question should probe deeper based on what the candidate has already shared.

        Return the question as a JSON with: question, question_type, expected_skills."""

        result = self.llm.generate(prompt, system_prompt="You are a professional interviewer.")
        return {
            "question": result,
            "question_type": question_type,
            "expected_skills": []
        }

    def decide_next_agent(self, state: Dict[str, Any]) -> str:
        """Decide which agent to route to next"""
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