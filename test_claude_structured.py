"""Quick smoke test: verify Claude structured outputs works with our exact payload shape."""
import json
import os
import httpx

API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
if not API_KEY:
    print("ERROR: Set ANTHROPIC_API_KEY env var")
    exit(1)

caption_schema = {
    "type": "object",
    "properties": {
        "caption": {"type": "string", "description": "A short test caption"},
        "hashtags": {"type": "string", "description": "Space-separated hashtags"},
        "alt_text": {"type": "string", "description": "Image alt text"},
        "overlay_text": {
            "type": ["string", "null"],
            "description": "Optional overlay text or null",
        },
    },
    "required": ["caption", "hashtags", "alt_text"],
    "additionalProperties": False,
}

payload = {
    "model": "claude-sonnet-4-6",
    "max_tokens": 300,
    "messages": [
        {
            "role": "user",
            "content": "Write a test Instagram caption for a hand-painted saree. Keep it short.",
        }
    ],
    "output_config": {
        "format": {
            "type": "json_schema",
            "schema": caption_schema,
        }
    },
}

headers = {
    "x-api-key": API_KEY,
    "anthropic-version": "2023-06-01",
    "content-type": "application/json",
}

print("Sending request to Claude API...")
print(f"Headers: { {k: v if k != 'x-api-key' else '***' for k, v in headers.items()} }")
print(f"Payload keys: {list(payload.keys())}")
print(f"output_config: {json.dumps(payload['output_config'], indent=2)}")
print()

with httpx.Client(timeout=60.0) as client:
    response = client.post("https://api.anthropic.com/v1/messages", headers=headers, json=payload)
    print(f"Status: {response.status_code}")
    data = response.json()
    if response.status_code != 200:
        print(f"ERROR: {json.dumps(data, indent=2)}")
        exit(1)

    text = data["content"][0]["text"]
    print(f"Raw response text: {text}")
    parsed = json.loads(text)
    print(f"Parsed JSON: {json.dumps(parsed, indent=2)}")
    print(f"\nAll keys present: {set(parsed.keys())}")
    print("SUCCESS!")
