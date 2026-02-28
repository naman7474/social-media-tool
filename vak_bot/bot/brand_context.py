from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass


@dataclass(frozen=True)
class BotBrandContext:
    brand_id: int
    brand_slug: str


_current_context: ContextVar[BotBrandContext | None] = ContextVar("bot_brand_context", default=None)


def set_current_brand_context(context: BotBrandContext):
    return _current_context.set(context)


def reset_current_brand_context(token) -> None:
    _current_context.reset(token)


def get_current_brand_context() -> BotBrandContext | None:
    return _current_context.get()


def require_current_brand_context() -> BotBrandContext:
    context = get_current_brand_context()
    if context is None:
        raise RuntimeError("missing brand context")
    return context
