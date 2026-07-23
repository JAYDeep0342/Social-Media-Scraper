"""Health check endpoint. Reports liveness plus basic environment info."""

from fastapi import APIRouter

from app.config.settings import get_settings
from app.schemas.response import APIResponse

router = APIRouter()


@router.get("/health", response_model=APIResponse[dict], tags=["health"])
async def health_check() -> APIResponse[dict]:
    settings = get_settings()
    return APIResponse.ok(
        data={"status": "healthy", "environment": settings.ENV, "version": settings.APP_VERSION},
        message="Service is running",
    )
