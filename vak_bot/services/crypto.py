from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet

from vak_bot.config import get_settings


def _materialize_key(raw_key: str) -> bytes:
    raw = (raw_key or "").strip()
    if raw:
        try:
            # Already a Fernet key
            Fernet(raw.encode("utf-8"))
            return raw.encode("utf-8")
        except Exception:
            pass

    settings = get_settings()
    seed = raw or (settings.admin_session_secret or "").strip()
    if not seed:
        if settings.app_env.lower() in {"production", "staging"}:
            raise RuntimeError("CREDENTIAL_ENCRYPTION_KEY (or ADMIN_SESSION_SECRET) must be set in production/staging")
        seed = "credential-dev-secret"
    digest = hashlib.sha256(seed.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


def get_fernet() -> Fernet:
    settings = get_settings()
    return Fernet(_materialize_key(settings.credential_encryption_key))


def encrypt_text(value: str | None) -> str | None:
    if value is None:
        return None
    return get_fernet().encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_text(value: str | None) -> str | None:
    if value is None:
        return None
    return get_fernet().decrypt(value.encode("utf-8")).decode("utf-8")
