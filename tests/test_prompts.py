from vak_bot.pipeline.prompts import load_analysis_prompt, load_brand_config, load_caption_prompt


def test_prompt_files_load() -> None:
    assert "visual design analyst" in load_analysis_prompt().lower()
    assert "social media copywriter" in load_caption_prompt().lower()


def test_brand_config_has_variations() -> None:
    cfg = load_brand_config()
    assert len(cfg["variation_modifiers"]) >= 3
    assert "product_vocabulary" in cfg
    assert "product_code_pattern" in cfg
