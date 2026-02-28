from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from vak_bot.config import get_settings
from vak_bot.db.models import Brand


@dataclass(frozen=True)
class TenantContext:
    brand_id: int
    brand_slug: str


def parse_allowed_users_csv(raw: str | None) -> set[int]:
    if not raw:
        return set()
    allowed: set[int] = set()
    for value in raw.split(","):
        value = value.strip()
        if not value:
            continue
        try:
            allowed.add(int(value))
        except ValueError:
            continue
    return allowed


def get_or_create_default_brand(db: Session) -> Brand:
    settings = get_settings()
    brand = db.query(Brand).filter(Brand.slug == settings.default_brand_slug).first()
    if brand:
        return brand

    brand = Brand(
        slug=settings.default_brand_slug,
        name=settings.brand_name,
        timezone=settings.default_posting_timezone,
        telegram_bot_token=settings.telegram_bot_token or None,
        telegram_webhook_secret=settings.telegram_webhook_secret or None,
        allowed_user_ids=settings.allowed_user_ids or None,
    )
    db.add(brand)
    db.commit()
    db.refresh(brand)
    return brand


def get_brand_by_slug(db: Session, slug: str) -> Brand | None:
    return db.query(Brand).filter(Brand.slug == slug).first()


def require_brand_by_slug(db: Session, slug: str) -> Brand:
    brand = get_brand_by_slug(db, slug)
    if brand is None:
        raise ValueError(f"brand_not_found:{slug}")
    return brand


def assert_brand_scope(resource_brand_id: int, brand_id: int) -> None:
    if resource_brand_id != brand_id:
        raise PermissionError("brand_scope_violation")
