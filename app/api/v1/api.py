"""Aggregates all v1 endpoint routers into a single APIRouter."""

from fastapi import APIRouter

from app.api.v1.endpoints import health, search

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(search.router)
