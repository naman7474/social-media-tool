from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException, Request

from aiogram.types import Update

from vak_bot.bot.brand_context import BotBrandContext, reset_current_brand_context, set_current_brand_context
from vak_bot.bot.runtime import get_bot_for_brand, get_dispatcher
from vak_bot.config import get_settings
from vak_bot.db.models import Brand
from vak_bot.db.session import SessionLocal
from vak_bot.db.tenant import get_or_create_default_brand

router = APIRouter()
settings = get_settings()


def _resolve_webhook_secret(brand: Brand) -> str | None:
    if brand.telegram_webhook_secret:
        return brand.telegram_webhook_secret
    return settings.telegram_webhook_secret or None


async def _feed_update_for_brand(brand: Brand, payload: dict) -> None:
    bot = get_bot_for_brand(brand.id)
    update = Update.model_validate(payload)
    dispatcher = get_dispatcher()
    token = set_current_brand_context(BotBrandContext(brand_id=brand.id, brand_slug=brand.slug))
    try:
        await dispatcher.feed_update(bot, update)
    finally:
        reset_current_brand_context(token)


@router.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": settings.app_name}


@router.post("/webhooks/telegram/{brand_slug}")
async def telegram_webhook_by_brand(
    brand_slug: str,
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
) -> dict:
    try:
        with SessionLocal() as db:
            brand = db.query(Brand).filter(Brand.slug == brand_slug).first()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"database not ready: {exc}") from exc

    if not brand:
        raise HTTPException(status_code=404, detail="brand not found")

    expected_secret = _resolve_webhook_secret(brand)
    if expected_secret and x_telegram_bot_api_secret_token != expected_secret:
        raise HTTPException(status_code=401, detail="invalid webhook secret")

    payload = await request.json()
    await _feed_update_for_brand(brand, payload)
    return {"ok": True, "brand": brand.slug}


@router.post("/webhooks/telegram")
async def telegram_webhook_legacy(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
) -> dict:
    try:
        with SessionLocal() as db:
            brand = get_or_create_default_brand(db)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"database not ready: {exc}") from exc

    expected_secret = _resolve_webhook_secret(brand)
    if expected_secret and x_telegram_bot_api_secret_token != expected_secret:
        raise HTTPException(status_code=401, detail="invalid webhook secret")

    payload = await request.json()
    await _feed_update_for_brand(brand, payload)
    return {"ok": True, "brand": brand.slug, "legacy": True}
