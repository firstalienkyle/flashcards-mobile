from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class PictureButton:
    label: str
    path: str          # absolute path to the image file
    position: int = 0
    id: Optional[int] = None
    created_at: datetime = field(default_factory=datetime.now)
