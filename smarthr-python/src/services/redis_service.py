"""
Redis Service - Session memory and caching
"""

import redis
import json
from typing import Any, Optional, Dict
from src.config import settings


class RedisService:
    """Redis service for session management and caching"""

    def __init__(self):
        self.client = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db,
            decode_responses=True
        )

    def set(self, key: str, value: Any, expire: Optional[int] = None):
        """Set value with optional expiration in seconds"""
        if isinstance(value, (dict, list)):
            value = json.dumps(value)
        self.client.set(key, value)
        if expire:
            self.client.expire(key, expire)

    def get(self, key: str) -> Optional[Any]:
        """Get value by key"""
        value = self.client.get(key)
        if value is None:
            return None
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value

    def delete(self, key: str):
        """Delete key"""
        self.client.delete(key)

    def exists(self, key: str) -> bool:
        """Check if key exists"""
        return self.client.exists(key) > 0

    def hash_set(self, name: str, mapping: Dict[str, Any]):
        """Set hash field"""
        encoded = {k: json.dumps(v) if isinstance(v, (dict, list)) else v for k, v in mapping.items()}
        self.client.hset(name, mapping=encoded)

    def hash_get(self, name: str, key: str) -> Optional[Any]:
        """Get hash field"""
        value = self.client.hget(name, key)
        if value is None:
            return None
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value

    def hash_get_all(self, name: str) -> Dict[str, Any]:
        """Get all hash fields"""
        data = self.client.hgetall(name)
        return {
            k: json.loads(v) if v.startswith('{') or v.startswith('[') else v
            for k, v in data.items()
        }

    def hash_delete(self, name: str, *keys):
        """Delete hash fields"""
        self.client.hdel(name, *keys)

    def keys(self, pattern: str) -> list:
        """Get keys matching pattern"""
        return self.client.keys(pattern)


# Global instance
redis_service = RedisService()