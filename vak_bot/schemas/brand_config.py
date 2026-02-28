from __future__ import annotations

import copy
from typing import Any

from pydantic import BaseModel, Field


CATEGORY_CHOICES = ("fashion", "furniture", "food", "beauty", "general")


class ProductVocabulary(BaseModel):
    singular: str = "product"
    plural: str = "products"
    featured_part: str | None = "detail"
    parts: dict[str, str] = Field(default_factory=dict)


class ColorPalette(BaseModel):
    primary: dict[str, str] = Field(default_factory=lambda: {"charcoal": "#2C2C2C", "cream": "#F5F0E8"})
    secondary: dict[str, str] = Field(default_factory=dict)
    accent: dict[str, str] = Field(default_factory=dict)
    usage_rules: dict[str, Any] = Field(default_factory=dict)


class TypographyConfig(BaseModel):
    heading_feel: str = "Editorial serif"
    body_feel: str = "Readable sans"
    overlay_feel: str = "Simple display type"
    rules: list[str] = Field(default_factory=list)


class VisualIdentity(BaseModel):
    grid_aesthetic: str = "Curated, uncluttered, and premium"
    dominant_mood: str = "Warm and intentional"
    avoid: list[str] = Field(default_factory=list)
    prefer: list[str] = Field(default_factory=list)


class HashtagConfig(BaseModel):
    brand_always: list[str] = Field(default_factory=list)
    craft: list[str] = Field(default_factory=list)
    product: list[str] = Field(default_factory=list)
    product_other: list[str] = Field(default_factory=list)
    discovery: list[str] = Field(default_factory=list)
    occasion_festive: list[str] = Field(default_factory=list)
    occasion_wedding: list[str] = Field(default_factory=list)
    occasion_everyday: list[str] = Field(default_factory=list)
    niche: list[str] = Field(default_factory=list)
    never_use: list[str] = Field(default_factory=list)


class CaptionRules(BaseModel):
    optimal_length: str = "150-220 words"
    max_length: int = 280
    emoji_limit: int = 2
    must_mention: list[str] = Field(default_factory=list)
    banned_words: list[str] = Field(default_factory=list)


class OccasionConfig(BaseModel):
    festive: list[str] = Field(default_factory=list)
    wedding: list[str] = Field(default_factory=list)
    everyday: list[str] = Field(default_factory=list)
    campaign: list[str] = Field(default_factory=list)
    content_mix: dict[str, int] = Field(default_factory=lambda: {"hero": 50, "lifestyle": 25, "detail": 25})


class BrandAIConfig(BaseModel):
    brand: dict[str, str] = Field(default_factory=dict)
    language: str = "en"
    product_code_pattern: str = r"\b[A-Z]{2,12}-\d{2,}\b"
    product_vocabulary: ProductVocabulary = Field(default_factory=ProductVocabulary)
    colors: ColorPalette = Field(default_factory=ColorPalette)
    typography: TypographyConfig = Field(default_factory=TypographyConfig)
    visual_identity: VisualIdentity = Field(default_factory=VisualIdentity)
    props_library: dict[str, list[str]] = Field(default_factory=dict)
    display_styles: dict[str, str] = Field(default_factory=dict)
    variation_modifiers: list[str] = Field(default_factory=list)
    hashtags: HashtagConfig = Field(default_factory=HashtagConfig)
    caption_rules: CaptionRules = Field(default_factory=CaptionRules)
    occasions: OccasionConfig = Field(default_factory=OccasionConfig)
    cta_rotation: list[str] = Field(default_factory=list)
    sample_artisans: list[str] = Field(default_factory=list)
    audience_profile: str = ""
    brand_voice: str = ""
    llm_guardrails: str = ""


def deep_merge_config(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge_config(merged[key], value)
        else:
            merged[key] = copy.deepcopy(value)
    return merged


def _general_template() -> dict[str, Any]:
    return {
        "brand": {
            "name": "",
            "tagline": "",
            "website": "",
            "instagram": "",
        },
        "language": "en",
        "product_code_pattern": r"\b[A-Z]{2,12}-\d{2,}\b",
        "product_vocabulary": {
            "singular": "product",
            "plural": "products",
            "featured_part": "detail",
            "parts": {},
        },
        "colors": {
            "primary": {
                "charcoal": "#2C2C2C",
                "cream": "#F5F0E8",
            },
            "secondary": {
                "stone": "#B7B0A8",
                "sage": "#7A8B6F",
            },
            "accent": {
                "warm_gold": "#C9A96E",
            },
            "usage_rules": {
                "text_on_dark_bg": "#F5F0E8",
                "text_on_light_bg": "#2C2C2C",
                "never_use": ["neon", "oversaturated gradients"],
            },
        },
        "typography": {
            "heading_feel": "Editorial serif",
            "body_feel": "Clean sans-serif",
            "overlay_feel": "Elegant display text",
            "rules": [
                "Use sentence case",
                "Keep overlay text short",
            ],
        },
        "visual_identity": {
            "grid_aesthetic": "Curated, spacious, and tactile",
            "dominant_mood": "Warm premium",
            "avoid": [
                "Busy cluttered compositions",
                "Harsh direct flash",
                "Cheap stock image look",
            ],
            "prefer": [
                "Generous whitespace",
                "Natural light or soft studio light",
                "Textured physical backgrounds",
            ],
        },
        "props_library": {
            "warm": ["ceramic bowl", "textured linen", "dried florals"],
            "minimal": ["single stem", "neutral paper", "matte stone"],
            "luxe": ["brass tray", "smoked glass", "silk ribbon"],
            "earthy": ["wood surface", "terracotta", "jute fabric"],
            "never_use": ["plastic props", "brand logos", "novelty decor"],
        },
        "display_styles": {
            "hero-closeup": "Tight frame on hero detail",
            "flat-lay": "Top-down clean arrangement",
            "lifestyle": "In-use context scene",
            "texture-detail": "Macro detail showing material quality",
        },
        "variation_modifiers": [
            "Minimal and gallery-like with high whitespace.",
            "Warm and intimate with tactile textures.",
            "Editorial and bold with controlled contrast.",
        ],
        "hashtags": {
            "brand_always": ["#craftedwithintent"],
            "craft": ["#handcrafted", "#designprocess"],
            "product": ["#productdesign", "#newdrop"],
            "product_other": ["#collection", "#limitedrun"],
            "discovery": ["#brandstory", "#smallbusiness"],
            "occasion_festive": ["#celebrationstyle"],
            "occasion_wedding": ["#eventstyle"],
            "occasion_everyday": ["#everydaystyle"],
            "niche": ["#materialculture"],
            "never_use": ["#fyp", "#viral", "#trending"],
        },
        "caption_rules": {
            "optimal_length": "150-220 words",
            "max_length": 280,
            "emoji_limit": 2,
            "must_mention": [],
            "banned_words": [
                "must-have",
                "best ever",
                "limited stock hurry",
            ],
        },
        "occasions": {
            "festive": ["festivals", "seasonal gifting"],
            "wedding": ["wedding guest", "celebration dinner"],
            "everyday": ["workday", "weekend outing"],
            "campaign": ["new launch", "maker spotlight"],
            "content_mix": {
                "hero": 50,
                "lifestyle": 25,
                "detail": 25,
            },
        },
        "cta_rotation": [
            "Save this look for later.",
            "Tell us which detail stood out to you.",
            "DM us for availability.",
        ],
        "sample_artisans": ["Aarav", "Meera", "Naina"],
        "audience_profile": "People who value quality and design-led storytelling.",
        "brand_voice": "Warm, clear, and confident.",
        "llm_guardrails": "Avoid hype, avoid aggressive sales language, avoid competitor mentions.",
    }


CATEGORY_TEMPLATE_OVERRIDES: dict[str, dict[str, Any]] = {
    "fashion": {
        "product_vocabulary": {
            "singular": "garment",
            "plural": "garments",
            "featured_part": "silhouette",
            "parts": {
                "neckline": "Neckline",
                "hem": "Hem",
                "sleeve": "Sleeve",
            },
        },
        "props_library": {
            "warm": ["brass bangle", "silk drape", "fresh flowers"],
            "minimal": ["matte hanger", "plain backdrop", "single accessory"],
            "luxe": ["mirror tray", "pearl string", "velvet base"],
            "earthy": ["jute mat", "wood stool", "terracotta vase"],
            "never_use": ["plastic mannequins", "discount stickers"],
        },
        "display_styles": {
            "draped-flowing": "Fabric movement with soft folds",
            "flat-lay-folded": "Folded product with hero detail visible",
            "on-model-editorial": "Worn look with premium framing",
            "detail-border": "Close crop of edge detail",
        },
        "hashtags": {
            "craft": ["#artisanmade", "#slowfashion", "#handfinished"],
            "product": ["#fashiondesign", "#statementstyle", "#wardrobestory"],
            "discovery": ["#fashionbrand", "#consciousfashion", "#madeinindia"],
        },
        "occasions": {
            "festive": ["festive dressing", "cocktail evening"],
            "wedding": ["wedding guest", "engagement celebration"],
            "everyday": ["brunch look", "work event"],
        },
    },
    "furniture": {
        "product_vocabulary": {
            "singular": "furniture piece",
            "plural": "furniture pieces",
            "featured_part": "finish",
            "parts": {
                "arm": "Arm",
                "base": "Base",
                "upholstery": "Upholstery",
            },
        },
        "props_library": {
            "warm": ["ceramic vase", "linen throw", "wood side table"],
            "minimal": ["neutral wall", "single sculpture", "plain rug"],
            "luxe": ["marble top", "metal lamp", "art book"],
            "earthy": ["clay pot", "woven basket", "raw wood"],
            "never_use": ["cluttered decor", "fake plants"],
        },
        "display_styles": {
            "room-hero": "Product as focal point in a styled room",
            "detail-material": "Close-up on grain, stitch, or joinery",
            "angled-perspective": "Three-quarter view showing depth",
            "paired-styling": "Piece shown with complementary decor",
        },
        "hashtags": {
            "craft": ["#interiordesign", "#craftedfurniture", "#materiality"],
            "product": ["#furnituredesign", "#homedecor", "#spaces"],
            "discovery": ["#interiors", "#designstudio", "#homeinspo"],
        },
        "occasions": {
            "festive": ["holiday hosting", "seasonal refresh"],
            "wedding": ["new home setup", "registry picks"],
            "everyday": ["daily living", "work from home"],
        },
    },
    "food": {
        "product_vocabulary": {
            "singular": "dish",
            "plural": "dishes",
            "featured_part": "garnish",
            "parts": {
                "texture": "Texture",
                "topping": "Topping",
                "plating": "Plating",
            },
        },
        "props_library": {
            "warm": ["wood board", "linen napkin", "cutlery"],
            "minimal": ["plain plate", "clean table", "single herb"],
            "luxe": ["stoneware", "wine glass", "metal cutlery"],
            "earthy": ["terracotta bowl", "kraft paper", "fresh produce"],
            "never_use": ["neon backgrounds", "oversized logos"],
        },
        "display_styles": {
            "plated-hero": "Close hero shot of plated item",
            "overhead-spread": "Top-down composition with supporting items",
            "pour-action": "Action shot showing movement",
            "ingredient-story": "Dish with key ingredient context",
        },
        "hashtags": {
            "craft": ["#foodcraft", "#chefmade", "#freshingredients"],
            "product": ["#foodphotography", "#restaurantlife", "#menufeature"],
            "discovery": ["#foodie", "#eatlocal", "#culinary"],
        },
        "occasions": {
            "festive": ["festival menu", "holiday specials"],
            "wedding": ["event catering", "celebration table"],
            "everyday": ["weekday meal", "quick bite"],
        },
    },
    "beauty": {
        "product_vocabulary": {
            "singular": "beauty product",
            "plural": "beauty products",
            "featured_part": "formula texture",
            "parts": {
                "finish": "Finish",
                "applicator": "Applicator",
                "packaging": "Packaging",
            },
        },
        "props_library": {
            "warm": ["stone tray", "soft towel", "fresh petals"],
            "minimal": ["clear acrylic", "white tile", "single dropper"],
            "luxe": ["glass vessel", "gold hardware", "mirror surface"],
            "earthy": ["clay bowl", "botanical stems", "linen cloth"],
            "never_use": ["busy glitter backgrounds", "cheap plastic props"],
        },
        "display_styles": {
            "texture-swatch": "Close-up texture spread or swatch",
            "product-stack": "Layered bottles/jars in clean arrangement",
            "shelfie-curated": "Styled skincare shelf composition",
            "ritual-lifestyle": "In-use routine context",
        },
        "hashtags": {
            "craft": ["#cleanbeauty", "#skincareroutine", "#beautyritual"],
            "product": ["#beautybrand", "#skincare", "#cosmetics"],
            "discovery": ["#selfcare", "#glowskin", "#wellness"],
        },
        "occasions": {
            "festive": ["holiday glam", "party prep"],
            "wedding": ["bridal prep", "event makeup"],
            "everyday": ["daily routine", "morning ritual"],
        },
    },
    "general": {},
}


def build_category_template(category: str) -> dict[str, Any]:
    normalized = (category or "general").strip().lower()
    if normalized not in CATEGORY_CHOICES:
        normalized = "general"
    base = _general_template()
    override = CATEGORY_TEMPLATE_OVERRIDES.get(normalized, {})
    merged = deep_merge_config(base, override)
    return validate_ai_config(merged)


def get_category_template_map() -> dict[str, dict[str, Any]]:
    return {category: build_category_template(category) for category in CATEGORY_CHOICES}


def validate_ai_config(data: dict[str, Any]) -> dict[str, Any]:
    model = BrandAIConfig.model_validate(data)
    return model.model_dump(mode="json")
