"""
Redis 服务 - 会话内存和缓存
"""

import redis
import json
from typing import Any, Optional, Dict
from src.config import settings


class RedisService:
    """Redis 服务，用于会话管理和缓存"""

    def __init__(self):
        self.client = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db,
            decode_responses=True
        )

    def set(self, key: str, value: Any, expire: Optional[int] = None):
        """设置值，可选过期时间（秒）"""
        if isinstance(value, (dict, list)):
            value = json.dumps(value)
        self.client.set(key, value)
        if expire:
            self.client.expire(key, expire)

    def get(self, key: str) -> Optional[Any]:
        """根据键获取值"""
        value = self.client.get(key)
        if value is None:
            return None
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value

    def delete(self, key: str):
        """删除键"""
        self.client.delete(key)

    def exists(self, key: str) -> bool:
        """检查键是否存在"""
        return self.client.exists(key) > 0

    def hash_set(self, name: str, mapping: Dict[str, Any]):
        """设置哈希字段"""
        encoded = {k: json.dumps(v) if isinstance(v, (dict, list)) else v for k, v in mapping.items()}
        self.client.hset(name, mapping=encoded)

    def hash_get(self, name: str, key: str) -> Optional[Any]:
        """获取哈希字段"""
        value = self.client.hget(name, key)
        if value is None:
            return None
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value

    def hash_get_all(self, name: str) -> Dict[str, Any]:
        """获取所有哈希字段"""
        data = self.client.hgetall(name)
        return {
            k: json.loads(v) if isinstance(v, str) and (v.startswith('{') or v.startswith('[')) else v
            for k, v in data.items()
        }

    def hash_delete(self, name: str, *keys):
        """删除哈希字段"""
        self.client.hdel(name, *keys)

    def keys(self, pattern: str) -> list:
        """获取匹配模式的键"""
        return self.client.keys(pattern)


# 全局实例
redis_service = RedisService()