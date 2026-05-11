import random
import re
from datetime import datetime
from typing import Literal
from data.models import Card

def compute_effective_level(card: Card, decay_rate: float) -> float:
    if card.last_reviewed is None:
        return card.memory_level
    days_elapsed = (datetime.now() - card.last_reviewed).total_seconds() / 86400
    # Stability increases with both review_count AND mastery_count (each mastery = bigger interval)
    stability = 1.0 + card.review_count * 0.4 + card.mastery_count * 2.0
    effective_decay = decay_rate / stability
    return max(0.0, card.memory_level - effective_decay * days_elapsed)

def build_review_queue(cards: list[Card], decay_rate: float, queue_size: int = 25) -> list[Card]:
    if not cards:
        return []
    scored = sorted(cards, key=lambda c: compute_effective_level(c, decay_rate))
    # Bottom 75% of ALL cards is the weak pool; randomly sample from it (not sequential)
    weak_end = max(1, int(len(scored) * 0.75))
    weak_pool = scored[:weak_end]
    strong_pool = scored[weak_end:]
    # Fill 75% of queue slots from weak pool, rest from strong pool — both randomly sampled
    n_weak = min(max(1, int(queue_size * 0.75)), len(weak_pool))
    n_strong = min(queue_size - n_weak, len(strong_pool))
    queue = random.sample(weak_pool, n_weak) + (
        random.sample(strong_pool, n_strong) if n_strong > 0 else []
    )
    random.shuffle(queue)
    return queue

def answers_match(user_answer: str, correct_answer: str) -> bool:
    def normalize(s: str) -> str:
        s = s.lower().strip()
        s = re.sub(r"[^\w\s]", "", s)
        return re.sub(r"\s+", " ", s).strip()

    first_line = correct_answer.splitlines()[0] if correct_answer.strip() else correct_answer
    user_norm = normalize(user_answer)
    if not user_norm:
        return False

    accepted: set[str] = set()
    for part in first_line.split("/"):
        part_norm = normalize(part)
        if part_norm:
            accepted.add(part_norm)          # full slash-separated phrase
            for word in part_norm.split():   # any individual word on the first line
                accepted.add(word)

    return user_norm in accepted

def apply_memory_delta(card: Card, result: Literal['seen', 'correct', 'incorrect'], already_seen: bool) -> float:
    level = card.memory_level
    if result == "seen":
        # Flip: scales from 20 at 0% to 5 at 100%
        delta = 20 - int(level * 0.15)
    elif result == "correct":
        # Correct quiz: scales from 60 at 0% to 20 at 100%
        delta = int(60 - level * 0.40)
    else:
        # Incorrect quiz: scales from -75 at 0% to -125 at 100%
        delta = -int(75 + level * 0.50)
    return max(0.0, min(100.0, level + delta))
