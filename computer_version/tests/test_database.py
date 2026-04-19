import sqlite3
import pytest
from datetime import datetime
from computer_version.data.models import Card, Deck
import computer_version.data.database as db

@pytest.fixture(autouse=True)
def use_memory_db(monkeypatch, tmp_path):
    """Redirect all DB calls to a fresh in-memory DB for each test."""
    test_db = tmp_path / "test.db"
    monkeypatch.setattr(db, "_DB_PATH", test_db)
    db.init_db()

def test_create_and_get_deck():
    d = db.create_deck("Biology")
    assert d.id is not None
    decks = db.get_all_decks()
    assert len(decks) == 1
    assert decks[0].name == "Biology"

def test_rename_deck():
    d = db.create_deck("Bio")
    db.rename_deck(d.id, "Biology")
    assert db.get_all_decks()[0].name == "Biology"

def test_delete_deck_cascades():
    d = db.create_deck("Temp")
    c = Card(front="Q", back="A", deck_id=d.id)
    db.create_card(c)
    db.delete_deck(d.id)
    assert db.get_all_decks() == []
    assert db.get_all_cards() == []

def test_create_and_get_card():
    d = db.create_deck("Bio")
    c = Card(front="Q", back="A", deck_id=d.id)
    saved = db.create_card(c)
    assert saved.id is not None
    cards = db.get_cards_for_deck(d.id)
    assert len(cards) == 1
    assert cards[0].front == "Q"

def test_update_card():
    d = db.create_deck("Bio")
    c = db.create_card(Card(front="Q", back="A", deck_id=d.id))
    c.back = "Updated"
    db.update_card(c)
    assert db.get_cards_for_deck(d.id)[0].back == "Updated"

def test_update_card_memory():
    d = db.create_deck("Bio")
    c = db.create_card(Card(front="Q", back="A", deck_id=d.id))
    now = datetime.now()
    db.update_card_memory(c.id, 70.0, now)
    updated = db.get_cards_for_deck(d.id)[0]
    assert updated.memory_level == 70.0
    assert updated.last_reviewed is not None

def test_settings_defaults():
    assert db.get_setting("daily_goal") == "20"
    assert db.get_setting("decay_rate") == ""

def test_set_and_get_setting():
    db.set_setting("daily_goal", "30")
    assert db.get_setting("daily_goal") == "30"

def test_get_today_reviewed_count():
    s = db.create_session()
    db.record_session_card_result(s.id, card_id=1, result="seen",
                                  memory_before=50, memory_after=60)
    db.record_session_card_result(s.id, card_id=2, result="correct",
                                  memory_before=40, memory_after=60)
    assert db.get_today_reviewed_count() == 2
