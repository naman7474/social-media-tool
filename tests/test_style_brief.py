from vak_bot.schemas import StyleBrief


def test_style_brief_validation() -> None:
    payload = {
        "layout_type": "flat-lay",
        "composition": {
            "product_placement": "center",
            "whitespace": "moderate",
            "text_area": "bottom",
            "aspect_ratio": "4:5",
        },
        "color_mood": {
            "temperature": "warm",
            "dominant_colors": ["#AABBCC", "#DDEEFF"],
            "palette_name": "earthy",
        },
        "background": {
            "type": "textured",
            "description": "Soft linen texture",
            "suggested_background": "Warm neutral fabric with soft handcrafted accents",
        },
        "lighting": "natural-soft",
        "text_overlay": {
            "has_text": False,
            "text_style": "none",
            "text_position": "none",
            "text_purpose": "none",
        },
        "content_format": "single-image",
        "vibe_words": ["warm", "artisan"],
        "adaptation_notes": "Keep saree unchanged",
    }

    brief = StyleBrief.model_validate(payload)
    assert brief.layout_type == "flat-lay"
    assert brief.composition.aspect_ratio == "4:5"


def test_style_brief_accepts_legacy_background_key() -> None:
    brief = StyleBrief.model_validate(
        {
            "layout_type": "flat-lay",
            "color_mood": {
                "temperature": "warm",
                "dominant_colors": ["#AABBCC"],
                "palette_name": "earthy",
            },
            "background": {
                "suggested_bg_for_saree": "Neutral backdrop",
            },
            "vibe_words": ["warm", "artisan"],
        }
    )
    assert brief.background.suggested_background == "Neutral backdrop"
