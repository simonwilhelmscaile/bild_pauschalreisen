"""Route modules — assembled into a single router."""
from fastapi import APIRouter

from .core import router as core_router
from .backfill import router as backfill_router
from .reports import router as reports_router
from .imports import router as imports_router

router = APIRouter(prefix="/social-listening", tags=["Social Listening"])
router.include_router(core_router)
router.include_router(backfill_router)
router.include_router(reports_router)
router.include_router(imports_router)

__all__ = ["router"]
