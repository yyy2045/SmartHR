"""
SmartHR Python AI Service - FastAPI Entry Point
Multi-Agent Recruitment Platform
"""

import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api import health, resume, interview, knowledge

from src.config import settings

app = FastAPI(
    title=settings.app_name,
    description="AI Service for SmartHR Multi-Agent Recruitment Platform",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(resume.router, tags=["Resume"])
app.include_router(interview.router, tags=["Interview"])
app.include_router(knowledge.router, prefix="/api/knowledge", tags=["Knowledge"])

@app.get("/")
async def root():
    return {
        "service": "SmartHR Python AI Service",
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