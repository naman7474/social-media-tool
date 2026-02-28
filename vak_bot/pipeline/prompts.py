from __future__ import annotations

import copy
import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from vak_bot.db.models import Brand, BrandCategoryTemplate, BrandPromptConfig
from vak_bot.db.session import SessionLocal
from vak_bot.schemas.brand_config import build_category_template, deep_merge_config, validate_ai_config

PROMPTS_DIR = Path(__file__).resolve().parents[2] / "prompts"


class SafeDict(dict[str, Any]):
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


def _normalize_category(raw: str | None) -> str:
    value = (raw or "").strip().lower()
    return value or "general"


@lru_cache(maxsize=1)
def _load_analysis_prompt_base() -> str:
    return (PROMPTS_DIR / "analysis_prompt.txt").read_text(encoding="utf-8").strip()


@lru_cache(maxsize=1)
def _load_caption_prompt_base() -> str:
    return (PROMPTS_DIR / "caption_prompt.txt").read_text(encoding="utf-8").strip()


@lru_cache(maxsize=1)
def _load_styling_prompt_base() -> str:
    return (PROMPTS_DIR / "gemini_styling_prompt.txt").read_text(encoding="utf-8").strip()


@lru_cache(maxsize=1)
def _load_default_brand_config() -> dict[str, Any]:
    try:
        return json.loads((PROMPTS_DIR / "brand_config.json").read_text(encoding="utf-8"))
    except Exception:
        return build_category_template("general")


def _active_template_for_category(db, category: str) -> dict[str, Any] | None:
    try:
        row = (
            db.query(BrandCategoryTemplate)
            .filter(
                BrandCategoryTemplate.category == category,
                BrandCategoryTemplate.is_active.is_(True),
            )
            .order_by(BrandCategoryTemplate.created_at.desc(), BrandCategoryTemplate.id.desc())
            .first()
        )
    except Exception:
        return None
    if not row or not isinstance(row.template_json, dict):
        return None
    try:
        return validate_ai_config(row.template_json)
    except Exception:
        return row.template_json


def _extract_int(value: Any, default: int) -> int:
    """Extract integer from value, handling strings like '2200 characters...' or '0-2 emojis'."""
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        import re
        match = re.search(r"(\d+)", value)
        if match:
            return int(match.group(1))
    return default


def _normalize_legacy_config_keys(raw_config: dict[str, Any]) -> dict[str, Any]:
    normalized = copy.deepcopy(raw_config)

    primary_product_label = normalized.pop("primary_product_label", None)
    if isinstance(primary_product_label, str) and primary_product_label.strip():
        vocab = normalized.get("product_vocabulary", {}) if isinstance(normalized.get("product_vocabulary"), dict) else {}
        vocab.setdefault("singular", primary_product_label.strip())
        vocab.setdefault("plural", f"{primary_product_label.strip()}s")
        normalized["product_vocabulary"] = vocab

    if isinstance(normalized.get("saree_display_styles"), dict) and not isinstance(normalized.get("display_styles"), dict):
        normalized["display_styles"] = normalized["saree_display_styles"]

    hashtags = normalized.get("hashtags", {})
    if isinstance(hashtags, dict):
        if isinstance(hashtags.get("product_saree"), list) and not isinstance(hashtags.get("product"), list):
            hashtags["product"] = hashtags["product_saree"]
        normalized["hashtags"] = hashtags

    props = normalized.get("props_library", {})
    if isinstance(props, dict):
        legacy_map = {
            "warm_festive": "warm",
            "calm_minimal": "minimal",
            "rich_luxe": "luxe",
            "earthy_grounded": "earthy",
        }
        for old_key, new_key in legacy_map.items():
            if isinstance(props.get(old_key), list) and not isinstance(props.get(new_key), list):
                props[new_key] = props[old_key]
        normalized["props_library"] = props

    # Normalize brand block - pillars was a list in legacy, remove non-string fields
    brand_block = normalized.get("brand", {})
    if isinstance(brand_block, dict):
        keys_to_remove = [k for k, v in brand_block.items() if not isinstance(v, str)]
        for k in keys_to_remove:
            brand_block.pop(k, None)
        normalized["brand"] = brand_block

    # Normalize caption_rules - fix string values that should be int
    caption_rules = normalized.get("caption_rules", {})
    if isinstance(caption_rules, dict):
        if "max_length" in caption_rules:
            caption_rules["max_length"] = _extract_int(caption_rules["max_length"], 280)
        if "emoji_limit" in caption_rules:
            caption_rules["emoji_limit"] = _extract_int(caption_rules["emoji_limit"], 2)
        normalized["caption_rules"] = caption_rules

    return normalized


def _build_base_template(db: Any | None = None, category: str = "general") -> dict[str, Any]:
    base = copy.deepcopy(_load_default_brand_config())

    if db is not None:
        general_template = _active_template_for_category(db, "general")
        if general_template:
            base = deep_merge_config(base, general_template)

        normalized_category = _normalize_category(category)
        if normalized_category != "general":
            category_template = _active_template_for_category(db, normalized_category)
            if category_template:
                base = deep_merge_config(base, category_template)
    else:
        base = deep_merge_config(base, build_category_template("general"))
        normalized_category = _normalize_category(category)
        if normalized_category != "general":
            base = deep_merge_config(base, build_category_template(normalized_category))

    return base


def load_brand_config(brand_id: int | None = None) -> dict[str, Any]:
    if brand_id is None:
        try:
            with SessionLocal() as db:
                config = _build_base_template(db, category="general")
                return validate_ai_config(config)
        except Exception:
            config = _build_base_template(None, category="general")
            return validate_ai_config(config)

    try:
        with SessionLocal() as db:
            brand = db.get(Brand, brand_id)
            category = _normalize_category(brand.category if brand else None)
            config = _build_base_template(db, category=category)

            row = (
                db.query(BrandPromptConfig)
                .filter(BrandPromptConfig.brand_id == brand_id, BrandPromptConfig.is_active.is_(True))
                .first()
            )
            if row and isinstance(row.config_json, dict):
                config = deep_merge_config(config, _normalize_legacy_config_keys(row.config_json))

            return validate_ai_config(config)
    except Exception:
        config = _build_base_template(None, category="general")
        return validate_ai_config(config)


def load_brand_profile(brand_id: int | None = None) -> dict[str, str]:
    config = load_brand_config(brand_id)
    brand_block = config.get("brand", {}) if isinstance(config.get("brand"), dict) else {}
    product_vocab = config.get("product_vocabulary", {}) if isinstance(config.get("product_vocabulary"), dict) else {}

    profile: dict[str, str] = {
        "brand_name": str(brand_block.get("name") or "").strip(),
        "brand_tagline": str(brand_block.get("tagline") or "").strip(),
        "brand_website": str(brand_block.get("website") or "").strip(),
        "brand_instagram": str(brand_block.get("instagram") or "").strip(),
        "brand_language": str(config.get("language") or "en").strip() or "en",
        "category": "general",
        "description": "",
        "audience_profile": str(config.get("audience_profile") or "").strip(),
        "brand_voice": str(config.get("brand_voice") or "").strip(),
        "llm_guardrails": str(config.get("llm_guardrails") or "").strip(),
        "product_singular": str(product_vocab.get("singular") or "product").strip() or "product",
        "product_plural": str(product_vocab.get("plural") or "products").strip() or "products",
        "product_part_featured": str(product_vocab.get("featured_part") or "detail").strip() or "detail",
    }

    if brand_id is not None:
        try:
            with SessionLocal() as db:
                brand = db.get(Brand, brand_id)
                if brand:
                    profile["brand_name"] = brand.name
                    profile["category"] = _normalize_category(brand.category)
                    profile["description"] = (brand.description or "").strip()
        except Exception:
            pass

    if not profile["brand_name"]:
        profile["brand_name"] = "This brand"

    return profile


def _format_color(color_map: Any) -> str:
    if not isinstance(color_map, dict):
        return "not specified"
    parts = [f"{name} ({value})" for name, value in color_map.items() if isinstance(value, str) and value.strip()]
    return ", ".join(parts) if parts else "not specified"


def _format_display_styles(styles: Any) -> str:
    if not isinstance(styles, dict):
        return ""
    entries = [f"{name}: {desc}" for name, desc in styles.items() if isinstance(desc, str) and desc.strip()]
    return "; ".join(entries)


def _format_props(props: Any) -> str:
    if not isinstance(props, dict):
        return ""
    formatted: list[str] = []
    for key, values in props.items():
        if isinstance(values, list):
            cleaned = [str(v).strip() for v in values if str(v).strip()]
            if cleaned:
                formatted.append(f"{key}: {', '.join(cleaned)}")
    return " ; ".join(formatted)


def _format_hashtags(tags: Any) -> str:
    if not isinstance(tags, dict):
        return ""
    items: list[str] = []
    for values in tags.values():
        if isinstance(values, list):
            items.extend(str(v).strip() for v in values if isinstance(v, str) and v.strip())
    unique = list(dict.fromkeys(items))
    return " ".join(unique[:40])


def _format_ctas(ctas: Any) -> str:
    if not isinstance(ctas, list):
        return ""
    cleaned = [str(v).strip() for v in ctas if str(v).strip()]
    return " | ".join(cleaned)


def _format_occasions(occasions: Any) -> str:
    if not isinstance(occasions, dict):
        return ""
    entries: list[str] = []
    for key in ("festive", "wedding", "everyday", "campaign"):
        values = occasions.get(key)
        if isinstance(values, list) and values:
            joined = ", ".join(str(v).strip() for v in values if str(v).strip())
            if joined:
                entries.append(f"{key}: {joined}")
    return " ; ".join(entries)


def _format_artisans(sample_artisans: Any) -> str:
    if not isinstance(sample_artisans, list):
        return ""
    cleaned = [str(v).strip() for v in sample_artisans if str(v).strip()]
    return ", ".join(cleaned)


def _render_prompt(base_prompt: str, brand_id: int | None) -> str:
    if brand_id is None:
        config = load_brand_config(None)
        profile = load_brand_profile(None)
    else:
        config = load_brand_config(brand_id)
        profile = load_brand_profile(brand_id)

    product_vocabulary = config.get("product_vocabulary", {}) if isinstance(config.get("product_vocabulary"), dict) else {}
    colors = config.get("colors", {}) if isinstance(config.get("colors"), dict) else {}
    visual_identity = config.get("visual_identity", {}) if isinstance(config.get("visual_identity"), dict) else {}

    replacements: dict[str, Any] = {
        "brand_name": profile.get("brand_name", "This brand"),
        "brand_description": profile.get("description", ""),
        "brand_tagline": profile.get("brand_tagline", ""),
        "brand_instagram": profile.get("brand_instagram", ""),
        "brand_language": profile.get("brand_language", "en"),
        "audience_profile": profile.get("audience_profile", ""),
        "brand_voice": profile.get("brand_voice", ""),
        "llm_guardrails": profile.get("llm_guardrails", ""),
        "product_singular": str(product_vocabulary.get("singular") or profile.get("product_singular") or "product"),
        "product_plural": str(product_vocabulary.get("plural") or profile.get("product_plural") or "products"),
        "product_part_featured": str(product_vocabulary.get("featured_part") or profile.get("product_part_featured") or "detail"),
        "product_parts": ", ".join(str(v) for v in (product_vocabulary.get("parts") or {}).values()),
        "primary_color": _format_color(colors.get("primary", {})),
        "secondary_color": _format_color(colors.get("secondary", {})),
        "accent_color": _format_color(colors.get("accent", {})),
        "display_styles": _format_display_styles(config.get("display_styles", {})),
        "props_library": _format_props(config.get("props_library", {})),
        "aesthetic_exclusions": ", ".join(visual_identity.get("avoid", [])) if isinstance(visual_identity.get("avoid"), list) else "",
        "aesthetic_preferences": ", ".join(visual_identity.get("prefer", [])) if isinstance(visual_identity.get("prefer"), list) else "",
        "hashtag_pool": _format_hashtags(config.get("hashtags", {})),
        "banned_words": ", ".join(config.get("caption_rules", {}).get("banned_words", [])) if isinstance(config.get("caption_rules"), dict) else "",
        "cta_options": _format_ctas(config.get("cta_rotation", [])),
        "occasions_list": _format_occasions(config.get("occasions", {})),
        "sample_artisans": _format_artisans(config.get("sample_artisans", [])),
        "variation_modifiers": " | ".join(config.get("variation_modifiers", [])) if isinstance(config.get("variation_modifiers"), list) else "",
    }

    return base_prompt.format_map(SafeDict(replacements))


def load_analysis_prompt(brand_id: int | None = None) -> str:
    return _render_prompt(_load_analysis_prompt_base(), brand_id)


def load_caption_prompt(brand_id: int | None = None) -> str:
    return _render_prompt(_load_caption_prompt_base(), brand_id)


def load_styling_prompt(brand_id: int | None = None) -> str:
    return _render_prompt(_load_styling_prompt_base(), brand_id)


@lru_cache(maxsize=1)
def _load_video_analysis_prompt_base() -> str:
    path = PROMPTS_DIR / "analysis_prompt_video.txt"
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8").strip()


def load_video_analysis_prompt(brand_id: int | None = None) -> str:
    return _render_prompt(_load_video_analysis_prompt_base(), brand_id)


@lru_cache(maxsize=1)
def _load_veo_prompt_base() -> str:
    path = PROMPTS_DIR / "veo_video_prompt.txt"
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8").strip()


def load_veo_prompt(brand_id: int | None = None) -> str:
    return _render_prompt(_load_veo_prompt_base(), brand_id)
