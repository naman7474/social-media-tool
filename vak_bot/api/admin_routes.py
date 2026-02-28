from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, Form, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session
from vak_bot.config import get_settings
from vak_bot.db.models import (
    AuditLog,
    Brand,
    BrandCategoryTemplate,
    BrandPromptConfig,
    Post,
    PostVariant,
    PostVariantItem,
    User,
    UserBrandRole,
)
from vak_bot.db.session import get_db_session
from vak_bot.enums import PostStatus
from vak_bot.pipeline.prompts import load_brand_config
from vak_bot.schemas.brand_config import (
    CATEGORY_CHOICES,
    build_category_template,
    deep_merge_config,
    get_category_template_map,
    validate_ai_config,
)
from vak_bot.services.admin_auth import (
    create_csrf_token,
    create_session_token,
    hash_password,
    validate_csrf_token,
    validate_session_token,
    verify_password,
)
from vak_bot.services.audit_service import write_audit_log
from vak_bot.services.credentials_service import upsert_brand_credentials
from vak_bot.workers.tasks import publish_post_task

router = APIRouter(prefix="/admin", tags=["admin"])
settings = get_settings()

class LoginPayload(BaseModel):
    email: str
    password: str = Field(min_length=8)


class BootstrapPayload(BaseModel):
    email: str
    password: str = Field(min_length=10)


class BrandCreatePayload(BaseModel):
    slug: str = Field(min_length=2, max_length=80)
    name: str = Field(min_length=1, max_length=200)
    category: str = Field(default="general", min_length=2, max_length=50)
    description: str | None = Field(default=None, max_length=3000)
    primary_product_label: str | None = Field(default=None, max_length=120)
    timezone: str = Field(default="Asia/Kolkata")
    telegram_bot_token: str | None = None
    telegram_webhook_secret: str | None = None
    allowed_user_ids: str | None = None


class BrandUpdatePayload(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    category: str | None = Field(default=None, min_length=2, max_length=50)
    description: str | None = Field(default=None, max_length=3000)
    timezone: str | None = Field(default=None)
    telegram_bot_token: str | None = None
    telegram_webhook_secret: str | None = None
    allowed_user_ids: str | None = None
class BrandCredentialPayload(BaseModel):
    meta_app_id: str
    meta_app_secret: str
    meta_page_access_token: str
    instagram_business_account_id: str
    meta_graph_api_version: str = "v25.0"


class SchedulePayload(BaseModel):
    scheduled_for: datetime
    scheduled_timezone: str = "Asia/Kolkata"


class PublishPayload(BaseModel):
    chat_id: int | None = None


class ApplyTemplatePayload(BaseModel):
    category: str = Field(default="general")


class UserCreatePayload(BaseModel):
    email: str
    password: str = Field(min_length=10)
    is_active: bool = True


class BrandMemberPayload(BaseModel):
    user_id: int
    role: str = Field(min_length=3, max_length=40)


AI_PROFILE_SECTIONS = (
    "basics",
    "colors",
    "typography",
    "visual",
    "props",
    "display",
    "hashtags",
    "captions",
    "occasions",
)

ROLE_CHOICES = ("super_admin", "account_manager", "brand_editor")


SECTION_PARTIALS: dict[str, str] = {
    "basics": "partials/ai_profile_basics.html",
    "colors": "partials/ai_profile_colors.html",
    "typography": "partials/ai_profile_typography.html",
    "visual": "partials/ai_profile_visual.html",
    "props": "partials/ai_profile_props.html",
    "display": "partials/ai_profile_display.html",
    "hashtags": "partials/ai_profile_hashtags.html",
    "captions": "partials/ai_profile_captions.html",
    "occasions": "partials/ai_profile_occasions.html",
}


def _find_user(db: Session, user_id: int | None) -> User | None:
    if user_id is None:
        return None
    return db.get(User, user_id)


def _is_super_admin(db: Session, user_id: int) -> bool:
    return (
        db.query(UserBrandRole)
        .filter(UserBrandRole.user_id == user_id, UserBrandRole.role == "super_admin")
        .first()
        is not None
    )


def _has_brand_role(db: Session, user_id: int, brand_id: int, allowed: set[str]) -> bool:
    if _is_super_admin(db, user_id):
        return True
    role = (
        db.query(UserBrandRole)
        .filter(
            UserBrandRole.user_id == user_id,
            UserBrandRole.role.in_(list(allowed)),
            (UserBrandRole.brand_id == brand_id) | (UserBrandRole.brand_id.is_(None)),
        )
        .first()
    )
    return role is not None


def _get_accessible_brands(db: Session, user: User) -> list[Brand]:
    if _is_super_admin(db, user.id):
        return db.query(Brand).order_by(Brand.name.asc()).all()

    role_rows = db.query(UserBrandRole).filter(UserBrandRole.user_id == user.id).all()
    brand_ids = [row.brand_id for row in role_rows if row.brand_id is not None]
    if not brand_ids:
        return []
    return db.query(Brand).filter(Brand.id.in_(brand_ids)).order_by(Brand.name.asc()).all()


def _require_user(request: Request, db: Session) -> User:
    token = request.cookies.get("admin_session")
    user_id = validate_session_token(token)
    user = _find_user(db, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="unauthorized")
    return user


def _require_csrf(request: Request, user: User) -> None:
    if request.method in {"GET", "HEAD", "OPTIONS"}:
        return
    token = request.headers.get("x-csrf-token")
    if not validate_csrf_token(user.id, token):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="invalid csrf token")


def _require_csrf_token(user_id: int, token: str | None) -> None:
    if not validate_csrf_token(user_id, token):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="invalid csrf token")


def _user_can_access_brand(db: Session, user: User, brand_id: int) -> bool:
    return _has_brand_role(db, user.id, brand_id, {"super_admin", "account_manager", "brand_editor"})


def _set_auth_cookies(response: Response, user_id: int) -> str:
    session_token = create_session_token(user_id)
    csrf_token = create_csrf_token(user_id)
    secure_cookie = settings.secure_cookies
    response.set_cookie("admin_session", session_token, httponly=True, secure=secure_cookie, samesite="lax", max_age=8 * 3600)
    response.set_cookie("admin_csrf", csrf_token, httponly=False, secure=secure_cookie, samesite="lax", max_age=8 * 3600)
    return csrf_token


def _perform_bootstrap(db: Session, email: str, password: str) -> User:
    existing = db.query(User).count()
    if existing > 0:
        raise HTTPException(status_code=409, detail="bootstrap already complete")

    user = User(email=email.lower(), password_hash=hash_password(password), is_active=True)
    db.add(user)
    db.commit()
    db.refresh(user)
    db.add(UserBrandRole(user_id=user.id, brand_id=None, role="super_admin"))
    db.commit()
    return user


def _perform_login(db: Session, email: str, password: str) -> User:
    user = db.query(User).filter(User.email == email.lower()).first()
    if not user:
        raise HTTPException(status_code=401, detail="invalid credentials")

    now = datetime.now(timezone.utc)
    if user.locked_until and user.locked_until > now:
        raise HTTPException(status_code=429, detail="account temporarily locked")

    if not verify_password(user.password_hash, password):
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= 5:
            user.locked_until = now + timedelta(minutes=15)
            user.failed_login_attempts = 0
        db.commit()
        raise HTTPException(status_code=401, detail="invalid credentials")

    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login_at = now
    db.commit()
    return user


def _redirect_ui(
    brand_id: int | None = None,
    status_msg: str | None = None,
    error_msg: str | None = None,
    ai_section: str | None = None,
) -> RedirectResponse:
    params: dict[str, str] = {}
    if brand_id is not None:
        params["brand_id"] = str(brand_id)
    if ai_section:
        params["ai_section"] = ai_section
    if status_msg:
        params["status"] = status_msg
    if error_msg:
        params["error"] = error_msg
    url = "/admin/ui"
    if params:
        url += "?" + urlencode(params)
    return RedirectResponse(url=url, status_code=status.HTTP_303_SEE_OTHER)


def _safe_int(value: str | None) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _normalize_brand_category(raw: str | None) -> str:
    value = (raw or "").strip().lower()
    if value not in CATEGORY_CHOICES:
        return "general"
    return value


def _require_brand_category(raw: str | None) -> str:
    value = (raw or "").strip().lower()
    if not value:
        raise HTTPException(status_code=422, detail="category is required")
    return value


def _require_template_category(raw: str | None) -> str:
    value = (raw or "").strip().lower()
    if value not in CATEGORY_CHOICES:
        raise HTTPException(status_code=422, detail=f"invalid template category (allowed: {', '.join(CATEGORY_CHOICES)})")
    return value


def _normalize_role(raw: str | None) -> str:
    value = (raw or "").strip().lower()
    if value not in ROLE_CHOICES:
        raise HTTPException(status_code=422, detail=f"invalid role (allowed: {', '.join(ROLE_CHOICES)})")
    return value


def _join_lines(values: Any) -> str:
    if not isinstance(values, list):
        return ""
    return "\n".join(str(v).strip() for v in values if str(v).strip())


def _split_items(raw: str | None) -> list[str]:
    if not raw:
        return []
    tokens = raw.replace("\n", ",").split(",")
    return [token.strip() for token in tokens if token.strip()]


def _parse_key_value_lines(raw: str | None) -> dict[str, str]:
    if not raw:
        return {}
    mapping: dict[str, str] = {}
    for line in raw.splitlines():
        line = line.strip()
        if not line or ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if key and value:
            mapping[key] = value
    return mapping


def _parse_percent_map(raw: str | None) -> dict[str, int]:
    if not raw:
        return {}
    mapping: dict[str, int] = {}
    for key, value in _parse_key_value_lines(raw).items():
        try:
            mapping[key] = int(value)
        except ValueError:
            continue
    return mapping


def _render_key_value_lines(mapping: Any) -> str:
    if not isinstance(mapping, dict):
        return ""
    return "\n".join(f"{k}: {v}" for k, v in mapping.items() if str(k).strip() and str(v).strip())


def _latest_template_by_category(db: Session) -> dict[str, dict[str, Any]]:
    try:
        rows = (
            db.query(BrandCategoryTemplate)
            .filter(BrandCategoryTemplate.is_active.is_(True))
            .order_by(BrandCategoryTemplate.category.asc(), BrandCategoryTemplate.created_at.desc(), BrandCategoryTemplate.id.desc())
            .all()
        )
    except Exception:
        return {}
    by_category: dict[str, dict[str, Any]] = {}
    for row in rows:
        category = _normalize_brand_category(row.category)
        if category in by_category:
            continue
        if isinstance(row.template_json, dict):
            by_category[category] = row.template_json
    return by_category


def _get_category_template(db: Session, category: str) -> dict[str, Any]:
    normalized = _normalize_brand_category(category)
    from_db = _latest_template_by_category(db).get(normalized)
    if isinstance(from_db, dict):
        try:
            return validate_ai_config(from_db)
        except Exception:
            return build_category_template(normalized)
    return build_category_template(normalized)


def _list_category_templates(db: Session) -> dict[str, dict[str, Any]]:
    from_db = _latest_template_by_category(db)
    defaults = get_category_template_map()
    merged: dict[str, dict[str, Any]] = {}
    for category in CATEGORY_CHOICES:
        source = from_db.get(category, defaults[category])
        try:
            merged[category] = validate_ai_config(source)
        except Exception:
            merged[category] = defaults[category]
    return merged


def _upsert_brand_prompt_config(
    db: Session,
    brand_id: int,
    updates: dict[str, Any],
    *,
    replace: bool = False,
) -> BrandPromptConfig:
    record = db.query(BrandPromptConfig).filter(BrandPromptConfig.brand_id == brand_id).first()
    existing = {} if replace else (dict(record.config_json) if record and isinstance(record.config_json, dict) else {})
    merged = deep_merge_config(existing, updates)
    validated = validate_ai_config(merged)

    if record is None:
        record = BrandPromptConfig(brand_id=brand_id, config_json=validated)
        db.add(record)
    else:
        record.config_json = validated
        record.is_active = True
    db.commit()
    db.refresh(record)
    return record


def _extract_brand_ai_profile(brand: Brand | None) -> dict[str, Any]:
    if not brand:
        return build_category_template("general")
    return load_brand_config(brand.id)


def _color_dict_to_list(color_dict: dict[str, str]) -> list[dict[str, str]]:
    """Convert color dict {name: hex} to list of {name, hex} for UI."""
    if not isinstance(color_dict, dict):
        return []
    return [{"name": name, "hex": hex_val} for name, hex_val in color_dict.items() if hex_val]


def _safe_list(val: Any) -> list[str]:
    """Safely convert to list of strings."""
    if isinstance(val, list):
        return [str(v).strip() for v in val if str(v).strip()]
    return []


def _build_ai_form_data(config: dict[str, Any]) -> dict[str, Any]:
    product = config.get("product_vocabulary", {}) if isinstance(config.get("product_vocabulary"), dict) else {}
    colors = config.get("colors", {}) if isinstance(config.get("colors"), dict) else {}
    typography = config.get("typography", {}) if isinstance(config.get("typography"), dict) else {}
    visual = config.get("visual_identity", {}) if isinstance(config.get("visual_identity"), dict) else {}
    props = config.get("props_library", {}) if isinstance(config.get("props_library"), dict) else {}
    hashtags = config.get("hashtags", {}) if isinstance(config.get("hashtags"), dict) else {}
    caption_rules = config.get("caption_rules", {}) if isinstance(config.get("caption_rules"), dict) else {}
    occasions = config.get("occasions", {}) if isinstance(config.get("occasions"), dict) else {}
    brand_block = config.get("brand", {}) if isinstance(config.get("brand"), dict) else {}

    return {
        # Basics
        "brand_tagline": str(brand_block.get("tagline") or ""),
        "brand_language": str(config.get("language") or "en"),
        "product_singular": str(product.get("singular") or ""),
        "product_plural": str(product.get("plural") or ""),
        "product_featured_part": str(product.get("featured_part") or ""),
        "audience_profile": str(config.get("audience_profile") or ""),
        "brand_voice": str(config.get("brand_voice") or ""),
        "llm_guardrails": str(config.get("llm_guardrails") or ""),
        # Colors - string format for textarea fallback
        "colors_primary": _render_key_value_lines(colors.get("primary", {})),
        "colors_secondary": _render_key_value_lines(colors.get("secondary", {})),
        "colors_accent": _render_key_value_lines(colors.get("accent", {})),
        # Colors - list format for color picker UI
        "colors_primary_list": _color_dict_to_list(colors.get("primary", {})),
        "colors_secondary_list": _color_dict_to_list(colors.get("secondary", {})),
        "colors_accent_list": _color_dict_to_list(colors.get("accent", {})),
        # Typography
        "typography_heading_feel": str(typography.get("heading_feel") or ""),
        "typography_body_feel": str(typography.get("body_feel") or ""),
        "typography_overlay_feel": str(typography.get("overlay_feel") or ""),
        "typography_rules": _join_lines(typography.get("rules", [])),
        # Visual
        "visual_grid_aesthetic": str(visual.get("grid_aesthetic") or ""),
        "visual_dominant_mood": str(visual.get("dominant_mood") or ""),
        "visual_avoid": "\n".join(visual.get("avoid", [])) if isinstance(visual.get("avoid"), list) else "",
        "visual_prefer": "\n".join(visual.get("prefer", [])) if isinstance(visual.get("prefer"), list) else "",
        # Props - string format
        "props_warm": ", ".join(props.get("warm", [])) if isinstance(props.get("warm"), list) else "",
        "props_minimal": ", ".join(props.get("minimal", [])) if isinstance(props.get("minimal"), list) else "",
        "props_luxe": ", ".join(props.get("luxe", [])) if isinstance(props.get("luxe"), list) else "",
        "props_earthy": ", ".join(props.get("earthy", [])) if isinstance(props.get("earthy"), list) else "",
        "props_never_use": ", ".join(props.get("never_use", [])) if isinstance(props.get("never_use"), list) else "",
        # Props - list format for tag input UI
        "props_warm_list": _safe_list(props.get("warm", [])),
        "props_minimal_list": _safe_list(props.get("minimal", [])),
        "props_luxe_list": _safe_list(props.get("luxe", [])),
        "props_earthy_list": _safe_list(props.get("earthy", [])),
        "props_never_use_list": _safe_list(props.get("never_use", [])),
        # Display
        "display_styles": _render_key_value_lines(config.get("display_styles", {})),
        "variation_modifiers": _join_lines(config.get("variation_modifiers", [])),
        # Hashtags - string format
        "hashtags_brand_always": " ".join(hashtags.get("brand_always", [])) if isinstance(hashtags.get("brand_always"), list) else "",
        "hashtags_craft": " ".join(hashtags.get("craft", [])) if isinstance(hashtags.get("craft"), list) else "",
        "hashtags_product": " ".join(hashtags.get("product", [])) if isinstance(hashtags.get("product"), list) else "",
        "hashtags_product_other": " ".join(hashtags.get("product_other", [])) if isinstance(hashtags.get("product_other"), list) else "",
        "hashtags_discovery": " ".join(hashtags.get("discovery", [])) if isinstance(hashtags.get("discovery"), list) else "",
        "hashtags_occasion_festive": " ".join(hashtags.get("occasion_festive", [])) if isinstance(hashtags.get("occasion_festive"), list) else "",
        "hashtags_occasion_wedding": " ".join(hashtags.get("occasion_wedding", [])) if isinstance(hashtags.get("occasion_wedding"), list) else "",
        "hashtags_occasion_everyday": " ".join(hashtags.get("occasion_everyday", [])) if isinstance(hashtags.get("occasion_everyday"), list) else "",
        "hashtags_niche": " ".join(hashtags.get("niche", [])) if isinstance(hashtags.get("niche"), list) else "",
        "hashtags_never_use": " ".join(hashtags.get("never_use", [])) if isinstance(hashtags.get("never_use"), list) else "",
        # Hashtags - list format for tag input UI
        "hashtags_brand_always_list": _safe_list(hashtags.get("brand_always", [])),
        "hashtags_craft_list": _safe_list(hashtags.get("craft", [])),
        "hashtags_product_list": _safe_list(hashtags.get("product", [])),
        "hashtags_product_other_list": _safe_list(hashtags.get("product_other", [])),
        "hashtags_discovery_list": _safe_list(hashtags.get("discovery", [])),
        "hashtags_occasion_festive_list": _safe_list(hashtags.get("occasion_festive", [])),
        "hashtags_occasion_wedding_list": _safe_list(hashtags.get("occasion_wedding", [])),
        "hashtags_occasion_everyday_list": _safe_list(hashtags.get("occasion_everyday", [])),
        "hashtags_niche_list": _safe_list(hashtags.get("niche", [])),
        "hashtags_never_use_list": _safe_list(hashtags.get("never_use", [])),
        # Captions
        "captions_optimal_length": str(caption_rules.get("optimal_length") or ""),
        "captions_max_length": str(caption_rules.get("max_length") or ""),
        "captions_emoji_limit": str(caption_rules.get("emoji_limit") or ""),
        "captions_must_mention": _join_lines(caption_rules.get("must_mention", [])),
        "captions_banned_words": _join_lines(caption_rules.get("banned_words", [])),
        "captions_cta_rotation": _join_lines(config.get("cta_rotation", [])),
        # Occasions
        "occasions_festive": _join_lines(occasions.get("festive", [])),
        "occasions_wedding": _join_lines(occasions.get("wedding", [])),
        "occasions_everyday": _join_lines(occasions.get("everyday", [])),
        "occasions_campaign": _join_lines(occasions.get("campaign", [])),
        "occasions_content_mix": _render_key_value_lines(occasions.get("content_mix", {})),
    }


def _updates_from_section_payload(section: str, payload: dict[str, Any]) -> dict[str, Any]:
    normalized = section if section in AI_PROFILE_SECTIONS else "basics"
    brand = payload.get("brand", {}) if isinstance(payload.get("brand"), dict) else {}
    if normalized == "basics":
        return {
            "brand": {"tagline": str(payload.get("brand_tagline", brand.get("tagline", "")))},
            "language": str(payload.get("brand_language", payload.get("language", "en")) or "en"),
            "product_vocabulary": {
                "singular": str(payload.get("product_singular", payload.get("singular", "product"))),
                "plural": str(payload.get("product_plural", payload.get("plural", "products"))),
                "featured_part": str(payload.get("product_featured_part", payload.get("featured_part", "detail"))),
            },
            "audience_profile": str(payload.get("audience_profile", "")),
            "brand_voice": str(payload.get("brand_voice", "")),
            "llm_guardrails": str(payload.get("llm_guardrails", "")),
        }
    if normalized == "colors":
        if isinstance(payload.get("colors"), dict):
            return {"colors": payload["colors"]}
        return {"colors": payload}
    if normalized == "typography":
        if isinstance(payload.get("typography"), dict):
            return {"typography": payload["typography"]}
        return {"typography": payload}
    if normalized == "visual":
        if isinstance(payload.get("visual_identity"), dict):
            return {"visual_identity": payload["visual_identity"]}
        return {"visual_identity": payload}
    if normalized == "props":
        if isinstance(payload.get("props_library"), dict):
            return {"props_library": payload["props_library"]}
        return {"props_library": payload}
    if normalized == "display":
        updates: dict[str, Any] = {}
        if isinstance(payload.get("display_styles"), dict):
            updates["display_styles"] = payload["display_styles"]
        if isinstance(payload.get("variation_modifiers"), list):
            updates["variation_modifiers"] = payload["variation_modifiers"]
        if updates:
            return updates
        return {"display_styles": payload}
    if normalized == "hashtags":
        if isinstance(payload.get("hashtags"), dict):
            return {"hashtags": payload["hashtags"]}
        return {"hashtags": payload}
    if normalized == "captions":
        updates = {}
        if isinstance(payload.get("caption_rules"), dict):
            updates["caption_rules"] = payload["caption_rules"]
        if isinstance(payload.get("cta_rotation"), list):
            updates["cta_rotation"] = payload["cta_rotation"]
        if updates:
            return updates
        return {"caption_rules": payload}
    if normalized == "occasions":
        if isinstance(payload.get("occasions"), dict):
            return {"occasions": payload["occasions"]}
        return {"occasions": payload}
    return {}


def _updates_from_section_form(section: str, form_data: dict[str, str]) -> dict[str, Any]:
    normalized = section if section in AI_PROFILE_SECTIONS else "basics"
    if normalized == "basics":
        return {
            "brand": {"tagline": form_data.get("brand_tagline", "").strip()},
            "language": form_data.get("brand_language", "").strip() or "en",
            "product_vocabulary": {
                "singular": form_data.get("product_singular", "").strip() or "product",
                "plural": form_data.get("product_plural", "").strip() or "products",
                "featured_part": form_data.get("product_featured_part", "").strip() or "detail",
            },
            "audience_profile": form_data.get("audience_profile", "").strip(),
            "brand_voice": form_data.get("brand_voice", "").strip(),
            "llm_guardrails": form_data.get("llm_guardrails", "").strip(),
        }
    if normalized == "colors":
        return {
            "colors": {
                "primary": _parse_key_value_lines(form_data.get("colors_primary")),
                "secondary": _parse_key_value_lines(form_data.get("colors_secondary")),
                "accent": _parse_key_value_lines(form_data.get("colors_accent")),
            }
        }
    if normalized == "typography":
        return {
            "typography": {
                "heading_feel": form_data.get("typography_heading_feel", "").strip(),
                "body_feel": form_data.get("typography_body_feel", "").strip(),
                "overlay_feel": form_data.get("typography_overlay_feel", "").strip(),
                "rules": _split_items(form_data.get("typography_rules")),
            }
        }
    if normalized == "visual":
        return {
            "visual_identity": {
                "grid_aesthetic": form_data.get("visual_grid_aesthetic", "").strip(),
                "dominant_mood": form_data.get("visual_dominant_mood", "").strip(),
                "avoid": _split_items(form_data.get("visual_avoid")),
                "prefer": _split_items(form_data.get("visual_prefer")),
            }
        }
    if normalized == "props":
        return {
            "props_library": {
                "warm": _split_items(form_data.get("props_warm")),
                "minimal": _split_items(form_data.get("props_minimal")),
                "luxe": _split_items(form_data.get("props_luxe")),
                "earthy": _split_items(form_data.get("props_earthy")),
                "never_use": _split_items(form_data.get("props_never_use")),
            }
        }
    if normalized == "display":
        return {
            "display_styles": _parse_key_value_lines(form_data.get("display_styles")),
            "variation_modifiers": _split_items(form_data.get("variation_modifiers")),
        }
    if normalized == "hashtags":
        return {
            "hashtags": {
                "brand_always": _split_items(form_data.get("hashtags_brand_always")),
                "craft": _split_items(form_data.get("hashtags_craft")),
                "product": _split_items(form_data.get("hashtags_product")),
                "product_other": _split_items(form_data.get("hashtags_product_other")),
                "discovery": _split_items(form_data.get("hashtags_discovery")),
                "occasion_festive": _split_items(form_data.get("hashtags_occasion_festive")),
                "occasion_wedding": _split_items(form_data.get("hashtags_occasion_wedding")),
                "occasion_everyday": _split_items(form_data.get("hashtags_occasion_everyday")),
                "niche": _split_items(form_data.get("hashtags_niche")),
                "never_use": _split_items(form_data.get("hashtags_never_use")),
            }
        }
    if normalized == "captions":
        return {
            "caption_rules": {
                "optimal_length": form_data.get("captions_optimal_length", "").strip(),
                "max_length": int(form_data.get("captions_max_length", "280") or 280),
                "emoji_limit": int(form_data.get("captions_emoji_limit", "2") or 2),
                "must_mention": _split_items(form_data.get("captions_must_mention")),
                "banned_words": _split_items(form_data.get("captions_banned_words")),
            },
            "cta_rotation": _split_items(form_data.get("captions_cta_rotation")),
        }
    if normalized == "occasions":
        return {
            "occasions": {
                "festive": _split_items(form_data.get("occasions_festive")),
                "wedding": _split_items(form_data.get("occasions_wedding")),
                "everyday": _split_items(form_data.get("occasions_everyday")),
                "campaign": _split_items(form_data.get("occasions_campaign")),
                "content_mix": _parse_percent_map(form_data.get("occasions_content_mix")),
            }
        }
    return {}


def _generation_dependency_checks() -> dict[str, bool]:
    # Provider and storage settings are global dependencies in the current architecture.
    if settings.dry_run:
        return {
            "dry_run_mode": True,
            "openai_configured": True,
            "claude_configured": True,
            "google_or_gemini_configured": True,
            "databright_configured": True,
            "storage_configured": True,
        }
    return {
        "dry_run_mode": False,
        "openai_configured": bool(settings.openai_api_key),
        "claude_configured": bool(settings.anthropic_api_key),
        "google_or_gemini_configured": bool(settings.google_api_key or settings.gemini_api_key),
        "databright_configured": bool(settings.databright_api_key),
        "storage_configured": bool(
            settings.storage_bucket
            and settings.storage_access_key_id
            and settings.storage_secret_access_key
            and settings.storage_endpoint_url
            and settings.storage_public_base_url
        ),
    }


def _brand_metrics(db: Session, brand_id: int) -> dict[str, Any]:
    status_rows = (
        db.query(Post.status, func.count(Post.id))
        .filter(Post.brand_id == brand_id)
        .group_by(Post.status)
        .all()
    )
    status_counts = {status: count for status, count in status_rows}
    total_posts = int(sum(status_counts.values()))
    next_scheduled = (
        db.query(Post)
        .filter(Post.brand_id == brand_id, Post.scheduled_for.is_not(None), Post.scheduled_for >= datetime.now(timezone.utc))
        .order_by(Post.scheduled_for.asc())
        .first()
    )

    last_activity = (
        db.query(AuditLog.created_at)
        .filter(AuditLog.brand_id == brand_id)
        .order_by(AuditLog.created_at.desc())
        .limit(1)
        .scalar()
    )

    return {
        "total_posts": total_posts,
        "review_ready": int(status_counts.get(PostStatus.REVIEW_READY.value, 0)),
        "scheduled": int(status_counts.get(PostStatus.SCHEDULED.value, 0)),
        "posted": int(status_counts.get(PostStatus.POSTED.value, 0)),
        "failed": int(status_counts.get(PostStatus.FAILED.value, 0)),
        "next_scheduled_for": next_scheduled.scheduled_for if next_scheduled else None,
        "last_activity": last_activity,
    }


@router.get("/health")
def admin_health() -> dict[str, Any]:
    return {"status": "ok", "surface": "admin"}


@router.get("/login")
def login_page(request: Request, db: Session = Depends(get_db_session)) -> RedirectResponse:
    # Redirect HTML page requests to the new Next.js frontend
    return RedirectResponse(url=f"{settings.frontend_base_url.rstrip('/')}/login", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/login")
def login_page_submit(
    response: Response,
    db: Session = Depends(get_db_session),
    email: str = Form(...),
    password: str = Form(...),
) -> Response:
    try:
        user = _perform_login(db, email=email, password=password)
    except HTTPException as exc:
        return RedirectResponse(url=f"/admin/login?error={exc.detail}", status_code=status.HTTP_303_SEE_OTHER)

    _set_auth_cookies(response, user.id)
    write_audit_log(db, action="auth.login", user_id=user.id)
    response.status_code = status.HTTP_303_SEE_OTHER
    response.headers["Location"] = "/admin/ui"
    return response


@router.post("/bootstrap")
def bootstrap_page_submit(
    response: Response,
    db: Session = Depends(get_db_session),
    email: str = Form(...),
    password: str = Form(...),
) -> Response:
    if len(password) < 10:
        return RedirectResponse(url="/admin/login?error=Password must be at least 10 characters", status_code=status.HTTP_303_SEE_OTHER)

    try:
        user = _perform_bootstrap(db, email=email, password=password)
    except HTTPException as exc:
        return RedirectResponse(url=f"/admin/login?error={exc.detail}", status_code=status.HTTP_303_SEE_OTHER)

    _set_auth_cookies(response, user.id)
    write_audit_log(db, action="auth.bootstrap", user_id=user.id)
    response.status_code = status.HTTP_303_SEE_OTHER
    response.headers["Location"] = "/admin/ui"
    return response


@router.post("/ui/logout")
def ui_logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db_session),
    csrf_token: str = Form(...),
) -> Response:
    user = _require_user(request, db)
    _require_csrf_token(user.id, csrf_token)
    response.delete_cookie("admin_session")
    response.delete_cookie("admin_csrf")
    write_audit_log(db, action="auth.logout", user_id=user.id)
    response.status_code = status.HTTP_303_SEE_OTHER
    response.headers["Location"] = "/admin/login?status=Logged out"
    return response


@router.get("/ui")
def admin_ui(request: Request, db: Session = Depends(get_db_session)) -> RedirectResponse:
    return RedirectResponse(url=f"{settings.frontend_base_url.rstrip('/')}/dashboard", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/ui/brands/{brand_id}/ai-profile")
def ai_profile_page(
    brand_id: int,
    section: str = "basics",
) -> Response:
    normalized = section if section in AI_PROFILE_SECTIONS else "basics"
    return RedirectResponse(
        url=f"/admin/ui?brand_id={brand_id}&ai_section={normalized}",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post("/ui/brands/create")
def ui_create_brand(
    request: Request,
    db: Session = Depends(get_db_session),
    csrf_token: str = Form(...),
    slug: str = Form(...),
    name: str = Form(...),
    category_value: str = Form("general"),
    description_value: str = Form(""),
    primary_product_label: str = Form(""),
    timezone_value: str = Form("Asia/Kolkata"),
    telegram_bot_token: str = Form(""),
    telegram_webhook_secret: str = Form(""),
    allowed_user_ids: str = Form(""),
) -> Response:
    user = _require_user(request, db)
    _require_csrf_token(user.id, csrf_token)
    if not _is_super_admin(db, user.id):
        raise HTTPException(status_code=403, detail="forbidden")

    clean_slug = slug.strip()
    clean_name = name.strip()
    existing = db.query(Brand).filter(Brand.slug == clean_slug).first()
    if existing:
        return _redirect_ui(status_msg=None, error_msg="Brand slug already exists")

    brand = Brand(
        slug=clean_slug,
        name=clean_name,
        category=_require_brand_category(category_value),
        description=description_value.strip() or None,
        timezone=timezone_value.strip() or "Asia/Kolkata",
        telegram_bot_token=telegram_bot_token.strip() or None,
        telegram_webhook_secret=telegram_webhook_secret.strip() or None,
        allowed_user_ids=allowed_user_ids.strip() or None,
    )
    db.add(brand)
    db.commit()
    db.refresh(brand)
    seeded_config = _get_category_template(db, brand.category)
    if primary_product_label.strip():
        seeded_config = deep_merge_config(
            seeded_config,
            {
                "product_vocabulary": {
                    "singular": primary_product_label.strip(),
                    "plural": f"{primary_product_label.strip()}s",
                }
            },
        )
    _upsert_brand_prompt_config(db, brand.id, seeded_config, replace=True)

    write_audit_log(
        db,
        action="brand.create",
        brand_id=brand.id,
        user_id=user.id,
        entity_type="brand",
        entity_id=str(brand.id),
        details={"slug": brand.slug, "name": brand.name, "category": brand.category},
    )
    return _redirect_ui(brand_id=brand.id, status_msg="Brand created")


@router.post("/ui/brands/{brand_id}/credentials")
def ui_set_brand_credentials(
    brand_id: int,
    request: Request,
    db: Session = Depends(get_db_session),
    csrf_token: str = Form(...),
    meta_app_id: str = Form(...),
    meta_app_secret: str = Form(...),
    meta_page_access_token: str = Form(...),
    instagram_business_account_id: str = Form(...),
    meta_graph_api_version: str = Form("v25.0"),
) -> Response:
    user = _require_user(request, db)
    _require_csrf_token(user.id, csrf_token)
    if not _has_brand_role(db, user.id, brand_id, {"super_admin", "account_manager"}):
        raise HTTPException(status_code=403, detail="forbidden")

    brand = db.get(Brand, brand_id)
    if not brand:
        raise HTTPException(status_code=404, detail="brand not found")

    upsert_brand_credentials(
        db,
        brand_id=brand_id,
        meta_app_id=meta_app_id,
        meta_app_secret=meta_app_secret,
        meta_page_access_token=meta_page_access_token,
        instagram_business_account_id=instagram_business_account_id,
        meta_graph_api_version=meta_graph_api_version,
    )

    write_audit_log(
        db,
        action="brand.credentials.update",
        brand_id=brand_id,
        user_id=user.id,
        entity_type="brand_credentials",
        entity_id=str(brand_id),
    )
    return _redirect_ui(brand_id=brand_id, status_msg="Credentials saved")


@router.post("/ui/brands/{brand_id}/ai-profile")
async def ui_update_ai_profile(
    brand_id: int,
    request: Request,
    db: Session = Depends(get_db_session),
) -> Response:
    user = _require_user(request, db)
    form = await request.form()
    csrf_token = str(form.get("csrf_token") or "")
    _require_csrf_token(user.id, csrf_token)
    if not _has_brand_role(db, user.id, brand_id, {"super_admin", "account_manager", "brand_editor"}):
        raise HTTPException(status_code=403, detail="forbidden")

    brand = db.get(Brand, brand_id)
    if not brand:
        raise HTTPException(status_code=404, detail="brand not found")

    section = str(form.get("section") or "basics")
    payload = {key: str(value) for key, value in form.items() if key not in {"csrf_token", "section"}}
    try:
        updates = _updates_from_section_form(section, payload)
        _upsert_brand_prompt_config(db, brand_id=brand_id, updates=updates)
    except Exception as exc:
        return _redirect_ui(brand_id=brand_id, error_msg=f"Invalid AI profile input: {exc}", ai_section=section)

    write_audit_log(
        db,
        action="brand.ai_profile.update",
        brand_id=brand_id,
        user_id=user.id,
        entity_type="brand_prompt_config",
        entity_id=str(brand_id),
        details={
            "section": section,
            "updated_fields": list(updates.keys()),
        },
    )
    return _redirect_ui(brand_id=brand_id, status_msg="AI profile saved", ai_section=section)


@router.post("/ui/brands/{brand_id}/apply-template")
def ui_apply_template(
    brand_id: int,
    request: Request,
    db: Session = Depends(get_db_session),
    csrf_token: str = Form(...),
    category: str = Form("general"),
) -> Response:
    user = _require_user(request, db)
    _require_csrf_token(user.id, csrf_token)
    if not _has_brand_role(db, user.id, brand_id, {"super_admin", "account_manager", "brand_editor"}):
        raise HTTPException(status_code=403, detail="forbidden")

    brand = db.get(Brand, brand_id)
    if not brand:
        raise HTTPException(status_code=404, detail="brand not found")

    normalized = _require_template_category(category)
    template_json = _get_category_template(db, normalized)
    _upsert_brand_prompt_config(db, brand_id, template_json, replace=True)
    brand.category = normalized
    db.commit()

    write_audit_log(
        db,
        action="brand.ai_profile.apply_template",
        brand_id=brand_id,
        user_id=user.id,
        entity_type="brand_prompt_config",
        entity_id=str(brand_id),
        details={"category": normalized},
    )
    return _redirect_ui(brand_id=brand_id, status_msg=f"Applied {normalized} template", ai_section="basics")


@router.post("/ui/brands/{brand_id}/onboarding/validate")
def ui_validate_onboarding(
    brand_id: int,
    request: Request,
    db: Session = Depends(get_db_session),
    csrf_token: str = Form(...),
) -> Response:
    user = _require_user(request, db)
    _require_csrf_token(user.id, csrf_token)
    if not _has_brand_role(db, user.id, brand_id, {"super_admin", "account_manager", "brand_editor"}):
        raise HTTPException(status_code=403, detail="forbidden")

    brand = db.get(Brand, brand_id)
    if not brand:
        raise HTTPException(status_code=404, detail="brand not found")

    checks = {
        "brand_exists": True,
        "telegram_bot_configured": bool(brand.telegram_bot_token),
        "telegram_webhook_secret": bool(brand.telegram_webhook_secret),
        "meta_credentials_configured": bool(brand.credentials and brand.credentials.instagram_business_account_id),
        **_generation_dependency_checks(),
    }
    write_audit_log(
        db,
        action="brand.onboarding.validate",
        brand_id=brand_id,
        user_id=user.id,
        entity_type="brand",
        entity_id=str(brand_id),
        details=checks,
    )

    ok = all(checks.values())
    return _redirect_ui(
        brand_id=brand_id,
        status_msg="Onboarding checks passed" if ok else "Onboarding checks ran",
        error_msg=None if ok else "Some checks are missing",
    )


@router.post("/ui/posts/{post_id}/schedule")
def ui_schedule_post(
    post_id: int,
    request: Request,
    db: Session = Depends(get_db_session),
    csrf_token: str = Form(...),
    scheduled_for: str = Form(...),
    scheduled_timezone: str = Form("UTC"),
) -> Response:
    user = _require_user(request, db)
    _require_csrf_token(user.id, csrf_token)

    post = db.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="post not found")
    if not _user_can_access_brand(db, user, post.brand_id):
        raise HTTPException(status_code=403, detail="forbidden")

    try:
        dt = datetime.fromisoformat(scheduled_for)
    except Exception:
        return _redirect_ui(brand_id=post.brand_id, error_msg="Invalid datetime format")

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    post.scheduled_for = dt.astimezone(timezone.utc)
    post.scheduled_timezone = scheduled_timezone
    post.scheduled_by_user_id = user.id
    post.status = PostStatus.SCHEDULED.value
    db.commit()

    write_audit_log(
        db,
        action="post.schedule",
        brand_id=post.brand_id,
        user_id=user.id,
        entity_type="post",
        entity_id=str(post.id),
        details={"scheduled_for": post.scheduled_for.isoformat(), "timezone": scheduled_timezone},
    )
    return _redirect_ui(brand_id=post.brand_id, status_msg=f"Post {post.id} scheduled")


@router.post("/ui/posts/{post_id}/publish")
def ui_publish_post(
    post_id: int,
    request: Request,
    db: Session = Depends(get_db_session),
    csrf_token: str = Form(...),
    chat_id: str = Form(""),
) -> Response:
    user = _require_user(request, db)
    _require_csrf_token(user.id, csrf_token)

    post = db.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="post not found")
    if not _has_brand_role(db, user.id, post.brand_id, {"super_admin", "account_manager", "brand_editor"}):
        raise HTTPException(status_code=403, detail="forbidden")

    parsed_chat_id = _safe_int(chat_id)
    if parsed_chat_id is None:
        parsed_chat_id = int(post.sessions[0].chat_id) if post.sessions else 0

    publish_post_task.delay(post.id, parsed_chat_id, str(user.id), post.brand_id)
    write_audit_log(
        db,
        action="post.publish.requested",
        brand_id=post.brand_id,
        user_id=user.id,
        entity_type="post",
        entity_id=str(post.id),
        details={"chat_id": parsed_chat_id},
    )
    return _redirect_ui(brand_id=post.brand_id, status_msg=f"Post {post.id} publish queued")


# JSON API endpoints

@router.post("/auth/bootstrap")
def bootstrap_admin(payload: BootstrapPayload, db: Session = Depends(get_db_session)) -> dict[str, Any]:
    user = _perform_bootstrap(db, email=payload.email, password=payload.password)
    return {"ok": True, "user_id": user.id}


@router.post("/auth/login")
def admin_login(payload: LoginPayload, response: Response, db: Session = Depends(get_db_session)) -> dict[str, Any]:
    user = _perform_login(db, email=payload.email, password=payload.password)
    csrf_token = _set_auth_cookies(response, user.id)
    write_audit_log(db, action="auth.login", user_id=user.id)
    return {"ok": True, "user_id": user.id, "csrf_token": csrf_token}


@router.post("/auth/logout")
def admin_logout(request: Request, response: Response, db: Session = Depends(get_db_session)) -> dict[str, Any]:
    user = _require_user(request, db)
    _require_csrf(request, user)
    response.delete_cookie("admin_session")
    response.delete_cookie("admin_csrf")
    write_audit_log(db, action="auth.logout", user_id=user.id)
    return {"ok": True}


@router.get("/api/dashboard")
def get_dashboard_data(
    request: Request,
    brand_id: int | None = None,
    db: Session = Depends(get_db_session),
) -> dict[str, Any]:
    user = _require_user(request, db)
    brands = _get_accessible_brands(db, user)
    if not brands:
        selected_brand = None
    else:
        selected_brand = next((b for b in brands if b.id == brand_id), brands[0])

    onboarding_checks: dict[str, bool] | None = None
    brand_metrics: dict[str, Any] | None = None
    category_templates = _list_category_templates(db)

    brand_data = None
    if selected_brand is not None:
        onboarding_checks = {
            "telegram_bot_configured": bool(selected_brand.telegram_bot_token),
            "telegram_webhook_secret": bool(selected_brand.telegram_webhook_secret),
            "meta_credentials_configured": bool(selected_brand.credentials and selected_brand.credentials.instagram_business_account_id),
            **_generation_dependency_checks(),
        }
        brand_metrics = _brand_metrics(db, selected_brand.id)
        brand_data = {
            "id": selected_brand.id,
            "slug": selected_brand.slug,
            "name": selected_brand.name,
            "category": selected_brand.category,
            "timezone": selected_brand.timezone,
            "status": selected_brand.status,
            "description": selected_brand.description,
            "telegram_bot_token": selected_brand.telegram_bot_token,
            "telegram_webhook_secret": selected_brand.telegram_webhook_secret,
            "allowed_user_ids": selected_brand.allowed_user_ids,
        }

    return {
        "is_super_admin": _is_super_admin(db, user.id),
        "brands": [
            {
                "id": b.id,
                "slug": b.slug,
                "name": b.name,
                "category": b.category,
            }
            for b in brands
        ],
        "selected_brand": brand_data,
        "brand_metrics": brand_metrics,
        "onboarding_checks": onboarding_checks,
        "category_templates": category_templates,
        "user": {"id": user.id, "email": user.email},
    }



@router.get("/api/category-templates")
def get_category_templates(request: Request, db: Session = Depends(get_db_session)) -> dict[str, Any]:
    _require_user(request, db)
    templates_map = _list_category_templates(db)
    return {
        "templates": [
            {"category": category, "template_json": templates_map[category]}
            for category in CATEGORY_CHOICES
        ]
    }


@router.get("/api/category-templates/{category}")
def get_category_template(category: str, request: Request, db: Session = Depends(get_db_session)) -> dict[str, Any]:
    _require_user(request, db)
    normalized = _normalize_brand_category(category)
    return {"category": normalized, "template_json": _get_category_template(db, normalized)}


@router.post("/api/brands/{brand_id}/apply-template")
def apply_template_api(
    brand_id: int,
    payload: ApplyTemplatePayload,
    request: Request,
    db: Session = Depends(get_db_session),
) -> dict[str, Any]:
    user = _require_user(request, db)
    _require_csrf(request, user)
    if not _has_brand_role(db, user.id, brand_id, {"super_admin", "account_manager", "brand_editor"}):
        raise HTTPException(status_code=403, detail="forbidden")

    brand = db.get(Brand, brand_id)
    if not brand:
        raise HTTPException(status_code=404, detail="brand not found")

    normalized = _require_template_category(payload.category)
    template_json = _get_category_template(db, normalized)
    _upsert_brand_prompt_config(db, brand_id, template_json, replace=True)
    brand.category = normalized
    db.commit()

    write_audit_log(
        db,
        action="brand.ai_profile.apply_template",
        brand_id=brand_id,
        user_id=user.id,
        entity_type="brand_prompt_config",
        entity_id=str(brand_id),
        details={"category": normalized},
    )
    return {"ok": True, "brand_id": brand_id, "category": normalized}


@router.get("/api/brands/{brand_id}/ai-config")
def get_brand_ai_config_api(brand_id: int, request: Request, db: Session = Depends(get_db_session)) -> dict[str, Any]:
    user = _require_user(request, db)
    if not _user_can_access_brand(db, user, brand_id):
        raise HTTPException(status_code=403, detail="forbidden")
    brand = db.get(Brand, brand_id)
    if not brand:
        raise HTTPException(status_code=404, detail="brand not found")
    return {
        "brand_id": brand_id,
        "category": brand.category,
        "config": _extract_brand_ai_profile(brand),
    }


@router.put("/api/brands/{brand_id}/ai-config")
def put_brand_ai_config_api(
    brand_id: int,
    payload: dict[str, Any],
    request: Request,
    db: Session = Depends(get_db_session),
) -> dict[str, Any]:
    user = _require_user(request, db)
    _require_csrf(request, user)
    if not _has_brand_role(db, user.id, brand_id, {"super_admin", "account_manager", "brand_editor"}):
        raise HTTPException(status_code=403, detail="forbidden")
    brand = db.get(Brand, brand_id)
    if not brand:
        raise HTTPException(status_code=404, detail="brand not found")

    config_payload = payload.get("config") if isinstance(payload.get("config"), dict) else payload
    validated = validate_ai_config(config_payload)
    _upsert_brand_prompt_config(db, brand_id, validated, replace=True)

    write_audit_log(
        db,
        action="brand.ai_profile.replace",
        brand_id=brand_id,
        user_id=user.id,
        entity_type="brand_prompt_config",
        entity_id=str(brand_id),
    )
    return {"ok": True, "brand_id": brand_id}


@router.patch("/api/brands/{brand_id}/ai-config/{section}")
def patch_brand_ai_config_section_api(
    brand_id: int,
    section: str,
    payload: dict[str, Any],
    request: Request,
    db: Session = Depends(get_db_session),
) -> dict[str, Any]:
    user = _require_user(request, db)
    _require_csrf(request, user)
    if not _has_brand_role(db, user.id, brand_id, {"super_admin", "account_manager", "brand_editor"}):
        raise HTTPException(status_code=403, detail="forbidden")
    brand = db.get(Brand, brand_id)
    if not brand:
        raise HTTPException(status_code=404, detail="brand not found")

    updates = _updates_from_section_payload(section, payload)
    _upsert_brand_prompt_config(db, brand_id, updates)
    write_audit_log(
        db,
        action="brand.ai_profile.patch_section",
        brand_id=brand_id,
        user_id=user.id,
        entity_type="brand_prompt_config",
        entity_id=str(brand_id),
        details={"section": section, "updated_fields": list(updates.keys())},
    )
    return {"ok": True, "brand_id": brand_id, "section": section}


@router.get("/brands")
def list_brands(request: Request, db: Session = Depends(get_db_session)) -> dict[str, Any]:
    user = _require_user(request, db)
    brands = _get_accessible_brands(db, user)
    return {
        "brands": [
            {
                "id": b.id,
                "slug": b.slug,
                "name": b.name,
                "category": b.category,
                "description": b.description,
                "timezone": b.timezone,
                "status": b.status,
            }
            for b in brands
        ]
    }


@router.post("/brands")
def create_brand(payload: BrandCreatePayload, request: Request, db: Session = Depends(get_db_session)) -> dict[str, Any]:
    user = _require_user(request, db)
    _require_csrf(request, user)
    if not _is_super_admin(db, user.id):
        raise HTTPException(status_code=403, detail="forbidden")

    clean_slug = payload.slug.strip()
    clean_name = payload.name.strip()
    existing = db.query(Brand).filter(Brand.slug == clean_slug).first()
    if existing:
        raise HTTPException(status_code=409, detail="brand slug already exists")

    brand = Brand(
        slug=clean_slug,
        name=clean_name,
        category=_require_brand_category(payload.category),
        description=(payload.description or "").strip() or None,
        timezone=payload.timezone,
        telegram_bot_token=payload.telegram_bot_token,
        telegram_webhook_secret=payload.telegram_webhook_secret,
        allowed_user_ids=payload.allowed_user_ids,
    )
    db.add(brand)
    db.commit()
    db.refresh(brand)
    seeded_config = _get_category_template(db, brand.category)
    if payload.primary_product_label:
        seeded_config = deep_merge_config(
            seeded_config,
            {
                "product_vocabulary": {
                    "singular": payload.primary_product_label.strip(),
                    "plural": f"{payload.primary_product_label.strip()}s",
                }
            },
        )
    _upsert_brand_prompt_config(db, brand.id, seeded_config, replace=True)

    write_audit_log(
        db,
        action="brand.create",
        brand_id=brand.id,
        user_id=user.id,
        entity_type="brand",
        entity_id=str(brand.id),
        details={"slug": brand.slug, "name": brand.name, "category": brand.category},
    )

    return {"ok": True, "brand_id": brand.id}


@router.put("/brands/{brand_id}")
def update_brand(brand_id: int, payload: BrandUpdatePayload, request: Request, db: Session = Depends(get_db_session)) -> dict[str, Any]:
    user = _require_user(request, db)
    _require_csrf(request, user)
    if not _has_brand_role(db, user.id, brand_id, {"super_admin", "account_manager"}):
        raise HTTPException(status_code=403, detail="forbidden")

    brand = db.get(Brand, brand_id)
    if not brand:
        raise HTTPException(status_code=404, detail="brand not found")

    updated_fields = {}
    category_changed = False
    if payload.name is not None:
        brand.name = payload.name.strip()
        updated_fields["name"] = brand.name
    if payload.category is not None:
        brand.category = _require_brand_category(payload.category)
        category_changed = True
        updated_fields["category"] = brand.category
    if payload.description is not None:
        brand.description = payload.description.strip() or None
        updated_fields["description"] = brand.description
    if payload.timezone is not None:
        brand.timezone = payload.timezone
        updated_fields["timezone"] = brand.timezone
    
    # Telegram settings
    if payload.telegram_bot_token is not None:
        brand.telegram_bot_token = payload.telegram_bot_token.strip() if payload.telegram_bot_token else None
        updated_fields["telegram_bot_token"] = "***" if brand.telegram_bot_token else None
    if payload.telegram_webhook_secret is not None:
        brand.telegram_webhook_secret = payload.telegram_webhook_secret.strip() if payload.telegram_webhook_secret else None
        updated_fields["telegram_webhook_secret"] = "***" if brand.telegram_webhook_secret else None
    if payload.allowed_user_ids is not None:
        brand.allowed_user_ids = payload.allowed_user_ids.strip() if payload.allowed_user_ids else None
        updated_fields["allowed_user_ids"] = brand.allowed_user_ids

    # Changing category should reset this brand's AI config to the selected category starter template.
    # This updates brand-local config only and does not mutate global category templates.
    if category_changed:
        seeded_config = _get_category_template(db, brand.category)
        _upsert_brand_prompt_config(db, brand.id, seeded_config, replace=True)

    if updated_fields:
        db.commit()
        write_audit_log(
            db,
            action="brand.update",
            brand_id=brand.id,
            user_id=user.id,
            entity_type="brand",
            entity_id=str(brand.id),
            details=updated_fields
        )

    return {"ok": True}


@router.post("/brands/{brand_id}/credentials")
def set_brand_credentials(
    brand_id: int,
    payload: BrandCredentialPayload,
    request: Request,
    db: Session = Depends(get_db_session),
) -> dict[str, Any]:
    user = _require_user(request, db)
    _require_csrf(request, user)
    if not _has_brand_role(db, user.id, brand_id, {"super_admin", "account_manager"}):
        raise HTTPException(status_code=403, detail="forbidden")

    brand = db.get(Brand, brand_id)
    if not brand:
        raise HTTPException(status_code=404, detail="brand not found")

    upsert_brand_credentials(
        db,
        brand_id=brand_id,
        meta_app_id=payload.meta_app_id,
        meta_app_secret=payload.meta_app_secret,
        meta_page_access_token=payload.meta_page_access_token,
        instagram_business_account_id=payload.instagram_business_account_id,
        meta_graph_api_version=payload.meta_graph_api_version,
    )

    write_audit_log(
        db,
        action="brand.credentials.update",
        brand_id=brand_id,
        user_id=user.id,
        entity_type="brand_credentials",
        entity_id=str(brand_id),
    )
    return {"ok": True}


@router.post("/brands/{brand_id}/onboarding/validate")
def validate_onboarding(brand_id: int, request: Request, db: Session = Depends(get_db_session)) -> dict[str, Any]:
    user = _require_user(request, db)
    _require_csrf(request, user)
    if not _has_brand_role(db, user.id, brand_id, {"super_admin", "account_manager", "brand_editor"}):
        raise HTTPException(status_code=403, detail="forbidden")

    brand = db.get(Brand, brand_id)
    if not brand:
        raise HTTPException(status_code=404, detail="brand not found")

    checks = {
        "brand_exists": True,
        "telegram_bot_configured": bool(brand.telegram_bot_token),
        "telegram_webhook_secret": bool(brand.telegram_webhook_secret),
        "meta_credentials_configured": bool(brand.credentials and brand.credentials.instagram_business_account_id),
        **_generation_dependency_checks(),
    }

    write_audit_log(
        db,
        action="brand.onboarding.validate",
        brand_id=brand_id,
        user_id=user.id,
        entity_type="brand",
        entity_id=str(brand_id),
        details=checks,
    )
    return {"ok": True, "checks": checks}


@router.get("/roles")
def list_roles(request: Request, db: Session = Depends(get_db_session)) -> dict[str, Any]:
    _require_user(request, db)
    return {
        "roles": [
            {"name": "super_admin", "description": "Global access to all brands and admin operations."},
            {"name": "account_manager", "description": "Can manage assigned brands, credentials, and publishing."},
            {"name": "brand_editor", "description": "Can edit AI profile and trigger publishing for assigned brands."},
        ]
    }


@router.get("/users")
def list_users(request: Request, db: Session = Depends(get_db_session)) -> dict[str, Any]:
    user = _require_user(request, db)
    if not _is_super_admin(db, user.id):
        raise HTTPException(status_code=403, detail="forbidden")

    users = db.query(User).order_by(User.created_at.desc()).all()
    role_rows = db.query(UserBrandRole).order_by(UserBrandRole.user_id.asc(), UserBrandRole.created_at.asc()).all()
    roles_by_user: dict[int, list[dict[str, Any]]] = {}
    for row in role_rows:
        roles_by_user.setdefault(row.user_id, []).append(
            {"role": row.role, "brand_id": row.brand_id, "created_at": row.created_at}
        )

    return {
        "users": [
            {
                "id": row.id,
                "email": row.email,
                "is_active": row.is_active,
                "last_login_at": row.last_login_at,
                "created_at": row.created_at,
                "roles": roles_by_user.get(row.id, []),
            }
            for row in users
        ]
    }


@router.post("/users")
def create_user(payload: UserCreatePayload, request: Request, db: Session = Depends(get_db_session)) -> dict[str, Any]:
    actor = _require_user(request, db)
    _require_csrf(request, actor)
    if not _is_super_admin(db, actor.id):
        raise HTTPException(status_code=403, detail="forbidden")

    email = payload.email.strip().lower()
    if not email:
        raise HTTPException(status_code=422, detail="email is required")

    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise HTTPException(status_code=409, detail="user already exists")

    record = User(email=email, password_hash=hash_password(payload.password), is_active=payload.is_active)
    db.add(record)
    db.commit()
    db.refresh(record)

    write_audit_log(
        db,
        action="user.create",
        user_id=actor.id,
        entity_type="user",
        entity_id=str(record.id),
        details={"email": record.email, "is_active": record.is_active},
    )
    return {"ok": True, "user_id": record.id}


@router.get("/brands/{brand_id}/members")
def list_brand_members(brand_id: int, request: Request, db: Session = Depends(get_db_session)) -> dict[str, Any]:
    user = _require_user(request, db)
    if not _user_can_access_brand(db, user, brand_id):
        raise HTTPException(status_code=403, detail="forbidden")

    rows = (
        db.query(UserBrandRole, User)
        .join(User, UserBrandRole.user_id == User.id)
        .filter(UserBrandRole.brand_id == brand_id)
        .order_by(UserBrandRole.created_at.asc())
        .all()
    )
    return {
        "members": [
            {
                "user_id": usr.id,
                "email": usr.email,
                "is_active": usr.is_active,
                "role": role.role,
                "brand_id": role.brand_id,
                "created_at": role.created_at,
            }
            for role, usr in rows
        ]
    }


@router.post("/brands/{brand_id}/members")
def add_brand_member(
    brand_id: int,
    payload: BrandMemberPayload,
    request: Request,
    db: Session = Depends(get_db_session),
) -> dict[str, Any]:
    actor = _require_user(request, db)
    _require_csrf(request, actor)
    if not _has_brand_role(db, actor.id, brand_id, {"super_admin", "account_manager"}):
        raise HTTPException(status_code=403, detail="forbidden")
    if not db.get(Brand, brand_id):
        raise HTTPException(status_code=404, detail="brand not found")

    role = _normalize_role(payload.role)
    member = db.get(User, payload.user_id)
    if not member:
        raise HTTPException(status_code=404, detail="user not found")

    existing = (
        db.query(UserBrandRole)
        .filter(UserBrandRole.user_id == payload.user_id, UserBrandRole.brand_id == brand_id, UserBrandRole.role == role)
        .first()
    )
    if existing:
        return {"ok": True, "already_exists": True}

    db.add(UserBrandRole(user_id=payload.user_id, brand_id=brand_id, role=role))
    db.commit()

    write_audit_log(
        db,
        action="brand.member.add",
        brand_id=brand_id,
        user_id=actor.id,
        entity_type="user_brand_role",
        entity_id=f"{payload.user_id}:{brand_id}:{role}",
    )
    return {"ok": True}


@router.delete("/brands/{brand_id}/members/{user_id}")
def remove_brand_member(
    brand_id: int,
    user_id: int,
    role: str,
    request: Request,
    db: Session = Depends(get_db_session),
) -> dict[str, Any]:
    actor = _require_user(request, db)
    _require_csrf(request, actor)
    if not _has_brand_role(db, actor.id, brand_id, {"super_admin", "account_manager"}):
        raise HTTPException(status_code=403, detail="forbidden")

    normalized_role = _normalize_role(role)
    record = (
        db.query(UserBrandRole)
        .filter(UserBrandRole.user_id == user_id, UserBrandRole.brand_id == brand_id, UserBrandRole.role == normalized_role)
        .first()
    )
    if not record:
        raise HTTPException(status_code=404, detail="member role not found")

    db.delete(record)
    db.commit()
    write_audit_log(
        db,
        action="brand.member.remove",
        brand_id=brand_id,
        user_id=actor.id,
        entity_type="user_brand_role",
        entity_id=f"{user_id}:{brand_id}:{normalized_role}",
    )
    return {"ok": True}


@router.get("/posts")
def list_posts(brand_id: int, request: Request, db: Session = Depends(get_db_session)) -> dict[str, Any]:
    user = _require_user(request, db)
    if not _user_can_access_brand(db, user, brand_id):
        raise HTTPException(status_code=403, detail="forbidden")

    posts = (
        db.query(Post)
        .filter(Post.brand_id == brand_id)
        .order_by(Post.created_at.desc())
        .limit(100)
        .all()
    )

    post_ids = [post.id for post in posts]
    variants_by_post: dict[int, list[dict[str, Any]]] = {}
    if post_ids:
        variants = (
            db.query(PostVariant)
            .filter(PostVariant.brand_id == brand_id, PostVariant.post_id.in_(post_ids))
            .order_by(PostVariant.post_id.asc(), PostVariant.variant_index.asc())
            .all()
        )
        variant_ids = [variant.id for variant in variants]
        items_by_variant: dict[int, list[str]] = {}
        if variant_ids:
            rows = (
                db.query(PostVariantItem)
                .filter(PostVariantItem.brand_id == brand_id, PostVariantItem.variant_id.in_(variant_ids))
                .order_by(PostVariantItem.variant_id.asc(), PostVariantItem.position.asc())
                .all()
            )
            for row in rows:
                items_by_variant.setdefault(row.variant_id, []).append(row.image_url)

        for variant in variants:
            variants_by_post.setdefault(variant.post_id, []).append(
                {
                    "variant_index": variant.variant_index,
                    "preview_url": variant.preview_url,
                    "item_urls": items_by_variant.get(variant.id, []),
                    "quality_flags": {
                        "ssim_score": float(variant.ssim_score),
                        "is_valid": bool(variant.is_valid),
                    },
                }
            )

    return {
        "posts": [
            {
                "id": p.id,
                "status": p.status,
                "media_type": p.media_type,
                "reference_url": p.reference_url,
                "scheduled_for": p.scheduled_for,
                "created_at": p.created_at,
                "caption": p.caption,
                "hashtags": p.hashtags,
                "error_code": p.error_code,
                "error_message": p.error_message,
                "selected_variant_index": p.selected_variant_index,
                "detected_media_type": p.detected_media_type,
                "preview_urls": [variant["preview_url"] for variant in variants_by_post.get(p.id, []) if variant.get("preview_url")],
                "variants": variants_by_post.get(p.id, []),
            }
            for p in posts
        ]
    }


@router.post("/posts/{post_id}/schedule")
def schedule_post(
    post_id: int,
    payload: SchedulePayload,
    request: Request,
    db: Session = Depends(get_db_session),
) -> dict[str, Any]:
    user = _require_user(request, db)
    _require_csrf(request, user)

    post = db.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="post not found")
    if not _user_can_access_brand(db, user, post.brand_id):
        raise HTTPException(status_code=403, detail="forbidden")

    post.scheduled_for = payload.scheduled_for
    post.scheduled_timezone = payload.scheduled_timezone
    post.scheduled_by_user_id = user.id
    post.status = PostStatus.SCHEDULED.value
    db.commit()

    write_audit_log(
        db,
        action="post.schedule",
        brand_id=post.brand_id,
        user_id=user.id,
        entity_type="post",
        entity_id=str(post.id),
        details={"scheduled_for": payload.scheduled_for.isoformat(), "timezone": payload.scheduled_timezone},
    )
    return {"ok": True, "post_id": post.id, "status": post.status}


@router.post("/posts/{post_id}/publish")
def publish_post(post_id: int, payload: PublishPayload, request: Request, db: Session = Depends(get_db_session)) -> dict[str, Any]:
    user = _require_user(request, db)
    _require_csrf(request, user)

    post = db.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="post not found")
    if not _has_brand_role(db, user.id, post.brand_id, {"super_admin", "account_manager", "brand_editor"}):
        raise HTTPException(status_code=403, detail="forbidden")

    chat_id = payload.chat_id
    if chat_id is None:
        chat_id = int(post.sessions[0].chat_id) if post.sessions else 0

    publish_post_task.delay(post.id, int(chat_id), str(user.id), post.brand_id)
    write_audit_log(
        db,
        action="post.publish.requested",
        brand_id=post.brand_id,
        user_id=user.id,
        entity_type="post",
        entity_id=str(post.id),
        details={"chat_id": chat_id},
    )
    return {"ok": True, "queued": True}


@router.get("/calendar")
def calendar(brand_id: int, request: Request, db: Session = Depends(get_db_session)) -> dict[str, Any]:
    user = _require_user(request, db)
    if not _user_can_access_brand(db, user, brand_id):
        raise HTTPException(status_code=403, detail="forbidden")

    rows = (
        db.query(Post)
        .filter(Post.brand_id == brand_id, Post.scheduled_for.is_not(None))
        .order_by(Post.scheduled_for.asc())
        .limit(200)
        .all()
    )
    return {
        "calendar": [
            {
                "post_id": row.id,
                "scheduled_for": row.scheduled_for,
                "scheduled_timezone": row.scheduled_timezone,
                "status": row.status,
            }
            for row in rows
        ]
    }


@router.get("/audit-logs")
def audit_logs(brand_id: int | None = None, request: Request = None, db: Session = Depends(get_db_session)) -> dict[str, Any]:
    user = _require_user(request, db)

    query = db.query(AuditLog)
    if brand_id is not None:
        if not _user_can_access_brand(db, user, brand_id):
            raise HTTPException(status_code=403, detail="forbidden")
        query = query.filter(AuditLog.brand_id == brand_id)
    elif not _is_super_admin(db, user.id):
        role_rows = db.query(UserBrandRole).filter(UserBrandRole.user_id == user.id).all()
        brand_ids = [row.brand_id for row in role_rows if row.brand_id is not None]
        query = query.filter(AuditLog.brand_id.in_(brand_ids))

    logs = query.order_by(AuditLog.created_at.desc()).limit(200).all()
    return {
        "audit_logs": [
            {
                "id": log.id,
                "action": log.action,
                "brand_id": log.brand_id,
                "user_id": log.user_id,
                "entity_type": log.entity_type,
                "entity_id": log.entity_id,
                "details": log.details_json,
                "created_at": log.created_at,
            }
            for log in logs
        ]
    }
