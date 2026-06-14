# SmartHR Python 服务配置

import os
from pydantic_settings import BaseSettings
from typing import Optional


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class Settings(BaseSettings):
    # 应用配置
    app_name: str = "SmartHR Python AI 服务"
    environment: str = os.getenv("ENVIRONMENT", "development")
    debug: bool = env_bool("DEBUG", os.getenv("ENVIRONMENT", "development").lower() != "production")
    host: str = "0.0.0.0"
    port: int = 8001

    # LLM 配置 - 统一接口
    llm_provider: str = os.getenv("LLM_PROVIDER", "deepseek")
    deepseek_api_key: str = os.getenv("DEEPSEEK_API_KEY", "")
    deepseek_base_url: str = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    deepseek_model: str = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_base_url: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4-turbo-preview")

    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    anthropic_model: str = os.getenv("ANTHROPIC_MODEL", "claude-3-sonnet-20240229")

    # Embedding / rerank 配置。生产演示必须使用本地 BGE，mock 仅允许开发模式显式启用。
    embedding_provider: str = os.getenv("EMBEDDING_PROVIDER", "mock")
    embedding_api_key: str = os.getenv("EMBEDDING_API_KEY", "")
    embedding_base_url: str = os.getenv("EMBEDDING_BASE_URL", "")
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "bge-base-zh-v1.5")
    embedding_dimensions: int = int(os.getenv("EMBEDDING_DIMENSIONS", "768"))
    local_bge_model_path: str = os.getenv("LOCAL_BGE_MODEL_PATH", "/opt/smarthr/models/bge-base-zh-v1.5")
    allow_mock_embedding: bool = env_bool(
        "ALLOW_MOCK_EMBEDDING",
        os.getenv("ENVIRONMENT", "development").lower() != "production",
    )
    rerank_provider: str = os.getenv("RERANK_PROVIDER", "hybrid")
    rerank_base_url: str = os.getenv("RERANK_BASE_URL", "")
    rerank_model: str = os.getenv("RERANK_MODEL", "bge-reranker-v2-m3")

    # RAG 评测配置。默认使用本地启发式评测；完整 RAGas 需要手动选择或设置 RAGAS_MODE=ragas。
    ragas_mode: str = os.getenv("RAGAS_MODE", "heuristic")
    ragas_threshold: float = float(os.getenv("RAGAS_THRESHOLD", "0.70"))
    ragas_llm_provider: str = os.getenv("RAGAS_LLM_PROVIDER", os.getenv("LLM_PROVIDER", "deepseek"))
    ragas_llm_api_key: str = os.getenv("RAGAS_LLM_API_KEY", "")
    ragas_llm_base_url: str = os.getenv("RAGAS_LLM_BASE_URL", "")
    ragas_llm_model: str = os.getenv("RAGAS_LLM_MODEL", "")
    ragas_timeout_seconds: float = float(os.getenv("RAGAS_TIMEOUT_SECONDS", "120"))

    # 可选 MCP HTTP 网关配置；未启用时内部 tools/skills 继续工作
    mcp_enabled: bool = os.getenv("MCP_ENABLED", "false").lower() == "true"
    mcp_gateway_url: str = os.getenv("MCP_GATEWAY_URL", "")
    mcp_timeout_seconds: float = float(os.getenv("MCP_TIMEOUT_SECONDS", "3"))
    expose_internal_rag_tools: bool = env_bool("EXPOSE_INTERNAL_RAG_TOOLS", False)

    # Chroma 向量数据库
    chroma_host: str = os.getenv("CHROMA_HOST", "localhost")
    chroma_port: int = int(os.getenv("CHROMA_PORT", "8000"))
    chroma_persist_directory: str = os.getenv("CHROMA_PERSIST_DIR", "./chroma_data")

    # Redis 配置
    redis_host: str = os.getenv("REDIS_HOST", "localhost")
    redis_port: int = int(os.getenv("REDIS_PORT", "6379"))
    redis_db: int = int(os.getenv("REDIS_DB", "0"))

    # Java 后端回调地址
    java_backend_url: str = os.getenv("JAVA_BACKEND_URL", "http://localhost:8080")

    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()
