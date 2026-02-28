from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from vak_bot.api import router as api_router
from vak_bot.config import get_settings
from vak_bot.config.logging import configure_logging
from vak_bot.db.session import SessionLocal
from vak_bot.db.tenant import get_or_create_default_brand

settings = get_settings()
configure_logging(settings.log_level)

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.on_event("startup")
async def startup_checks() -> None:
    try:
        with SessionLocal() as db:
            get_or_create_default_brand(db)
    except Exception:
        # Schema may not be migrated yet; keep app booting for health/debug endpoints.
        return
