from __future__ import annotations

from datetime import datetime, timedelta, timezone

from celery.utils.log import get_task_logger

from vak_bot.config import get_settings
from vak_bot.db.models import Brand, Post, TelegramSession
from vak_bot.db.session import SessionLocal
from vak_bot.enums import PostStatus
from vak_bot.pipeline.orchestrator import (
    notify_token_expiry,
    purge_old_reference_images,
    run_caption_rewrite,
    run_generation_pipeline,
    run_publish,
    run_reel_this_conversion,
    run_video_extension,
    run_video_generation_pipeline,
)
from vak_bot.pipeline.poster import MetaGraphPoster
from vak_bot.services.credentials_service import update_brand_meta_token
from vak_bot.storage import R2StorageClient
from vak_bot.workers.celery_app import celery_app

logger = get_task_logger(__name__)
settings = get_settings()


@celery_app.task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 2})
def process_post_task(self, post_id: int, chat_id: int, brand_id: int | None = None) -> None:
    logger.info("process_post_task_start post_id=%s brand_id=%s", post_id, brand_id)
    run_generation_pipeline(post_id=post_id, chat_id=chat_id, brand_id=brand_id)


@celery_app.task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 2})
def rewrite_caption_task(self, post_id: int, chat_id: int, instruction: str, brand_id: int | None = None) -> None:
    logger.info("rewrite_caption_task_start post_id=%s brand_id=%s", post_id, brand_id)
    run_caption_rewrite(post_id=post_id, chat_id=chat_id, rewrite_instruction=instruction, brand_id=brand_id)


@celery_app.task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 2})
def publish_post_task(self, post_id: int, chat_id: int, posted_by: str, brand_id: int | None = None) -> None:
    resolved_brand_id = brand_id
    if resolved_brand_id is None:
        with SessionLocal() as db:
            post = db.get(Post, post_id)
            if post:
                resolved_brand_id = post.brand_id
    logger.info("publish_post_task_start post_id=%s brand_id=%s", post_id, resolved_brand_id)
    poster = MetaGraphPoster(brand_id=resolved_brand_id)
    run_publish(
        post_id=post_id,
        chat_id=chat_id,
        posted_by=posted_by,
        brand_id=resolved_brand_id,
        poster_client=poster,
    )


@celery_app.task
def refresh_meta_token_task() -> None:
    with SessionLocal() as db:
        brands = db.query(Brand).all()

    for brand in brands:
        poster = MetaGraphPoster(brand_id=brand.id)
        try:
            result = poster.refresh_page_token()
            logger.info("meta_token_refresh_result brand_id=%s result=%s", brand.id, result)
        except Exception as exc:
            logger.warning("meta_token_refresh_failed brand_id=%s error=%s", brand.id, exc)
            continue

        token_value = str(result.get("access_token") or "").strip()
        expires_in_raw = result.get("expires_in")
        expires_at = None
        if expires_in_raw is not None:
            try:
                expires_at = datetime.now(timezone.utc) + timedelta(seconds=int(expires_in_raw))
            except Exception:
                expires_at = None

        if token_value:
            try:
                with SessionLocal() as db:
                    update_brand_meta_token(
                        db,
                        brand_id=brand.id,
                        access_token=token_value,
                        expires_at=expires_at,
                    )
            except Exception as exc:
                logger.warning("meta_token_persist_failed brand_id=%s error=%s", brand.id, exc)

        if not expires_at or not settings.founder_telegram_chat_id:
            continue

        if expires_at - datetime.now(timezone.utc) <= timedelta(days=7):
            notify_token_expiry(settings.founder_telegram_chat_id, expires_at.isoformat(), brand_id=brand.id)


@celery_app.task
def cleanup_reference_images_task() -> int:
    storage = R2StorageClient()
    deleted = purge_old_reference_images(days=30, storage_client=storage)
    logger.info("cleanup_reference_images deleted=%s", deleted)
    return deleted


@celery_app.task
def dispatch_scheduled_posts_task() -> int:
    now = datetime.now(timezone.utc)
    queued = 0

    with SessionLocal() as db:
        rows = (
            db.query(Post)
            .filter(
                Post.status == PostStatus.SCHEDULED.value,
                Post.scheduled_for.is_not(None),
                Post.scheduled_for <= now,
            )
            .order_by(Post.scheduled_for.asc())
            .limit(200)
            .all()
        )

        for post in rows:
            session = (
                db.query(TelegramSession)
                .filter(TelegramSession.post_id == post.id, TelegramSession.brand_id == post.brand_id)
                .order_by(TelegramSession.updated_at.desc())
                .first()
            )
            chat_id = int(session.chat_id) if session else 0
            post.status = PostStatus.APPROVED.value
            db.commit()
            publish_post_task.delay(post.id, chat_id, post.posted_by or "scheduler", post.brand_id)
            queued += 1

    return queued


@celery_app.task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 2})
def process_video_post_task(self, post_id: int, chat_id: int, brand_id: int | None = None) -> None:
    logger.info("process_video_post_task_start post_id=%s brand_id=%s", post_id, brand_id)
    run_video_generation_pipeline(post_id=post_id, chat_id=chat_id, brand_id=brand_id)


@celery_app.task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 2})
def extend_video_task(self, post_id: int, chat_id: int, video_variation: int = 1, brand_id: int | None = None) -> None:
    logger.info("extend_video_task_start post_id=%s variation=%s brand_id=%s", post_id, video_variation, brand_id)
    run_video_extension(post_id=post_id, chat_id=chat_id, video_variation=video_variation, brand_id=brand_id)


@celery_app.task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 2})
def reel_this_task(self, post_id: int, chat_id: int, brand_id: int | None = None) -> None:
    logger.info("reel_this_task_start post_id=%s brand_id=%s", post_id, brand_id)
    run_reel_this_conversion(post_id=post_id, chat_id=chat_id, brand_id=brand_id)
