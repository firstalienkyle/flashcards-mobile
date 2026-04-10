import random
import re
from datetime import datetime
from typing import Optional
from data.models import Card

def compute_effective_level(card: Card, decay_rate: float) -> float:
    """Memory level after applying time-based decay."""
    if card.last_reviewed is None:
        return card.memory_level
    days_elapsed = (datetime.now() - card.last_reviewed).total_seconds() / 86400
    return max(0.0, card.memory_level - decay_rate * days_elapsed)

def build_review_queue(cards: list[Card], decay_rate: float, queue_size: int = 25) -> list[Card]:
    """75% lowest-memory cards + 25% random from the rest, shuffled."""
    if not cards:
        return []

    sorted_cards = sorted(cards, key=lambda c: compute_effective_level(c, decay_rate))

    n_priority = max(1, int(min(queue_size, len(cards)) * 0.75))
    priority = sorted_cards[:n_priority]
    remaining = sorted_cards[n_priority:]

    n_random = min(queue_size - len(priority), len(remaining))
    random_pick = random.sample(remaining, n_random) if n_random > 0 else []

    queue = priority + random_pick
    random.shuffle(queue)
    return queue[:queue_size]

def answers_match(user_answer: str, correct_answer: str) -> bool:
    """Case-insensitive, punctuation-stripped comparison."""
    def normalize(s: str) -> str:
        s = s.lower().strip()
        s = re.sub(r"[^\w\s]", "", s)
        s = re.sub(r"\s+", " ", s)
        return s
    return normalize(user_answer) == normalize(correct_answer)

def apply_memory_delta(card: Card, result: str, already_seen: bool) -> float:
    """
    result: 'seen' (regular flip), 'correct' (quiz), 'incorrect' (quiz)
    already_seen: True if this card was already reviewed earlier in this session.
    Returns new memory_level (clamped 0–100).
    """
    level = card.memory_level
    if result == "seen":
        delta = 0 if already_seen else 10
    elif result == "correct":
        delta = 20
    else:  # incorrect
        delta = -10
    return max(0.0, min(100.0, level + delta))
