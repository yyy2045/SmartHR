"""
上下文管理器 - 基于 Redis 的用户偏好与对话上下文管理
"""

import json
from typing import Dict, Any, List, Optional
from src.services.redis_service import redis_service


class ContextManager:
    """通过 Redis 管理用户偏好和对话上下文"""

    def __init__(self):
        self.redis = redis_service
        self.user_pref_ttl = 86400 * 30  # 30天
        self.conversation_ttl = 86400  # 24小时

    async def save_user_preference(self, user_id: str, preference: Dict[str, Any]):
        """
        保存用户偏好（面试风格、沟通偏好等）
        """
        key = f"user:{user_id}:preferences"
        self.redis.set(key, json.dumps(preference), expire=self.user_pref_ttl)

    async def get_user_preference(self, user_id: str) -> Dict[str, Any]:
        """获取用户偏好"""
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
        """更新特定的偏好字段"""
        current = await self.get_user_preference(user_id)
        current.update(updates)
        await self.save_user_preference(user_id, current)

    async def delete_user_preference(self, user_id: str):
        """删除用户偏好"""
        key = f"user:{user_id}:preferences"
        self.redis.delete(key)

    async def save_conversation_context(self, session_id: str, context: Dict[str, Any]):
        """
        保存某个会话的对话上下文。
        包含简历上下文、岗位上下文、面试进度等。
        """
        key = f"conversation:{session_id}:context"
        self.redis.set(key, json.dumps(context), expire=self.conversation_ttl)

    async def get_conversation_context(self, session_id: str) -> Dict[str, Any]:
        """获取对话上下文"""
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
        追加一条消息到对话历史中。
        维护一个包含最后 N 条消息的滚动窗口。
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

        # 仅保留最后 100 条消息
        if len(history) > 100:
            history = history[-100:]

        self.redis.set(key, json.dumps(history), expire=self.conversation_ttl)

    async def get_history(self, session_id: str) -> List[Dict[str, Any]]:
        """获取对话历史"""
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
        """清空对话历史"""
        key = f"conversation:{session_id}:history"
        self.redis.delete(key)

    async def save_interview_progress(self, session_id: str, progress: Dict[str, Any]):
        """保存面试进度（当前阶段、分数等）"""
        key = f"interview:{session_id}:progress"
        self.redis.set(key, json.dumps(progress), expire=self.conversation_ttl)

    async def get_interview_progress(self, session_id: str) -> Dict[str, Any]:
        """获取面试进度"""
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
        """保存候选人画像以供面试期间快速访问"""
        key = f"candidate:{candidate_id}:profile"
        self.redis.set(key, json.dumps(profile), expire=self.user_pref_ttl)

    async def get_candidate_profile(self, candidate_id: str) -> Dict[str, Any]:
        """获取候选人画像"""
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
        """保存岗位上下文用于面试准备"""
        key = f"job:{job_id}:context"
        self.redis.set(key, json.dumps(context), expire=self.user_pref_ttl)

    async def get_job_context(self, job_id: str) -> Dict[str, Any]:
        """获取岗位上下文"""
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
        """删除某个会话的所有上下文数据"""
        keys = [
            f"conversation:{session_id}:context",
            f"conversation:{session_id}:history",
            f"interview:{session_id}:progress"
        ]
        for key in keys:
            self.redis.delete(key)

    def _get_timestamp(self) -> str:
        """获取当前时间戳"""
        from datetime import datetime
        return datetime.utcnow().isoformat()

    async def get_all_user_sessions(self, user_id: str) -> List[str]:
        """获取用户的所有会话 ID（用于断点续面/恢复面试能力）"""
        pattern = f"conversation:*:context"
        keys = self.redis.scan_keys(pattern)
        session_ids = []
        for key in keys:
            # 从键名中提取 session_id: conversation:{session_id}:context
            # 使用 rsplit 处理可能包含冒号的 session_id
            parts = key.rsplit(":", 1)
            if len(parts) == 2:
                # parts[0] 为 "conversation:{session_id}"，提取出 session_id
                session_id = parts[0].split(":", 1)[1] if ":" in parts[0] else parts[0]
                session_ids.append(session_id)
        return session_ids


# 全局实例
context_manager = ContextManager()