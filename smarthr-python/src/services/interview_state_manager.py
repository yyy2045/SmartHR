"""
面试状态管理器 - 基于 Redis 的多智能体面试状态持久化
"""

import asyncio
import json
from typing import Dict, Any, List, Optional
from src.services.redis_service import redis_service


class InterviewStateManager:
    """通过 Redis 管理面试状态持久化，支持断点续面"""

    def __init__(self):
        self.redis = redis_service
        self.ttl = 86400  # 24 小时

    async def save_state(self, session_id: str, state: Dict[str, Any]):
        """将当前面试状态保存到 Redis"""
        key = f"interview:{session_id}:state"
        # 将状态序列化为 JSON
        serialized = self._serialize_state(state)
        self.redis.set(key, serialized, expire=self.ttl)

    async def load_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        """从 Redis 加载面试状态"""
        key = f"interview:{session_id}:state"
        data = self.redis.get(key)
        if data:
            return self._deserialize_state(data)
        return None

    async def append_message(self, session_id: str, role: str, content: str, metadata: Dict[str, Any] = None):
        """向对话历史添加消息（使用 Redis 列表实现原子操作）"""
        key = f"interview:{session_id}:history"
        message = {
            "role": role,
            "content": content,
            "metadata": metadata or {}
        }
        import json
        serialized = json.dumps(message)
        # 使用 RPUSH 原子追加，避免 get_history + set 的 race condition
        await asyncio.to_thread(self.redis.client.rpush, key, serialized)
        await asyncio.to_thread(self.redis.client.expire, key, self.ttl)

    async def get_history(self, session_id: str) -> List[Dict[str, Any]]:
        """获取完整的对话历史"""
        key = f"interview:{session_id}:history"
        # 使用 LRANGE 获取列表中的所有消息
        items = await asyncio.to_thread(self.redis.client.lrange, key, 0, -1)
        history = []
        for item in items:
            try:
                history.append(json.loads(item))
            except json.JSONDecodeError:
                pass
        return history

    async def update_skill_scores(self, session_id: str, skill_scores: Dict[str, float]):
        """更新会话的技能分数（合并已有分数）"""
        key = f"interview:{session_id}:skills"
        # 使用 Lua 脚本实现原子的读-合并-写，避免竞态条件
        lua_script = """
        local existing = redis.call('GET', KEYS[1])
        local merged = {}
        if existing then
            merged = cjson.decode(existing)
        end
        local update = cjson.decode(ARGV[1])
        for k, v in pairs(update) do
            merged[k] = v
        end
        redis.call('SET', KEYS[1], cjson.encode(merged), 'EX', ARGV[2])
        return 1
        """
        try:
            self.redis.client.eval(
                lua_script, 1, key,
                json.dumps(skill_scores), self.ttl
            )
        except Exception as e:
            # 降级：使用原有的非原子方式（极少并发场景）
            existing = await self.get_skill_scores(session_id)
            merged = {**existing, **skill_scores}
            await asyncio.to_thread(self.redis.set, key, json.dumps(merged), self.ttl)

    async def get_skill_scores(self, session_id: str) -> Dict[str, float]:
        """获取会话的技能分数"""
        key = f"interview:{session_id}:skills"
        data = await asyncio.to_thread(self.redis.get, key)
        if data:
            if isinstance(data, dict):
                return data
            try:
                return json.loads(data)
            except json.JSONDecodeError:
                return {}
        return {}

    async def update_behavior_scores(self, session_id: str, behavior_scores: Dict[str, float]):
        """更新会话的行为分数（合并已有分数）"""
        key = f"interview:{session_id}:behavior"
        lua_script = """
        local existing = redis.call('GET', KEYS[1])
        local merged = {}
        if existing then
            merged = cjson.decode(existing)
        end
        local update = cjson.decode(ARGV[1])
        for k, v in pairs(update) do
            merged[k] = v
        end
        redis.call('SET', KEYS[1], cjson.encode(merged), 'EX', ARGV[2])
        return 1
        """
        try:
            self.redis.client.eval(
                lua_script, 1, key,
                json.dumps(behavior_scores), self.ttl
            )
        except Exception as e:
            existing = await self.get_behavior_scores(session_id)
            merged = {**existing, **behavior_scores}
            await asyncio.to_thread(self.redis.set, key, json.dumps(merged), self.ttl)

    async def get_behavior_scores(self, session_id: str) -> Dict[str, float]:
        """获取会话的行为分数"""
        key = f"interview:{session_id}:behavior"
        data = await asyncio.to_thread(self.redis.get, key)
        if data:
            if isinstance(data, dict):
                return data
            try:
                return json.loads(data)
            except json.JSONDecodeError:
                return {}
        return {}

    async def save_report(self, session_id: str, report: Dict[str, Any]):
        """保存最终的面试报告"""
        key = f"interview:{session_id}:report"
        self.redis.set(key, json.dumps(report), expire=self.ttl * 30)  # 报告保留更长时间

    async def get_report(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取面试报告"""
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
        """删除会话的所有数据"""
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
        """检查会话是否存在"""
        key = f"interview:{session_id}:state"
        return self.redis.exists(key)

    async def get_session_status(self, session_id: str) -> Optional[str]:
        """获取会话的当前状态"""
        state = await self.load_state(session_id)
        if state:
            return state.get("status", "UNKNOWN")
        return None

    def _serialize_state(self, state: Dict[str, Any]) -> str:
        """将状态字典序列化为 JSON 字符串"""
        return json.dumps(state, default=str)

    def _deserialize_state(self, data: Any) -> Dict[str, Any]:
        """将 JSON 字符串反序列化为状态字典"""
        if isinstance(data, dict):
            return data
        if isinstance(data, str):
            try:
                return json.loads(data)
            except json.JSONDecodeError:
                return {}
        return {}

    async def get_all_sessions(self, company_id: str = None) -> List[str]:
        """获取所有会话 ID，可按公司过滤"""
        pattern = "interview:*:state"
        keys = self.redis.scan_keys(pattern)
        session_ids = []
        for key in keys:
            # 从键中提取 session_id
            parts = key.split(":")
            if len(parts) >= 2:
                session_ids.append(parts[1])
        return session_ids


# 全局实例
interview_state_manager = InterviewStateManager()