"""
SmartHR Python AI 服务 - FastAPI 入口
多智能体招聘平台
"""

import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api import health, resume, interview, knowledge, job, rag

from src.config import settings

app = FastAPI(
    title=settings.app_name,
    description="SmartHR 多智能体招聘平台 AI 服务",
    version="1.0.0"
)

# CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(health.router, tags=["健康检查"])
app.include_router(resume.router, tags=["简历"])
app.include_router(interview.router, tags=["面试"])
app.include_router(knowledge.router, prefix="/api/knowledge", tags=["知识库"])
app.include_router(job.router, tags=["岗位"])
app.include_router(rag.router)

@app.get("/")
async def root():
    return {
        "service": "SmartHR Python AI 服务",
        "version": "1.0.0",
        "status": "running"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
