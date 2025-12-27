"""Health check endpoint."""

from fastapi import APIRouter
from pydantic import BaseModel

from backend.utils.config import get_settings, get_config

router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    setup_complete: bool


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Check application health status."""
    settings = get_settings()
    config = get_config()
    
    return HealthResponse(
        status="healthy",
        version=settings.app_version,
        setup_complete=config.setup_complete,
    )
