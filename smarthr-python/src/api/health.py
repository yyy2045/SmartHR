"""
健康检查 API
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Any, Dict

from src.config import settings

router = APIRouter()

class HealthResponse(BaseModel):
    status: str
    service: str

@router.get("/health")
async def health_check() -> HealthResponse:
    """健康检查端点"""
    return HealthResponse(
        status="UP",
        service="SmartHR Python AI 服务"
    )


@router.get("/api/health")
async def api_health_check() -> HealthResponse:
    """兼容 Nginx /python/ 路由重写后的健康检查路径。"""
    return await health_check()


async def _dependency_health_check() -> Dict[str, Any]:
    """生产部署依赖健康检查：Redis、Chroma、本地 embedding 模型。"""
    dependencies: Dict[str, Any] = {}

    try:
        from src.services.redis_service import redis_service

        fallback_mode = bool(getattr(redis_service, "is_fallback_mode", False))
        dependencies["redis"] = {
            "status": "DOWN" if fallback_mode else "UP",
            "fallbackMode": fallback_mode,
        }
    except Exception as exc:
        dependencies["redis"] = {"status": "DOWN", "error": str(exc)}

    try:
        from src.services.vector_store import vector_store_service

        vector_store_service.client.heartbeat()
        use_http = getattr(vector_store_service, "_use_http", False)
        production_requires_http = settings.environment.lower() == "production"
        dependencies["chroma"] = {
            "status": "UP" if use_http or not production_requires_http else "DOWN",
            "mode": "http" if use_http else "embedded",
        }
    except Exception as exc:
        dependencies["chroma"] = {"status": "DOWN", "error": str(exc)}

    try:
        from src.services.rag.embedding_service import embedding_service

        dependencies["embedding"] = await embedding_service.healthcheck()
    except Exception as exc:
        dependencies["embedding"] = {"status": "DOWN", "error": str(exc)}

    overall = "UP" if all(item.get("status") == "UP" for item in dependencies.values()) else "DOWN"
    return {
        "status": overall,
        "service": "SmartHR Python AI 服务",
        "dependencies": dependencies,
    }


@router.get("/health/dependencies")
async def dependency_health_check() -> Dict[str, Any]:
    return await _dependency_health_check()


@router.get("/api/health/dependencies")
async def api_dependency_health_check() -> Dict[str, Any]:
    """兼容 Nginx /python/ 路由重写后的依赖健康检查路径。"""
    return await _dependency_health_check()
