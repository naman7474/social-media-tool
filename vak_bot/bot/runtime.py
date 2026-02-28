from __future__ import annotations

from aiogram import Bot, Dispatcher

from vak_bot.config import get_settings
from vak_bot.db.models import Brand
from vak_bot.db.session import SessionLocal
from vak_bot.db.tenant import get_or_create_default_brand

settings = get_settings()
_dispatcher: Dispatcher | None = None


def _get_dispatcher() -> Dispatcher:
    global _dispatcher
    if _dispatcher is None:
        from vak_bot.bot.handlers import register_handlers
        _dispatcher = Dispatcher()
        register_handlers(_dispatcher)
    return _dispatcher

_bot_cache: dict[tuple[int, str], Bot] = {}


def get_dispatcher() -> Dispatcher:
    return _get_dispatcher()


def _fallback_token() -> str:
    if not settings.telegram_bot_token:
        raise RuntimeError("telegram bot token is missing")
    return settings.telegram_bot_token


def _resolve_brand_id(brand_id: int | None) -> int:
    if brand_id is not None:
        return brand_id
    try:
        with SessionLocal() as db:
            return get_or_create_default_brand(db).id
    except Exception:
        return 0


def get_brand_bot_token(brand_id: int | None) -> str:
    explicit_brand_id = brand_id
    brand_id = _resolve_brand_id(brand_id)
    try:
        with SessionLocal() as db:
            brand = db.get(Brand, brand_id)
            if brand and brand.telegram_bot_token:
                return brand.telegram_bot_token
    except Exception:
        pass
    if explicit_brand_id is not None:
        raise RuntimeError(f"telegram bot token is not configured for brand_id={explicit_brand_id}")
    return _fallback_token()


def get_bot_for_brand(brand_id: int | None) -> Bot:
    brand_id = _resolve_brand_id(brand_id)
    token = get_brand_bot_token(brand_id)
    cache_key = (brand_id, token)
    bot = _bot_cache.get(cache_key)
    if bot is not None:
        return bot
    bot = Bot(token=token)
    _bot_cache[cache_key] = bot
    return bot
