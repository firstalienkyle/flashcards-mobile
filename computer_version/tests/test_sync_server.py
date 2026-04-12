import json
import pytest
from data.models import Card
import data.database as db
from sync_server import create_app

@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "_DB_PATH", tmp_path / "test.db")
    db.init_db()
    db.create_deck("Spanish")
    db.create_card(Card(front="hola", back="hello", deck_id=1))
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c

def test_import_adds_new_deck_and_card(client):
    payload = {
        "decks": [{"id": 99, "name": "French", "created_at": "2026-01-01T00:00:00"}],
        "cards": [{"id": 99, "deck_id": 99, "front": "bonjour", "back": "hello",
                   "is_quiz": False, "memory_level": 0.0, "last_reviewed": None,
                   "review_count": 0, "created_at": "2026-01-01T00:00:00"}],
    }
    resp = client.post("/import", json=payload)
    assert resp.status_code == 200

    # Verify deck was created
    decks = db.get_all_decks()
    french = next((d for d in decks if d.name == "French"), None)
    assert french is not None

    # Verify card was created with the desktop's deck id (not phone's id 99)
    cards = db.get_cards_for_deck(french.id)
    assert len(cards) == 1
    assert cards[0].front == "bonjour"


def test_export_returns_decks_and_cards(client):
    resp = client.get("/export")
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert len(data["decks"]) == 1
    assert data["decks"][0]["name"] == "Spanish"
    assert len(data["cards"]) == 1
    assert data["cards"][0]["front"] == "hola"
