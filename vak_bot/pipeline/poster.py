from __future__ import annotations

import httpx
import structlog

from vak_bot.config import get_settings
from vak_bot.db.session import SessionLocal
from vak_bot.pipeline.errors import PublishCredentialsError, PublishError
from vak_bot.services.credentials_service import resolve_meta_credentials

logger = structlog.get_logger(__name__)


class MetaGraphPoster:
    def __init__(self, brand_id: int | None = None) -> None:
        self.settings = get_settings()
        self.brand_id = brand_id

    def _resolved(self) -> dict:
        if self.brand_id is None:
            raise PublishCredentialsError(
                "Publishing requires a brand_id and brand-specific Meta credentials. "
                "Run this publish via a brand-scoped workflow."
            )

        with SessionLocal() as db:
            creds = resolve_meta_credentials(db, self.brand_id)
        if not creds:
            raise PublishCredentialsError(
                f"Meta credentials are not configured for brand_id={self.brand_id}. "
                "Set brand-specific Meta credentials before publishing."
            )

        resolved = {
            "meta_app_id": creds.meta_app_id,
            "meta_app_secret": creds.meta_app_secret,
            "meta_page_access_token": creds.meta_page_access_token,
            "instagram_business_account_id": creds.instagram_business_account_id,
            "meta_graph_api_version": creds.meta_graph_api_version,
        }
        missing = [key for key, value in resolved.items() if not value]
        if missing:
            raise PublishCredentialsError(
                f"Incomplete Meta credentials for brand_id={self.brand_id}. Missing: {', '.join(missing)}."
            )
        return resolved

    @property
    def _base(self) -> str:
        resolved = self._resolved()
        if not resolved.get("meta_graph_api_version"):
            raise PublishCredentialsError("Missing Meta Graph API version")
        return f"https://graph.facebook.com/{resolved['meta_graph_api_version']}"

    def _params(self) -> dict:
        resolved = self._resolved()
        if not resolved.get("meta_page_access_token"):
            raise PublishCredentialsError("Missing META_PAGE_ACCESS_TOKEN")
        return {"access_token": resolved["meta_page_access_token"]}

    def _ig_user_id(self) -> str:
        ig_user_id = self._resolved().get("instagram_business_account_id")
        if not ig_user_id:
            raise PublishCredentialsError("Missing INSTAGRAM_BUSINESS_ACCOUNT_ID")
        return ig_user_id

    def post_single_image(self, image_url: str, caption: str, alt_text: str, idempotency_key: str) -> dict:
        if self.settings.dry_run:
            return {
                "id": f"dryrun_{idempotency_key}",
                "permalink": f"https://instagram.com/p/{idempotency_key}",
            }

        try:
            ig_user_id = self._ig_user_id()
            with httpx.Client(timeout=60.0) as client:
                create_resp = client.post(
                    f"{self._base}/{ig_user_id}/media",
                    params=self._params(),
                    data={
                        "image_url": image_url,
                        "caption": caption,
                        "alt_text": alt_text,
                    },
                )
                create_resp.raise_for_status()
                container_id = create_resp.json()["id"]

                publish_resp = client.post(
                    f"{self._base}/{ig_user_id}/media_publish",
                    params=self._params(),
                    data={"creation_id": container_id},
                )
                publish_resp.raise_for_status()
                media_id = publish_resp.json()["id"]

                permalink_resp = client.get(
                    f"{self._base}/{media_id}",
                    params={**self._params(), "fields": "permalink"},
                )
                permalink_resp.raise_for_status()
                permalink = permalink_resp.json().get("permalink", "")

            return {"id": media_id, "permalink": permalink}
        except httpx.HTTPStatusError as exc:
            body = exc.response.text[:600] if exc.response is not None else ""
            logger.error(
                "meta_publish_http_error",
                method="single_image",
                status_code=exc.response.status_code if exc.response is not None else None,
                body=body,
                brand_id=self.brand_id,
            )
            raise PublishError(f"{exc} | {body}") from exc
        except Exception as exc:
            raise PublishError(str(exc)) from exc

    def post_carousel(self, image_urls: list[str], caption: str, alt_text: str, idempotency_key: str) -> dict:
        if self.settings.dry_run:
            return {
                "id": f"dryrun_{idempotency_key}",
                "permalink": f"https://instagram.com/p/{idempotency_key}",
            }

        try:
            children_ids: list[str] = []
            ig_user_id = self._ig_user_id()
            with httpx.Client(timeout=60.0) as client:
                for idx, image_url in enumerate(image_urls, start=1):
                    logger.info("meta_carousel_child_create", position=idx, total=len(image_urls), brand_id=self.brand_id)
                    media_resp = client.post(
                        f"{self._base}/{ig_user_id}/media",
                        params=self._params(),
                        data={"image_url": image_url, "is_carousel_item": "true"},
                    )
                    media_resp.raise_for_status()
                    children_ids.append(media_resp.json()["id"])

                logger.info("meta_carousel_container_create", children_count=len(children_ids), brand_id=self.brand_id)
                carousel_resp = client.post(
                    f"{self._base}/{ig_user_id}/media",
                    params=self._params(),
                    data={
                        "media_type": "CAROUSEL",
                        "children": ",".join(children_ids),
                        "caption": caption,
                    },
                )
                carousel_resp.raise_for_status()
                container_id = carousel_resp.json()["id"]

                publish_resp = client.post(
                    f"{self._base}/{ig_user_id}/media_publish",
                    params=self._params(),
                    data={"creation_id": container_id},
                )
                publish_resp.raise_for_status()
                media_id = publish_resp.json()["id"]

                permalink_resp = client.get(
                    f"{self._base}/{media_id}",
                    params={**self._params(), "fields": "permalink"},
                )
                permalink_resp.raise_for_status()
                permalink = permalink_resp.json().get("permalink", "")

            return {"id": media_id, "permalink": permalink}
        except httpx.HTTPStatusError as exc:
            body = exc.response.text[:600] if exc.response is not None else ""
            logger.error(
                "meta_publish_http_error",
                method="carousel",
                status_code=exc.response.status_code if exc.response is not None else None,
                body=body,
                children_created=len(children_ids),
                brand_id=self.brand_id,
            )
            raise PublishError(f"{exc} | {body}") from exc
        except Exception as exc:
            raise PublishError(str(exc)) from exc

    def post_reel(
        self,
        video_s3_url: str,
        caption: str,
        thumb_offset_ms: int = 0,
        share_to_feed: bool = True,
    ) -> dict:
        if self.settings.dry_run:
            return {
                "id": f"dryrun_reel_{thumb_offset_ms}",
                "permalink": "https://instagram.com/reel/dryrun",
            }

        ig_user_id = self._ig_user_id()

        try:
            with httpx.Client(timeout=120.0) as client:
                container_resp = client.post(
                    f"{self._base}/{ig_user_id}/media",
                    params=self._params(),
                    data={
                        "media_type": "REELS",
                        "video_url": video_s3_url,
                        "caption": caption,
                        "share_to_feed": str(share_to_feed).lower(),
                        "thumb_offset": str(thumb_offset_ms),
                    },
                )
                container_resp.raise_for_status()
                container_id = container_resp.json()["id"]

                import time

                max_retries = 30
                for _ in range(max_retries):
                    status_resp = client.get(
                        f"{self._base}/{container_id}",
                        params={**self._params(), "fields": "status_code"},
                    )
                    status_resp.raise_for_status()
                    status = status_resp.json().get("status_code")

                    if status == "FINISHED":
                        break
                    if status == "ERROR":
                        raise PublishError("Instagram video processing failed")
                    time.sleep(10)

                publish_resp = client.post(
                    f"{self._base}/{ig_user_id}/media_publish",
                    params=self._params(),
                    data={"creation_id": container_id},
                )
                publish_resp.raise_for_status()
                media_id = publish_resp.json()["id"]

                permalink_resp = client.get(
                    f"{self._base}/{media_id}",
                    params={**self._params(), "fields": "permalink"},
                )
                permalink_resp.raise_for_status()
                permalink = permalink_resp.json().get("permalink", "")

            return {"id": media_id, "permalink": permalink}
        except httpx.HTTPStatusError as exc:
            body = exc.response.text[:600] if exc.response is not None else ""
            logger.error(
                "meta_publish_http_error",
                method="reel",
                status_code=exc.response.status_code if exc.response is not None else None,
                body=body,
                brand_id=self.brand_id,
            )
            raise PublishError(f"{exc} | {body}") from exc
        except Exception as exc:
            raise PublishError(str(exc)) from exc

    def refresh_page_token(self) -> dict:
        if self.settings.dry_run:
            return {"access_token": "dry-run-token", "expires_in": 60 * 24 * 3600}

        resolved = self._resolved()
        if not resolved["meta_page_access_token"]:
            raise PublishCredentialsError("Missing META_PAGE_ACCESS_TOKEN")

        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.get(
                    f"{self._base}/oauth/access_token",
                    params={
                        "grant_type": "fb_exchange_token",
                        "client_id": resolved["meta_app_id"],
                        "client_secret": resolved["meta_app_secret"],
                        "fb_exchange_token": resolved["meta_page_access_token"],
                    },
                )
                response.raise_for_status()
                return response.json()
        except Exception as exc:
            raise PublishError(str(exc)) from exc
