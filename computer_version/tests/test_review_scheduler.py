import pytest
from datetime import datetime, timedelta
from computer_version.data.models import Card
from computer_version.services.review_scheduler import (
    compute_effective_level,
    build_review_queue,
    answers_match,
    apply_memory_delta,
)

def _card(mem: float, days_ago: float = 0, is_quiz: bool = False) -> Card:
    last = datetime.now() - timedelta(days=days_ago) if days_ago > 0 else None
    return Card(front="Q", back="A", memory_level=mem, last_reviewed=last, is_quiz=is_quiz, id=1)

def test_effective_level_no_decay_when_never_reviewed():
    c = _card(50.0, days_ago=0)
    assert compute_effective_level(c, decay_rate=5.0) == 50.0

def test_effective_level_decays_over_time():
    c = _card(50.0, days_ago=4)
    result = compute_effective_level(c, decay_rate=5.0)
    assert result == pytest.approx(30.0, abs=1.0)

def test_effective_level_floors_at_zero():
    c = _card(10.0, days_ago=20)
    assert compute_effective_level(c, decay_rate=5.0) == 0.0

def test_build_queue_75_25_split():
    import random
    random.seed(42)
    cards = [_card(float(i), days_ago=1) for i in range(1, 21)]  # 20 cards
    queue = build_review_queue(cards, decay_rate=5.0, queue_size=20)
    assert len(queue) == 20

def test_build_queue_fewer_cards_than_size():
    cards = [_card(float(i)) for i in range(1, 6)]  # only 5 cards
    queue = build_review_queue(cards, decay_rate=5.0, queue_size=25)
    assert len(queue) == 5

def test_answers_match_exact():
    assert answers_match("mitochondria", "mitochondria") is True

def test_answers_match_case_insensitive():
    assert answers_match("Mitochondria", "mitochondria") is True

def test_answers_match_strips_punctuation():
    assert answers_match("mitochondria.", "mitochondria") is True

def test_answers_mismatch():
    assert answers_match("nucleus", "mitochondria") is False

def test_apply_memory_delta_flip_first_time():
    c = _card(50.0)
    new_level = apply_memory_delta(c, result="seen", already_seen=False)
    assert new_level == 58.0

def test_apply_memory_delta_flip_repeat():
    c = _card(50.0)
    new_level = apply_memory_delta(c, result="seen", already_seen=True)
    assert new_level == 53.0

def test_apply_memory_delta_quiz_correct():
    c = _card(50.0, is_quiz=True)
    assert apply_memory_delta(c, result="correct", already_seen=False) == 65.0

def test_apply_memory_delta_quiz_wrong():
    c = _card(50.0, is_quiz=True)
    assert apply_memory_delta(c, result="incorrect", already_seen=False) == 40.0

def test_apply_memory_delta_clamps_at_100():
    c = _card(95.0, is_quiz=True)
    assert apply_memory_delta(c, result="correct", already_seen=False) == 100.0

def test_apply_memory_delta_clamps_at_zero():
    c = _card(5.0, is_quiz=True)
    assert apply_memory_delta(c, result="incorrect", already_seen=False) == 0.0
