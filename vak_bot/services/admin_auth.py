from __future__ import annotations

import base64
import hmac
import os
import time
from hashlib import sha256

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from vak_bot.config import get_settings

_password_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return _password_hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _password_hasher.verify(password_hash, password)
    except VerifyMismatchError:
        return False


def _secret() -> bytes:
    settings = get_settings()
    value = (settings.admin_session_secret or "").strip()
    if not value:
        if settings.app_env.lower() in {"production", "staging"}:
            raise RuntimeError("ADMIN_SESSION_SECRET must be set in production/staging")
        value = "admin-dev-secret"
    return value.encode("utf-8")


def _sign(message: bytes) -> str:
    digest = hmac.new(_secret(), message, sha256).digest()
    return base64.urlsafe_b64encode(digest).decode("utf-8")


def create_session_token(user_id: int, ttl_seconds: int = 8 * 3600) -> str:
    expires = int(time.time()) + ttl_seconds
    nonce = base64.urlsafe_b64encode(os.urandom(12)).decode("utf-8")
    payload = f"{user_id}:{expires}:{nonce}".encode("utf-8")
    sig = _sign(payload)
    return base64.urlsafe_b64encode(payload).decode("utf-8") + "." + sig


def validate_session_token(token: str | None) -> int | None:
    if not token or "." not in token:
        return None
    payload_b64, signature = token.split(".", 1)
    try:
        payload = base64.urlsafe_b64decode(payload_b64.encode("utf-8"))
    except Exception:
        return None
    if not hmac.compare_digest(_sign(payload), signature):
        return None
    try:
        user_id_s, expires_s, _nonce = payload.decode("utf-8").split(":", 2)
        user_id = int(user_id_s)
        expires = int(expires_s)
    except Exception:
        return None
    if expires < int(time.time()):
        return None
    return user_id


def create_csrf_token(user_id: int) -> str:
    nonce = base64.urlsafe_b64encode(os.urandom(10)).decode("utf-8")
    payload = f"{user_id}:{nonce}".encode("utf-8")
    return base64.urlsafe_b64encode(payload).decode("utf-8") + "." + _sign(payload)


def validate_csrf_token(user_id: int, token: str | None) -> bool:
    if not token or "." not in token:
        return False
    payload_b64, signature = token.split(".", 1)
    try:
        payload = base64.urlsafe_b64decode(payload_b64.encode("utf-8"))
    except Exception:
        return False
    if not hmac.compare_digest(_sign(payload), signature):
        return False
    try:
        token_user_id = int(payload.decode("utf-8").split(":", 1)[0])
    except Exception:
        return False
    return token_user_id == user_id
