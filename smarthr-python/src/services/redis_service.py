"""
Redis 服务 - 会话内存和缓存
带内存降级的容错设计
"""

import redis
import json
from typing import Any, Optional, Dict
from src.config import settings
from threading import Lock


class InMemoryFallback:
    """内存降级缓存 - Redis 不可用时使用"""

    def __init__(self):
        self._store: Dict[str, Any] = {}
        self._lock = Lock()
        self._ttl_store: Dict[str, float] = {}  # key -> expire_timestamp
        self._lists: Dict[str, list] = {}  # key -> list

    def set(self, key: str, value: Any, expire: Optional[int] = None):
        with self._lock:
            self._store[key] = value
            if expire:
                import time
                self._ttl_store[key] = time.time() + expire
            elif key in self._ttl_store:
                del self._ttl_store[key]

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            # 检查 TTL
            if key in self._ttl_store:
                import time
                if time.time() > self._ttl_store[key]:
                    del self._store[key]
                    del self._ttl_store[key]
                    return None
            return self._store.get(key)

    def delete(self, key: str):
        with self._lock:
            self._store.pop(key, None)
            self._ttl_store.pop(key, None)
            self._lists.pop(key, None)

    def exists(self, key: str) -> bool:
        with self._lock:
            if key in self._ttl_store:
                import time
                if time.time() > self._ttl_store[key]:
                    del self._store[key]
                    del self._ttl_store[key]
                    return False
            return key in self._store

    def scan_keys(self, pattern: str, count: int = 100) -> list:
        import fnmatch
        with self._lock:
            # 清理过期键
            import time
            now = time.time()
            expired = [k for k, exp in self._ttl_store.items() if now > exp]
            for k in expired:
                del self._store[k]
                del self._ttl_store[k]
            return [k for k in self._store.keys() if fnmatch.fnmatch(k, pattern)]

    def rpush(self, key: str, value: Any):
        """Redis RPUSH 的降级实现"""
        with self._lock:
            if key not in self._lists:
                self._lists[key] = []
            self._lists[key].append(value)

    def lrange(self, key: str, start: int, end: int) -> list:
        """Redis LRANGE 的降级实现"""
        with self._lock:
            if key not in self._lists:
                return []
            lst = self._lists[key]
            if end == -1:
                return lst[start:]
            return lst[start:end + 1] if start <= end else []

    def expire(self, key: str, seconds: int):
        """设置过期时间（兼容接口）"""
        with self._lock:
            import time
            self._ttl_store[key] = time.time() + seconds

    def eval(self, script: str, num_keys: int, key: str, *args):
        """
        评估 Lua 脚本（仅支持简单的 GET/SET/MERGE 模式）
        这是 InMemoryFallback 的简化实现，仅处理 update_skill_scores 和 update_behavior_scores 使用的模式
        """
        import json
        with self._lock:
            # 提取 JSON 参数（Lua 脚本传入的是序列化后的字符串）
            update_arg = args[0] if args else "{}"
            ttl = int(args[1]) if len(args) > 1 else 86400
            try:
                update = json.loads(update_arg)
            except (json.JSONDecodeError, TypeError):
                update = {}

            # GET existing value
            existing = self._store.get(key)
            merged = {}
            if existing:
                try:
                    merged = json.loads(existing) if isinstance(existing, str) else existing
                except (json.JSONDecodeError, TypeError):
                    merged = {}
            if not isinstance(merged, dict):
                merged = {}

            # Merge update into existing
            merged.update(update)

            # SET with new value and TTL
            import time
            self._store[key] = json.dumps(merged)
            self._ttl_store[key] = time.time() + ttl
            return 1

    def client(self):
        """返回兼容接口用于 rpush/lrange 等"""
        return self


class RedisService:
    """Redis 服务，用于会话管理和缓存，支持内存降级"""

    def __init__(self):
        self._use_fallback = False
        self._fallback = InMemoryFallback()
        self._lock = Lock()
        try:
            self.client = redis.Redis(
                host=settings.redis_host,
                port=settings.redis_port,
                db=settings.redis_db,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                max_connections=50
            )
            # Test connection
            self.client.ping()
            self._use_fallback = False
        except redis.ConnectionError as e:
            print(f"[redis] Redis 连接失败，使用内存降级: {e}")
            self._use_fallback = True
            self.client = self._fallback

    @property
    def is_fallback_mode(self) -> bool:
        return self._use_fallback

    def set(self, key: str, value: Any, expire: Optional[int] = None):
        """设置值，可选过期时间（秒）"""
        with self._lock:
            if self._use_fallback:
                self._fallback.set(key, value, expire)
                return
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            self.client.set(key, value)
            if expire:
                self.client.expire(key, expire)

    def get(self, key: str) -> Optional[Any]:
        """根据键获取值"""
        with self._lock:
            if self._use_fallback:
                return self._fallback.get(key)
            value = self.client.get(key)
            if value is None:
                return None
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value

    def delete(self, key: str):
        """删除键"""
        with self._lock:
            if self._use_fallback:
                self._fallback.delete(key)
                return
            self.client.delete(key)

    def exists(self, key: str) -> bool:
        """检查键是否存在"""
        with self._lock:
            if self._use_fallback:
                return self._fallback.exists(key)
            return self.client.exists(key) > 0

    def hash_set(self, name: str, mapping: Dict[str, Any]):
        """设置哈希字段"""
        with self._lock:
            if self._use_fallback:
                for k, v in mapping.items():
                    self._fallback.set(f"{name}:{k}", v)
                return
            encoded = {k: json.dumps(v) if isinstance(v, (dict, list)) else v for k, v in mapping.items()}
            self.client.hset(name, mapping=encoded)

    def hash_get(self, name: str, key: str) -> Optional[Any]:
        """获取哈希字段"""
        with self._lock:
            if self._use_fallback:
                return self._fallback.get(f"{name}:{key}")
            value = self.client.hget(name, key)
            if value is None:
                return None
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value

    def hash_get_all(self, name: str) -> Dict[str, Any]:
        """获取所有哈希字段"""
        with self._lock:
            if self._use_fallback:
                result = {}
                # 简单实现：获取所有以 name: 开头的键
                prefix = f"{name}:"
                for k, v in self._fallback._store.items():
                    if k.startswith(prefix):
                        result[k[len(prefix):]] = v
                return result
            data = self.client.hgetall(name)
            return {
                k: json.loads(v) if isinstance(v, str) and (v.startswith('{') or v.startswith('[')) else v
                for k, v in data.items()
            }

    def hash_delete(self, name: str, *keys):
        """删除哈希字段"""
        with self._lock:
            if self._use_fallback:
                for k in keys:
                    self._fallback.delete(f"{name}:{k}")
                return
            self.client.hdel(name, *keys)

    def keys(self, pattern: str) -> list:
        """获取匹配模式的键（仅开发环境使用，生产环境用 scan_keys）"""
        with self._lock:
            if self._use_fallback:
                return self._fallback.scan_keys(pattern)
            return self.client.keys(pattern)

    def scan_keys(self, pattern: str, count: int = 100) -> list:
        """使用 SCAN 迭代获取匹配模式的键，避免阻塞"""
        with self._lock:
            if self._use_fallback:
                return self._fallback.scan_keys(pattern, count)
            keys = []
            cursor = 0
            while True:
                cursor, batch = self.client.scan(cursor, match=pattern, count=count)
                keys.extend(batch)
                if cursor == 0:
                    break
            return keys


# 全局实例 - 延迟初始化避免启动失败
_redis_service: Optional[RedisService] = None


def get_redis_service() -> RedisService:
    global _redis_service
    if _redis_service is None:
        _redis_service = RedisService()
    return _redis_service


# 兼容旧代码的导出
def __getattr__(name):
    global _redis_service
    if name == "redis_service":
        return get_redis_service()
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


class RedisServiceProxy:
    """代理类，支持延迟初始化和降级"""

    def __getattr__(self, name):
        return getattr(get_redis_service(), name)


# 用于 from src.services.redis_service import redis_service 的兼容
redis_service = RedisServiceProxy()