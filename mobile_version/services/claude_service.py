import base64
import json
import anthropic
from config import CLAUDE_MODEL

class ClaudeService:
    def __init__(self, api_key: str):
        self.client = anthropic.Anthropic(api_key=api_key)

    def _parse_cards(self, raw: str) -> list[dict]:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            raise ValueError(f"Claude returned invalid JSON: {e}\nRaw: {raw[:200]}")
        if not isinstance(data, list):
            raise ValueError(f"Claude returned unexpected type: {type(data).__name__}")
        return data

    def generate_cards_from_text(self, text: str) -> list[dict]:
        response = self.client.messages.create(
            system="You are a flashcard extraction assistant. Always respond with raw JSON only.",
            model=CLAUDE_MODEL,
            max_tokens=2048,
            messages=[{"role": "user", "content": (
                "Extract flashcards from the following text.\n"
                "Return a JSON array of objects with keys:\n"
                "  - \"front\": the question or term (string)\n"
                "  - \"back\": the answer or definition (string)\n"
                "  - \"is_quiz\": true only for strict definition cards (boolean)\n"
                "Return ONLY valid JSON.\n\n"
                f"Text:\n{text}"
            )}]
        )
        return self._parse_cards(response.content[0].text)

    def explain_answer(self, front: str, back: str) -> str:
        response = self.client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=256,
            messages=[{"role": "user", "content": (
                f"Flashcard:\nQuestion: {front}\nCorrect Answer: {back}\n\n"
                "In 2-3 plain sentences, explain why this is the correct answer."
            )}]
        )
        return response.content[0].text.strip()
