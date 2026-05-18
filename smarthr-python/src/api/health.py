"""
Health Check API
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict

router = APIRouter()

class HealthResponse(BaseModel):
    status: str
    service: str

@router.get("/health")
async def health_check() -> HealthResponse:
    return HealthResponse(
        status="UP",
        service="SmartHR Python AI Service"
    )