import json
import pytest
from unittest.mock import MagicMock, patch
from services.claude_service import ClaudeService

@pytest.fixture
def svc():
    return ClaudeService(api_key="test-key")

def _mock_response(text: str):
    msg = MagicMock()
    msg.content = [MagicMock(text=text)]
    return msg

def test_generate_cards_from_text_parses_json(svc):
    payload = json.dumps([
        {"front": "What is ATP?", "back": "Energy currency of the cell", "is_quiz": True}
    ])
    with patch.object(svc.client.messages, "create", return_value=_mock_response(payload)):
        cards = svc.generate_cards_from_text("Some biology notes")
    assert len(cards) == 1
    assert cards[0]["front"] == "What is ATP?"
    assert cards[0]["is_quiz"] is True

def test_generate_cards_from_image_parses_json(svc):
    payload = json.dumps([{"front": "Capital of France?", "back": "Paris", "is_quiz": False}])
    with patch.object(svc.client.messages, "create", return_value=_mock_response(payload)):
        cards = svc.generate_cards_from_image(b"fake_image_bytes")
    assert cards[0]["back"] == "Paris"

def test_explain_answer_returns_string(svc):
    with patch.object(svc.client.messages, "create",
                      return_value=_mock_response("Because it produces ATP via oxidative phosphorylation.")):
        explanation = svc.explain_answer(
            front="What is the powerhouse of the cell?",
            back="Mitochondria"
        )
    assert "ATP" in explanation

def test_generate_cards_raises_on_invalid_json(svc):
    with patch.object(svc.client.messages, "create", return_value=_mock_response("not json")):
        with pytest.raises(ValueError, match="Claude returned invalid JSON"):
            svc.generate_cards_from_text("text")
