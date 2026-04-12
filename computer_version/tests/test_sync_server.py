import json
import pytest
from computer_version.data.models import Card
import computer_version.data.database as db
from computer_version.sync_server import create_app

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

def test_export_returns_decks_and_cards(client):
    resp = client.get("/export")
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert len(data["decks"]) == 1
    assert data["decks"][0]["name"] == "Spanish"
    assert len(data["cards"]) == 1
    assert data["cards"][0]["front"] == "hola"
