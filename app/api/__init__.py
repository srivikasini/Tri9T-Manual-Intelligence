"""API package initialization and router aggregation."""
from fastapi import APIRouter

from app.api.documents import router as documents_router
from app.api.diff import router as diff_router
from app.api.selections import router as selections_router
from app.api.qa import router as qa_router
from app.api.staleness import router as staleness_router
from app.api.ingest import router as ingest_router

api_router = APIRouter()

api_router.include_router(ingest_router)
api_router.include_router(documents_router)
api_router.include_router(diff_router)
api_router.include_router(selections_router)
api_router.include_router(qa_router)
api_router.include_router(staleness_router)

__all__ = ["api_router"]
