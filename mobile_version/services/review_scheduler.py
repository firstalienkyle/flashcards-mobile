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
    levels = {c.id: compute_effective_level(c, decay_rate) for c in cards}
    available = sorted(cards, key=lambda c: levels[c.id])
    queue: list[Card] = []

    while available and len(queue) < queue_size:
        min_lvl = levels[available[0].id]
        # "lowest ones" = all cards tied at (or within 0.5 of) the current minimum
        split = next((i for i, c in enumerate(available) if levels[c.id] > min_lvl + 0.5),
                     len(available))
        lowest = available[:split]
        others  = available[split:]

        pick = random.choice(lowest) if (not others or random.random() < 0.75) else random.choice(others)
        queue.append(pick)
        available.remove(pick)

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
