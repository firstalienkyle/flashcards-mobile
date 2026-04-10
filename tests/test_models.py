from datetime import datetime
from data.models import Card, Deck, ReviewSession, SessionCard

def test_card_defaults():
    c = Card(front="Q", back="A")
    assert c.memory_level == 50.0
    assert c.is_quiz is False
    assert c.id is None
    assert c.deck_id is None
    assert c.last_reviewed is None
    assert isinstance(c.created_at, datetime)

def test_card_quiz():
    c = Card(front="Q", back="A", is_quiz=True)
    assert c.is_quiz is True

def test_deck_defaults():
    d = Deck(name="Biology")
    assert d.name == "Biology"
    assert d.id is None
    assert isinstance(d.created_at, datetime)

def test_review_session_defaults():
    s = ReviewSession()
    assert s.cards_reviewed == 0
    assert s.ended_at is None

def test_session_card():
    sc = SessionCard(session_id=1, card_id=2, result="seen",
                     memory_before=50.0, memory_after=60.0)
    assert sc.result == "seen"
    assert sc.id is None
    assert isinstance(sc.reviewed_at, datetime)
