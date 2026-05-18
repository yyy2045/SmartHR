"""
Interview State Manager - Redis-based state persistence for multi-agent interview
"""

import json
from typing import Dict, Any, List, Optional
from src.services.redis_service import redis_service


class InterviewStateManager:
    """Manages interview state persistence via Redis for resume capability"""

    def __init__(self):
        self.redis = redis_service
        self.ttl = 86400  # 24 hours

    async def save_state(self, session_id: str, state: Dict[str, Any]):
        """Save the current interview state to Redis"""
        key = f"interview:{session_id}:state"
        # Serialize state to JSON
        serialized = self._serialize_state(state)
        self.redis.set(key, serialized, expire=self.ttl)

    async def load_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Load interview state from Redis"""
        key = f"interview:{session_id}:state"
        data = self.redis.get(key)
        if data:
            return self._deserialize_state(data)
        return None

    async def append_message(self, session_id: str, role: str, content: str, metadata: Dict[str, Any] = None):
        """Append a message to the conversation history"""
        key = f"interview:{session_id}:history"
        message = {
            "role": role,
            "content": content,
            "metadata": metadata or {}
        }
        # Get existing history
        history = self.get_history(session_id)
        history.append(message)
        # Save updated history
        self.redis.set(key, json.dumps(history), expire=self.ttl)

    async def get_history(self, session_id: str) -> List[Dict[str, Any]]:
        """Get the complete conversation history"""
        key = f"interview:{session_id}:history"
        data = self.redis.get(key)
        if data:
            if isinstance(data, list):
                return data
            try:
                return json.loads(data)
            except json.JSONDecodeError:
                return []
        return []

    async def update_skill_scores(self, session_id: str, skill_scores: Dict[str, float]):
        """Update skill scores for the session"""
        key = f"interview:{session_id}:skills"
        self.redis.set(key, json.dumps(skill_scores), expire=self.ttl)

    async def get_skill_scores(self, session_id: str) -> Dict[str, float]:
        """Get skill scores for the session"""
        key = f"interview:{session_id}:skills"
        data = self.redis.get(key)
        if data:
            if isinstance(data, dict):
                return data
            try:
                return json.loads(data)
            except json.JSONDecodeError:
                return {}
        return {}

    async def update_behavior_scores(self, session_id: str, behavior_scores: Dict[str, float]):
        """Update behavior scores for the session"""
        key = f"interview:{session_id}:behavior"
        self.redis.set(key, json.dumps(behavior_scores), expire=self.ttl)

    async def get_behavior_scores(self, session_id: str) -> Dict[str, float]:
        """Get behavior scores for the session"""
        key = f"interview:{session_id}:behavior"
        data = self.redis.get(key)
        if data:
            if isinstance(data, dict):
                return data
            try:
                return json.loads(data)
            except json.JSONDecodeError:
                return {}
        return {}

    async def save_report(self, session_id: str, report: Dict[str, Any]):
        """Save the final interview report"""
        key = f"interview:{session_id}:report"
        self.redis.set(key, json.dumps(report), expire=self.ttl * 30)  # Keep reports longer

    async def get_report(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get the interview report"""
        key = f"interview:{session_id}:report"
        data = self.redis.get(key)
        if data:
            if isinstance(data, dict):
                return data
            try:
                return json.loads(data)
            except json.JSONDecodeError:
                return None
        return None

    async def delete_session(self, session_id: str):
        """Delete all data for a session"""
        keys = [
            f"interview:{session_id}:state",
            f"interview:{session_id}:history",
            f"interview:{session_id}:skills",
            f"interview:{session_id}:behavior",
            f"interview:{session_id}:report"
        ]
        for key in keys:
            self.redis.delete(key)

    async def session_exists(self, session_id: str) -> bool:
        """Check if a session exists"""
        key = f"interview:{session_id}:state"
        return self.redis.exists(key)

    async def get_session_status(self, session_id: str) -> Optional[str]:
        """Get the current status of a session"""
        state = await self.load_state(session_id)
        if state:
            return state.get("status", "UNKNOWN")
        return None

    def _serialize_state(self, state: Dict[str, Any]) -> str:
        """Serialize state dict to JSON string"""
        return json.dumps(state, default=str)

    def _deserialize_state(self, data: Any) -> Dict[str, Any]:
        """Deserialize JSON string to state dict"""
        if isinstance(data, dict):
            return data
        if isinstance(data, str):
            try:
                return json.loads(data)
            except json.JSONDecodeError:
                return {}
        return {}

    async def get_all_sessions(self, company_id: str = None) -> List[str]:
        """Get all session IDs, optionally filtered by company"""
        pattern = "interview:*:state"
        keys = self.redis.keys(pattern)
        session_ids = []
        for key in keys:
            # Extract session_id from key
            parts = key.split(":")
            if len(parts) >= 2:
                session_ids.append(parts[1])
        return session_ids


# Global instance
interview_state_manager = InterviewStateManager()