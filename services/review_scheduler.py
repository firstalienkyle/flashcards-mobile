import random
import re
from datetime import datetime
from typing import Literal
from data.models import Card

def compute_effective_level(item, decay_rate: float) -> float:
    """
    Memory level after applying time-based decay.

    Decay slows for well-practiced items and for items that are closer to full
    mastery, which is suitable for both cards and photo memory entries.
    """
    if item.last_reviewed is None:
        return item.memory_level
    days_elapsed = (datetime.now() - item.last_reviewed).total_seconds() / 86400
    stability = 1.0 + item.review_count * 0.35 + (item.memory_level / 100.0) * 2.0
    effective_decay = decay_rate / stability
    return max(0.0, item.memory_level - effective_decay * days_elapsed)

def build_review_queue(items: list, decay_rate: float, queue_size: int = 25) -> list:
    """75% lowest-memory items + 25% random from the rest, shuffled."""
    if not items:
        return []

    sorted_items = sorted(items, key=lambda item: compute_effective_level(item, decay_rate))
    n_priority = max(1, int(min(queue_size, len(items)) * 0.75))
    priority = sorted_items[:n_priority]
    remaining = sorted_items[n_priority:]

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

def apply_memory_delta(card: Card, result: Literal['seen', 'correct', 'incorrect'], already_seen: bool) -> float:
    """
    result: 'seen' (regular flip), 'correct' (quiz), 'incorrect' (quiz)
    already_seen: True if this card was already reviewed earlier in this session.
    Returns new memory_level (clamped 0–100).

    Gains use diminishing returns — easier to improve a weak card than a strong
    one. Penalties scale up with memory level — forgetting something you know
    well costs more.
    """
    level = card.memory_level

    if result == "seen":
        # First flip this session: solid boost. Re-seen: smaller reinforcement.
        if not already_seen:
            delta = 8.0 * (1.0 - level / 100.0) + 4.0
        else:
            delta = max(1.0, 4.0 * (1.0 - level / 100.0))

    elif result == "correct":
        # Stronger gain for weaker memories; diminishing returns as level climbs.
        delta = max(3.0, 20.0 * (1.0 - level / 100.0))

    else:  # incorrect
        # Forgetting hurts more when the memory is stronger.
        delta = -(5.0 + level * 0.12)

    return max(0.0, min(100.0, level + delta))
