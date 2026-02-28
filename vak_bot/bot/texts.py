from __future__ import annotations

from dataclasses import dataclass

from vak_bot.pipeline.prompts import load_brand_profile


@dataclass(frozen=True)
class BotTextBundle:
    unauthorized_message: str
    welcome_message: str
    help_message: str
    processing_message: str
    need_photo_message: str
    unsupported_link_message: str
    v1_scheduling_message: str
    reel_detected_message: str
    video_processing_message: str
    video_extending_message: str


_UNAUTHORIZED_TEMPLATE = "This bot is private for {brand_name}. Visit {brand_website} to shop."
_WELCOME_TEMPLATE = (
    "Welcome to the {brand_name} posting bot.\n\n"
    "Send an Instagram/Pinterest inspiration link with product photo(s), or send a link + product code (e.g. SKU-042)."
)
_HELP_TEMPLATE = (
    "How to use:\n"
    "1) Send inspiration link + product photo(s)\n"
    "2) Or send link + product code (SKU-042)\n"
    "3) Review options and reply: 1/2/3, edit caption, redo, redo close-up, redo product-motion, redo detail-zoom, approve, cancel\n"
    "4) After approve, reply post now or schedule <datetime>\n\n"
    "Commands:\n"
    "/reel <link> [SKU-XXX] (force reel mode)\n"
    "/recent, /queue, /reelqueue\n"
    "/products, /stats, /cancel <post_id>\n\n"
    "Scheduling is enabled. Example: schedule 2026-03-10 18:30"
)

_PROCESSING_MESSAGE = (
    "Got it! Analyzing the reference post and styling your product.\n"
    "This usually takes 2-3 minutes. I'll send you options when ready."
)

_NEED_PHOTO_MESSAGE = "Got the inspiration! Now send me the product photo(s) you want to feature."
_UNSUPPORTED_LINK_MESSAGE = "I work best with Instagram and Pinterest links. Can you send one of those?"
_V1_SCHEDULING_MESSAGE = "Send: schedule 2026-03-10 18:30 (UTC) to queue publishing."

_REEL_DETECTED_MESSAGE = (
    "That's a Reel. I'll create a video version of your product.\n"
    "This takes ~5 minutes (styling + video generation). I'll send preview options when ready."
)

_VIDEO_PROCESSING_MESSAGE = (
    "Styling the start frame first, then animating with Veo 3.1.\n"
    "This usually takes 4-6 minutes. I'll send you a video preview."
)

_VIDEO_EXTENDING_MESSAGE = "Extending video by 8 seconds. This takes ~3 minutes..."


def _brand_text_context(brand_id: int | None) -> dict[str, str]:
    profile = load_brand_profile(brand_id)
    brand_name = (profile.get("brand_name") or "").strip() or "this brand"
    brand_website = (
        (profile.get("brand_website") or "").strip()
        or (profile.get("brand_instagram") or "").strip()
        or "our website"
    )
    return {
        "brand_name": brand_name,
        "brand_website": brand_website,
    }


def load_bot_texts(brand_id: int | None) -> BotTextBundle:
    context = _brand_text_context(brand_id)
    return BotTextBundle(
        unauthorized_message=_UNAUTHORIZED_TEMPLATE.format(**context),
        welcome_message=_WELCOME_TEMPLATE.format(**context),
        help_message=_HELP_TEMPLATE.format(**context),
        processing_message=_PROCESSING_MESSAGE,
        need_photo_message=_NEED_PHOTO_MESSAGE,
        unsupported_link_message=_UNSUPPORTED_LINK_MESSAGE,
        v1_scheduling_message=_V1_SCHEDULING_MESSAGE,
        reel_detected_message=_REEL_DETECTED_MESSAGE,
        video_processing_message=_VIDEO_PROCESSING_MESSAGE,
        video_extending_message=_VIDEO_EXTENDING_MESSAGE,
    )
