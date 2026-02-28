from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session

from vak_bot.db.models import BrandCredential
from vak_bot.services.crypto import decrypt_text, encrypt_text


@dataclass
class ResolvedMetaCredentials:
    meta_app_id: str
    meta_app_secret: str
    meta_page_access_token: str
    instagram_business_account_id: str
    meta_graph_api_version: str


def upsert_brand_credentials(
    db: Session,
    *,
    brand_id: int,
    meta_app_id: str,
    meta_app_secret: str,
    meta_page_access_token: str,
    instagram_business_account_id: str,
    meta_graph_api_version: str = "v25.0",
    meta_token_expires_at: datetime | None = None,
) -> BrandCredential:
    record = db.query(BrandCredential).filter(BrandCredential.brand_id == brand_id).first()
    if record is None:
        record = BrandCredential(brand_id=brand_id)
        db.add(record)

    record.meta_app_id = meta_app_id
    record.encrypted_meta_app_secret = encrypt_text(meta_app_secret)
    record.encrypted_meta_page_access_token = encrypt_text(meta_page_access_token)
    record.instagram_business_account_id = instagram_business_account_id
    record.meta_graph_api_version = meta_graph_api_version
    record.meta_token_expires_at = meta_token_expires_at

    db.commit()
    db.refresh(record)
    return record


def resolve_meta_credentials(db: Session, brand_id: int) -> ResolvedMetaCredentials | None:
    record = db.query(BrandCredential).filter(BrandCredential.brand_id == brand_id).first()
    if record is None:
        return None

    return ResolvedMetaCredentials(
        meta_app_id=record.meta_app_id or "",
        meta_app_secret=decrypt_text(record.encrypted_meta_app_secret) or "",
        meta_page_access_token=decrypt_text(record.encrypted_meta_page_access_token) or "",
        instagram_business_account_id=record.instagram_business_account_id or "",
        meta_graph_api_version=record.meta_graph_api_version,
    )


def update_brand_meta_token(
    db: Session,
    *,
    brand_id: int,
    access_token: str,
    expires_at: datetime | None,
) -> BrandCredential | None:
    record = db.query(BrandCredential).filter(BrandCredential.brand_id == brand_id).first()
    if record is None:
        return None

    record.encrypted_meta_page_access_token = encrypt_text(access_token)
    record.meta_token_expires_at = expires_at
    db.commit()
    db.refresh(record)
    return record
