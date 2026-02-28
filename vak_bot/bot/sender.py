from __future__ import annotations

import asyncio

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto

from vak_bot.bot.callbacks import make_callback
from vak_bot.bot.runtime import get_bot_for_brand
from vak_bot.enums import CallbackAction


def _run(coro):
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(asyncio.run, coro)
            return future.result(timeout=120)
    return asyncio.run(coro)


def _choice_buttons(post_id: int, option_count: int, action: CallbackAction) -> list[InlineKeyboardButton]:
    capped = max(1, min(3, option_count))
    return [
        InlineKeyboardButton(text=str(idx), callback_data=make_callback(post_id, idx, action))
        for idx in range(1, capped + 1)
    ]


def build_review_keyboard(post_id: int, option_count: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            _choice_buttons(post_id, option_count, CallbackAction.SELECT),
            [
                InlineKeyboardButton(
                    text="Edit Caption",
                    callback_data=make_callback(post_id, 0, CallbackAction.EDIT_CAPTION),
                ),
                InlineKeyboardButton(text="Redo", callback_data=make_callback(post_id, 0, CallbackAction.REDO)),
            ],
            [
                InlineKeyboardButton(text="Approve", callback_data=make_callback(post_id, 0, CallbackAction.APPROVE)),
                InlineKeyboardButton(text="Cancel", callback_data=make_callback(post_id, 0, CallbackAction.CANCEL)),
            ],
        ]
    )


async def _send_text_async(brand_id: int | None, chat_id: int, text: str) -> None:
    bot = get_bot_for_brand(brand_id)
    await bot.send_message(chat_id=chat_id, text=text)


def send_text(brand_id: int | None, chat_id: int, text: str) -> None:
    _run(_send_text_async(brand_id, chat_id, text))


async def _send_review_async(brand_id: int | None, chat_id: int, post_id: int, image_urls: list[str], caption: str, hashtags: str) -> None:
    bot = get_bot_for_brand(brand_id)
    media = [InputMediaPhoto(media=url) for url in image_urls[:3] if url]
    option_count = len(media)
    if media:
        await bot.send_media_group(chat_id=chat_id, media=media)
    else:
        option_count = 1

    message = (
        "Here are your options for this post:\n\n"
        f"Caption:\n\"{caption}\"\n\n"
        f"Hashtags:\n{hashtags}\n\n"
        f"Reply with 1-{option_count}; or use the buttons below."
    )
    await bot.send_message(chat_id=chat_id, text=message, reply_markup=build_review_keyboard(post_id, option_count))


def send_review_package(brand_id: int | None, chat_id: int, post_id: int, image_urls: list[str], caption: str, hashtags: str) -> None:
    _run(_send_review_async(brand_id, chat_id, post_id, image_urls, caption, hashtags))


def build_video_review_keyboard(post_id: int, option_count: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            _choice_buttons(post_id, option_count, CallbackAction.SELECT_VIDEO),
            [
                InlineKeyboardButton(text="Extend", callback_data=make_callback(post_id, 0, CallbackAction.EXTEND)),
                InlineKeyboardButton(
                    text="Edit Caption",
                    callback_data=make_callback(post_id, 0, CallbackAction.EDIT_CAPTION),
                ),
            ],
            [
                InlineKeyboardButton(text="Redo", callback_data=make_callback(post_id, 0, CallbackAction.REDO)),
                InlineKeyboardButton(text="Approve", callback_data=make_callback(post_id, 0, CallbackAction.APPROVE)),
                InlineKeyboardButton(text="Cancel", callback_data=make_callback(post_id, 0, CallbackAction.CANCEL)),
            ],
        ]
    )


async def _send_video_review_async(
    brand_id: int | None,
    chat_id: int,
    post_id: int,
    video_urls: list[str],
    start_frame_url: str,
    caption: str,
    hashtags: str,
) -> None:
    bot = get_bot_for_brand(brand_id)
    option_count = max(1, min(3, len(video_urls)))

    if start_frame_url:
        await bot.send_photo(chat_id=chat_id, photo=start_frame_url, caption="Start frame")

    for idx, url in enumerate(video_urls[:3], start=1):
        await bot.send_video(chat_id=chat_id, video=url, caption=f"Option {idx}")

    message = (
        "Here is your Reel preview:\n\n"
        f'Caption:\n"{caption}"\n\n'
        f"Hashtags:\n{hashtags}\n\n"
        f"Reply with 1-{option_count} to select, or use the buttons below."
    )
    await bot.send_message(chat_id=chat_id, text=message, reply_markup=build_video_review_keyboard(post_id, option_count))


def send_video_review_package(
    brand_id: int | None,
    chat_id: int,
    post_id: int,
    video_urls: list[str],
    start_frame_url: str,
    caption: str,
    hashtags: str,
) -> None:
    _run(_send_video_review_async(brand_id, chat_id, post_id, video_urls, start_frame_url, caption, hashtags))
