"""
ClaudeService using direct HTTP requests instead of the anthropic SDK.
The SDK pulls in pydantic-core (Rust) which cannot be cross-compiled for Android.
"""
import base64
import json
import requests
from config import CLAUDE_MODEL

_API_URL = "https://api.anthropic.com/v1/messages"
_API_VERSION = "2023-06-01"


class ClaudeService:
    def __init__(self, api_key: str):
        self.api_key = api_key

    def _headers(self):
        return {
            "x-api-key": self.api_key,
            "anthropic-version": _API_VERSION,
            "content-type": "application/json",
        }

    def _post(self, system: str, user_content, max_tokens: int = 2048) -> str:
        payload = {
            "model": CLAUDE_MODEL,
            "max_tokens": max_tokens,
            "system": system,
            "messages": [{"role": "user", "content": user_content}],
        }
        resp = requests.post(_API_URL, headers=self._headers(),
                             json=payload, timeout=30)
        resp.raise_for_status()
        return resp.json()["content"][0]["text"]

    def _parse_cards(self, raw: str) -> list[dict]:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            raise ValueError(f"Claude returned invalid JSON: {e}\nRaw: {raw[:200]}")
        if not isinstance(data, list):
            raise ValueError(f"Expected list, got {type(data).__name__}")
        return data

    def generate_cards_from_text(self, text: str) -> list[dict]:
        raw = self._post(
            system="You are a flashcard extraction assistant. Always respond with raw JSON only.",
            user_content=(
                "Extract flashcards from the following text.\n"
                "Return a JSON array of objects with keys:\n"
                "  - \"front\": the question or term (string)\n"
                "  - \"back\": the answer or definition (string)\n"
                "  - \"is_quiz\": true only for strict definition cards (boolean)\n"
                "Return ONLY valid JSON.\n\n"
                f"Text:\n{text}"
            ),
        )
        return self._parse_cards(raw)

    def generate_cards_from_image(self, image_bytes: bytes,
                                   media_type: str = "image/jpeg") -> list[dict]:
        image_b64 = base64.standard_b64encode(image_bytes).decode("utf-8")
        raw = self._post(
            system="You are a flashcard extraction assistant. Always respond with raw JSON only.",
            user_content=[
                {
                    "type": "image",
                    "source": {"type": "base64",
                               "media_type": media_type,
                               "data": image_b64},
                },
                {
                    "type": "text",
                    "text": (
                        "Extract flashcards from this image.\n"
                        "Return a JSON array of objects with keys:\n"
                        "  - \"front\": the question or term (string)\n"
                        "  - \"back\": the answer or definition (string)\n"
                        "  - \"is_quiz\": true only for strict definition cards (boolean)\n"
                        "Return ONLY valid JSON."
                    ),
                },
            ],
        )
        return self._parse_cards(raw)

    def explain_answer(self, front: str, back: str) -> str:
        return self._post(
            system="You are a helpful tutor. Be concise.",
            user_content=(
                f"Flashcard:\nQuestion: {front}\nCorrect Answer: {back}\n\n"
                "In 2-3 plain sentences, explain why this is the correct answer."
            ),
            max_tokens=256,
        )
