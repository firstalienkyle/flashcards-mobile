import base64
import json
import anthropic
from computer_version.config import CLAUDE_MODEL

class ClaudeService:
    def __init__(self, api_key: str):
        self.client = anthropic.Anthropic(api_key=api_key)

    def _parse_cards(self, raw: str) -> list[dict]:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            raise ValueError(f"Claude returned invalid JSON: {e}\nRaw: {raw[:200]}")
        if not isinstance(data, list):
            raise ValueError(f"Claude returned unexpected JSON type (expected list): {type(data).__name__}\nRaw: {raw[:200]}")
        return data

    def generate_cards_from_text(self, text: str) -> list[dict]:
        """Extract flashcard pairs from plain text. Returns list of {front, back, is_quiz}."""
        response = self.client.messages.create(
            system="You are a flashcard extraction assistant. Always respond with raw JSON only — no markdown formatting, no code fences, no commentary.",
            model=CLAUDE_MODEL,
            max_tokens=2048,
            messages=[{
                "role": "user",
                "content": (
                    "Extract flashcards from the following text.\n"
                    "Return a JSON array of objects with keys:\n"
                    "  - \"front\": the question or term (string)\n"
                    "  - \"back\": the answer or definition (string)\n"
                    "  - \"is_quiz\": true only for strict definition cards where the user must recall the exact term (boolean)\n"
                    "Return ONLY valid JSON — no markdown, no commentary.\n\n"
                    f"Text:\n{text}"
                )
            }]
        )
        return self._parse_cards(response.content[0].text)

    def generate_cards_from_image(self, image_bytes: bytes, media_type: str = "image/jpeg") -> list[dict]:
        """Extract flashcard pairs from an image via Claude Vision. Returns list of {front, back, is_quiz}."""
        image_b64 = base64.standard_b64encode(image_bytes).decode("utf-8")
        response = self.client.messages.create(
            system="You are a flashcard extraction assistant. Always respond with raw JSON only — no markdown formatting, no code fences, no commentary.",
            model=CLAUDE_MODEL,
            max_tokens=2048,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_b64,
                        },
                    },
                    {
                        "type": "text",
                        "text": (
                            "Extract flashcards from this image.\n"
                            "Return a JSON array of objects with keys:\n"
                            "  - \"front\": the question or term (string)\n"
                            "  - \"back\": the answer or definition (string)\n"
                            "  - \"is_quiz\": true only for strict definition cards (boolean)\n"
                            "Return ONLY valid JSON — no markdown, no commentary."
                        ),
                    },
                ],
            }]
        )
        return self._parse_cards(response.content[0].text)

    def explain_answer(self, front: str, back: str) -> str:
        """Return a short explanation of why `back` is the correct answer to `front`."""
        response = self.client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=256,
            messages=[{
                "role": "user",
                "content": (
                    f"Flashcard:\nQuestion: {front}\nCorrect Answer: {back}\n\n"
                    "In 2–3 plain sentences, explain why this is the correct answer. "
                    "Be concise and clear."
                )
            }]
        )
        return response.content[0].text.strip()
