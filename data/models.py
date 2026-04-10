from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

@dataclass
class Card:
    front: str
    back: str
    is_quiz: bool = False
    memory_level: float = 50.0
    id: Optional[int] = None
    deck_id: Optional[int] = None
    last_reviewed: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)

@dataclass
class Deck:
    name: str
    id: Optional[int] = None
    created_at: datetime = field(default_factory=datetime.now)

@dataclass
class ReviewSession:
    id: Optional[int] = None
    started_at: datetime = field(default_factory=datetime.now)
    ended_at: Optional[datetime] = None
    cards_reviewed: int = 0

@dataclass
class SessionCard:
    session_id: int
    card_id: int
    result: str          # 'seen', 'correct', 'incorrect'
    memory_before: float
    memory_after: float
    id: Optional[int] = None
    reviewed_at: datetime = field(default_factory=datetime.now)
