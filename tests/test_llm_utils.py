from vak_bot.pipeline.llm_utils import (
    extract_anthropic_response_text,
    extract_openai_response_text,
    normalize_claude_model,
    normalize_gemini_image_model,
    normalize_openai_model,
    parse_json_object,
)


def test_extract_openai_response_text_prefers_output_text() -> None:
    payload = {"output_text": '{"ok": true}'}
    assert extract_openai_response_text(payload) == '{"ok": true}'


def test_extract_openai_response_text_handles_mixed_output_items() -> None:
    payload = {
        "output": [
            {"type": "reasoning"},
            {
                "type": "message",
                "content": [
                    {"type": "output_text", "text": '{"layout_type":"flat-lay"}'},
                ],
            },
        ]
    }
    assert extract_openai_response_text(payload) == '{"layout_type":"flat-lay"}'


def test_extract_anthropic_response_text_joins_text_blocks() -> None:
    payload = {
        "content": [
            {"type": "thinking", "text": "hidden"},
            {"type": "text", "text": '{"caption":"Line one"'},
            {"type": "text", "text": ',"hashtags":"#x"}'},
        ]
    }
    assert extract_anthropic_response_text(payload) == '{"caption":"Line one"\n,"hashtags":"#x"}'


def test_parse_json_object_handles_code_fences() -> None:
    raw = "```json\n{\"caption\":\"hello\"}\n```"
    assert parse_json_object(raw) == {"caption": "hello"}


def test_parse_json_object_handles_prefixed_text() -> None:
    raw = 'Result:\n{"alt_text":"A saree"}\nThanks'
    assert parse_json_object(raw) == {"alt_text": "A saree"}


def test_model_alias_normalization() -> None:
    assert normalize_openai_model("gpt-5-mini-latest") == "gpt-5-mini"
    assert normalize_gemini_image_model("gemini-nano-banana-pro") == "gemini-3-pro-image-preview"
    assert normalize_claude_model("claude-sonet-latest") == "claude-sonnet-4-20250514"
    assert normalize_claude_model("claude sonet latest mode") == "claude-sonnet-4-20250514"
