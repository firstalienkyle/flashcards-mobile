from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class PictureButton:
    label: str
    path: str          # original path — file is never copied
    position: int = 0
    memory_level: float = 0.0
    last_reviewed: Optional[datetime] = None
    review_count: int = 0
    id: Optional[int] = None
    created_at: datetime = field(default_factory=datetime.now)
