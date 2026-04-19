import random
import re
from datetime import datetime
from typing import Literal
from data.models import Card

def compute_effective_level(card: Card, decay_rate: float) -> float:
    if card.last_reviewed is None:
        return card.memory_level
    days_elapsed = (datetime.now() - card.last_reviewed).total_seconds() / 86400
    stability = 1.0 + card.review_count * 0.4
    effective_decay = decay_rate / stability
    return max(0.0, card.memory_level - effective_decay * days_elapsed)

def build_review_queue(cards: list[Card], decay_rate: float, queue_size: int = 25) -> list[Card]:
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
    def normalize(s: str) -> str:
        s = s.lower().strip()
        s = re.sub(r"[^\w\s]", "", s)
        s = re.sub(r"\s+", " ", s)
        return s
    word_line = correct_answer.splitlines()[0] if correct_answer.strip() else correct_answer
    accepted = [normalize(p) for p in word_line.split("/") if p.strip()]
    return normalize(user_answer) in accepted

def apply_memory_delta(card: Card, result: Literal['seen', 'correct', 'incorrect'], already_seen: bool) -> float:
    level = card.memory_level
    if result == "seen":
        delta = 8 if not already_seen else 3
    elif result == "correct":
        delta = max(30.0, 40.0 - level * 0.1)
    else:
        delta = -(25.0 + level * 0.15)
    return max(0.0, min(100.0, level + delta))
