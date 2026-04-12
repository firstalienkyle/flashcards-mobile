import json
import pytest
from unittest.mock import patch, MagicMock
from sync_client import SyncClient

@pytest.fixture
def client():
    return SyncClient(base_url="http://192.168.1.1:5000")

def test_pull_replaces_local_db(client, tmp_path, monkeypatch):
    import data.database as db
    monkeypatch.setattr("data.database._DB_PATH", tmp_path / "test.db")
    db.init_db()

    mock_response = MagicMock()
    mock_response.json.return_value = {
        "decks": [{"id": 1, "name": "Spanish", "created_at": "2026-01-01T00:00:00"}],
        "cards": [{"id": 1, "deck_id": 1, "front": "hola", "back": "hello",
                   "is_quiz": False, "memory_level": 0.0, "last_reviewed": None,
                   "review_count": 0, "created_at": "2026-01-01T00:00:00"}],
    }
    mock_response.raise_for_status = MagicMock()

    with patch("requests.get", return_value=mock_response):
        client.pull()

    decks = db.get_all_decks()
    assert len(decks) == 1
    assert decks[0].name == "Spanish"

def test_push_posts_local_db(client, tmp_path, monkeypatch):
    import data.database as db
    monkeypatch.setattr("data.database._DB_PATH", tmp_path / "test.db")
    db.init_db()
    db.create_deck("Spanish")
    from data.models import Card
    db.create_card(Card(front="adios", back="goodbye", deck_id=1))

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()

    with patch("requests.post", return_value=mock_response) as mock_post:
        client.push()

    assert mock_post.called
    payload = mock_post.call_args[1]["json"]
    assert payload["decks"][0]["name"] == "Spanish"
    assert payload["cards"][0]["front"] == "adios"
