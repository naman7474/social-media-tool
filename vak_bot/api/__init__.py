from fastapi import APIRouter

from vak_bot.api.admin_routes import router as admin_router
from vak_bot.api.routes import router as public_router

router = APIRouter()
router.include_router(public_router)
router.include_router(admin_router)

__all__ = ["router"]
