from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = Field(default="development", alias="APP_ENV")
    app_name: str = Field(default="social-media-bot", alias="APP_NAME")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    dry_run: bool = Field(default=True, alias="DRY_RUN")
    default_posting_timezone: str = Field(default="Asia/Kolkata", alias="DEFAULT_POSTING_TIMEZONE")

    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    api_base_url: str = Field(default="http://localhost:8000", alias="API_BASE_URL")
    frontend_base_url: str = Field(default="http://localhost:3000", alias="FRONTEND_BASE_URL")
    cors_allowed_origins: str = Field(default="http://localhost:3000,http://127.0.0.1:3000", alias="CORS_ALLOWED_ORIGINS")
    telegram_webhook_secret: str = Field(default="", alias="TELEGRAM_WEBHOOK_SECRET")

    telegram_bot_token: str = Field(default="", alias="TELEGRAM_BOT_TOKEN")
    allowed_user_ids: str = Field(default="", alias="ALLOWED_USER_IDS")
    founder_telegram_chat_id: Optional[int] = Field(default=None, alias="FOUNDER_TELEGRAM_CHAT_ID")
    default_brand_slug: str = Field(default="default", alias="DEFAULT_BRAND_SLUG")

    databright_api_key: str = Field(default="", alias="DATABRIGHT_API_KEY")
    databright_base_url: str = Field(default="https://api.brightdata.com", alias="DATABRIGHT_BASE_URL")

    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-5-mini", alias="OPENAI_MODEL")

    google_api_key: str = Field(default="", alias="GOOGLE_API_KEY")
    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    gemini_image_model: str = Field(default="gemini-3-pro-image-preview", alias="GEMINI_IMAGE_MODEL")

    # Veo 3.1 (video generation — uses the same Google API key as Gemini)
    veo_model: str = Field(default="veo-3.1-generate-preview", alias="VEO_MODEL")
    veo_default_resolution: str = Field(default="1080p", alias="VEO_DEFAULT_RESOLUTION")
    veo_default_aspect_ratio: str = Field(default="9:16", alias="VEO_DEFAULT_ASPECT_RATIO")
    veo_poll_interval_seconds: int = Field(default=10, alias="VEO_POLL_INTERVAL_SECONDS")
    veo_max_poll_duration_seconds: int = Field(default=600, alias="VEO_MAX_POLL_DURATION_SECONDS")

    # Video processing
    ffmpeg_path: str = Field(default="ffmpeg", alias="FFMPEG_PATH")
    max_reel_duration_seconds: int = Field(default=90, alias="MAX_REEL_DURATION_SECONDS")
    default_reel_duration_seconds: int = Field(default=8, alias="DEFAULT_REEL_DURATION_SECONDS")

    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")
    claude_model: str = Field(default="claude-sonnet-4-6", alias="CLAUDE_MODEL")

    meta_app_id: str = Field(default="", alias="META_APP_ID")
    meta_app_secret: str = Field(default="", alias="META_APP_SECRET")
    meta_page_access_token: str = Field(default="", alias="META_PAGE_ACCESS_TOKEN")
    meta_token_expires_at: Optional[str] = Field(default=None, alias="META_TOKEN_EXPIRES_AT")
    instagram_business_account_id: str = Field(default="", alias="INSTAGRAM_BUSINESS_ACCOUNT_ID")
    meta_graph_api_version: str = Field(default="v25.0", alias="META_GRAPH_API_VERSION")

    storage_bucket: str = Field(default="", alias="STORAGE_BUCKET")
    storage_region: str = Field(default="ap-south-1", alias="STORAGE_REGION")
    storage_access_key_id: str = Field(default="", alias="STORAGE_ACCESS_KEY_ID")
    storage_secret_access_key: str = Field(default="", alias="STORAGE_SECRET_ACCESS_KEY")
    storage_endpoint_url: str = Field(default="", alias="STORAGE_ENDPOINT_URL")
    storage_public_base_url: str = Field(default="", alias="STORAGE_PUBLIC_BASE_URL")

    database_url: str = Field(default="postgresql+psycopg://postgres:postgres@localhost:5432/social_media_bot", alias="DATABASE_URL")
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    credential_encryption_key: str = Field(default="", alias="CREDENTIAL_ENCRYPTION_KEY")
    admin_session_secret: str = Field(default="", alias="ADMIN_SESSION_SECRET")
    admin_csrf_secret: str = Field(default="", alias="ADMIN_CSRF_SECRET")
    admin_secure_cookies: Optional[bool] = Field(default=None, alias="ADMIN_SECURE_COOKIES")

    brand_name: str = Field(default="Default Brand", alias="BRAND_NAME")
    brand_instagram_handle: str = Field(default="", alias="BRAND_INSTAGRAM_HANDLE")
    brand_website: str = Field(default="", alias="BRAND_WEBSITE")

    @property
    def allowed_user_id_set(self) -> set[int]:
        if not self.allowed_user_ids.strip():
            return set()
        return {int(value.strip()) for value in self.allowed_user_ids.split(",") if value.strip()}

    @property
    def cors_allowed_origin_list(self) -> list[str]:
        return [value.strip() for value in self.cors_allowed_origins.split(",") if value.strip()]

    @property
    def secure_cookies(self) -> bool:
        if self.admin_secure_cookies is not None:
            return self.admin_secure_cookies
        return self.app_env.lower() in {"production", "staging"}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
