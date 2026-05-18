# SmartHR Python Service Configuration

import os
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Application
    app_name: str = "SmartHR Python AI Service"
    debug: bool = True
    host: str = "0.0.0.0"
    port: int = 8001

    # LLM Configuration - Unified Interface
    llm_provider: str = "deepseek"  # deepseek, openai, anthropic
    deepseek_api_key: str = os.getenv("DEEPSEEK_API_KEY", "")
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"

    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_base_url: str = "https://api.openai.com"
    openai_model: str = "gpt-4-turbo-preview"

    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    anthropic_model: str = "claude-3-sonnet-20240229"

    # Chroma Vector Store
    chroma_host: str = "localhost"
    chroma_port: int = 8000
    chroma_persist_directory: str = "./chroma_data"

    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0

    # Java Backend (for callback)
    java_backend_url: str = "http://localhost:8080"

    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()