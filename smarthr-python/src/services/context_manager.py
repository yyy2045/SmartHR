"""
Context Manager - Redis-based user preferences and conversation context
"""

import json
from typing import Dict, Any, List, Optional
from src.services.redis_service import redis_service


class ContextManager:
    """Manage user preferences and conversation context via Redis"""

    def __init__(self):
        self.redis = redis_service
        self.user_pref_ttl = 86400 * 30  # 30 days
        self.conversation_ttl = 86400  # 24 hours

    async def save_user_preference(self, user_id: str, preference: Dict[str, Any]):
        """
        Save user preferences (interview style, communication preferences, etc.)
        """
        key = f"user:{user_id}:preferences"
        self.redis.set(key, json.dumps(preference), expire=self.user_pref_ttl)

    async def get_user_preference(self, user_id: str) -> Dict[str, Any]:
        """Get user preferences"""
        key = f"user:{user_id}:preferences"
        data = self.redis.get(key)
        if data:
            if isinstance(data, dict):
                return data
            try:
                return json.loads(data)
            except json.JSONDecodeError:
                return {}
        return {}

    async def update_user_preference(self, user_id: str, updates: Dict[str, Any]):
        """Update specific preference fields"""
        current = await self.get_user_preference(user_id)
        current.update(updates)
        await self.save_user_preference(user_id, current)

    async def delete_user_preference(self, user_id: str):
        """Delete user preferences"""
        key = f"user:{user_id}:preferences"
        self.redis.delete(key)

    async def save_conversation_context(self, session_id: str, context: Dict[str, Any]):
        """
        Save conversation context for a session.
        Includes resume context, job context, interview progress, etc.
        """
        key = f"conversation:{session_id}:context"
        self.redis.set(key, json.dumps(context), expire=self.conversation_ttl)

    async def get_conversation_context(self, session_id: str) -> Dict[str, Any]:
        """Get conversation context"""
        key = f"conversation:{session_id}:context"
        data = self.redis.get(key)
        if data:
            if isinstance(data, dict):
                return data
            try:
                return json.loads(data)
            except json.JSONDecodeError:
                return {}
        return {}

    async def append_to_history(self, session_id: str, role: str, content: str, metadata: Dict[str, Any] = None):
        """
        Append a message to the conversation history.
        Maintains a rolling window of last N messages.
        """
        key = f"conversation:{session_id}:history"
        history = await self.get_history(session_id)

        message = {
            "role": role,
            "content": content,
            "metadata": metadata or {},
            "timestamp": self._get_timestamp()
        }
        history.append(message)

        # Keep only last 100 messages
        if len(history) > 100:
            history = history[-100:]

        self.redis.set(key, json.dumps(history), expire=self.conversation_ttl)

    async def get_history(self, session_id: str) -> List[Dict[str, Any]]:
        """Get conversation history"""
        key = f"conversation:{session_id}:history"
        data = self.redis.get(key)
        if data:
            if isinstance(data, list):
                return data
            try:
                return json.loads(data)
            except json.JSONDecodeError:
                return []
        return []

    async def clear_history(self, session_id: str):
        """Clear conversation history"""
        key = f"conversation:{session_id}:history"
        self.redis.delete(key)

    async def save_interview_progress(self, session_id: str, progress: Dict[str, Any]):
        """Save interview progress (current phase, scores, etc.)"""
        key = f"interview:{session_id}:progress"
        self.redis.set(key, json.dumps(progress), expire=self.conversation_ttl)

    async def get_interview_progress(self, session_id: str) -> Dict[str, Any]:
        """Get interview progress"""
        key = f"interview:{session_id}:progress"
        data = self.redis.get(key)
        if data:
            if isinstance(data, dict):
                return data
            try:
                return json.loads(data)
            except json.JSONDecodeError:
                return {}
        return {}

    async def save_candidate_profile(self, candidate_id: str, profile: Dict[str, Any]):
        """Save candidate profile for quick access during interview"""
        key = f"candidate:{candidate_id}:profile"
        self.redis.set(key, json.dumps(profile), expire=self.user_pref_ttl)

    async def get_candidate_profile(self, candidate_id: str) -> Dict[str, Any]:
        """Get candidate profile"""
        key = f"candidate:{candidate_id}:profile"
        data = self.redis.get(key)
        if data:
            if isinstance(data, dict):
                return data
            try:
                return json.loads(data)
            except json.JSONDecodeError:
                return {}
        return {}

    async def save_job_context(self, job_id: str, context: Dict[str, Any]):
        """Save job context for interview preparation"""
        key = f"job:{job_id}:context"
        self.redis.set(key, json.dumps(context), expire=self.user_pref_ttl)

    async def get_job_context(self, job_id: str) -> Dict[str, Any]:
        """Get job context"""
        key = f"job:{job_id}:context"
        data = self.redis.get(key)
        if data:
            if isinstance(data, dict):
                return data
            try:
                return json.loads(data)
            except json.JSONDecodeError:
                return {}
        return {}

    async def delete_session_context(self, session_id: str):
        """Delete all context data for a session"""
        keys = [
            f"conversation:{session_id}:context",
            f"conversation:{session_id}:history",
            f"interview:{session_id}:progress"
        ]
        for key in keys:
            self.redis.delete(key)

    def _get_timestamp(self) -> str:
        """Get current timestamp"""
        from datetime import datetime
        return datetime.utcnow().isoformat()

    async def get_all_user_sessions(self, user_id: str) -> List[str]:
        """Get all session IDs for a user (for resume capability)"""
        pattern = f"conversation:*:context"
        keys = self.redis.scan_keys(pattern)
        session_ids = []
        for key in keys:
            # Extract session_id from key: conversation:{session_id}:context
            # Use rsplit to handle session_ids that may contain colons
            parts = key.rsplit(":", 1)
            if len(parts) == 2:
                # parts[0] is "conversation:{session_id}", extract session_id
                session_id = parts[0].split(":", 1)[1] if ":" in parts[0] else parts[0]
                session_ids.append(session_id)
        return session_ids


# Global instance
context_manager = ContextManager()