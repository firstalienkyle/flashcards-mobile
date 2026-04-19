# Flashcard App Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a dark-themed Python desktop flashcard app with spaced-repetition memory tracking, Claude API integration for card generation and answer explanations, camera/PDF import, and macOS push notifications.

**Architecture:** Service-oriented layered architecture — `data/` layer (SQLite models + CRUD) feeds into `services/` (ReviewScheduler, ClaudeService, ScanService, NotificationService), which are consumed by `ui/` screens (CustomTkinter). Built bottom-up: data → services → UI → main wiring.

**Tech Stack:** Python 3.11+, CustomTkinter, Anthropic SDK (`claude-sonnet-4-6`), OpenCV, pdfplumber, pystray, plyer, Pillow, SQLite (stdlib), pytest

---

## File Map

| File | Responsibility |
|---|---|
| `requirements.txt` | All pip dependencies |
| `config.py` | Constants: accent colour, fonts, DB path, model name |
| `data/models.py` | `Card`, `Deck`, `ReviewSession`, `SessionCard` dataclasses |
| `data/database.py` | SQLite init + all CRUD functions |
| `services/review_scheduler.py` | Memory decay, queue building (75/25), answer matching, session state |
| `services/claude_service.py` | `generate_cards_from_text`, `generate_cards_from_image`, `explain_answer` |
| `services/scan_service.py` | Webcam capture (OpenCV) + PDF extraction (pdfplumber) |
| `services/notification_service.py` | Background thread + plyer notifications + pystray tray icon |
| `ui/app.py` | Root CTk window, screen router (`show_home`, `show_review`, etc.) |
| `ui/home_screen.py` | Deck grid, daily goal bar, nav buttons |
| `ui/review_screen.py` | Card flip animation, quiz mode, back/forward nav, session logic |
| `ui/create_screen.py` | Manual card form + scan/PDF import flow |
| `ui/deck_screen.py` | Card list, edit modal, delete, rename deck |
| `ui/settings_screen.py` | Daily goal, notify time, API key, decay rate |
| `main.py` | Entry point — init DB, build services, launch App |
| `tests/test_models.py` | Dataclass construction tests |
| `tests/test_database.py` | CRUD tests against in-memory SQLite |
| `tests/test_review_scheduler.py` | Decay calc, queue split, answer matching |
| `tests/test_claude_service.py` | Claude calls with mocked Anthropic client |

---

## Task 1: Project Scaffolding

**Files:**
- Create: `requirements.txt`
- Create: `config.py`
- Create: `.gitignore`
- Create: `data/__init__.py`, `services/__init__.py`, `ui/__init__.py`, `tests/__init__.py`

- [ ] **Step 1: Create directory structure**

```bash
mkdir -p data services ui tests
touch data/__init__.py services/__init__.py ui/__init__.py tests/__init__.py
```

- [ ] **Step 2: Write requirements.txt**

```
customtkinter==5.2.2
anthropic>=0.25.0
opencv-python>=4.9.0
pdfplumber>=0.11.0
pystray>=0.19.5
plyer>=2.1.0
Pillow>=10.3.0
pytest>=8.0.0
pytest-mock>=3.12.0
```

- [ ] **Step 3: Write config.py**

```python
from pathlib import Path

# UI
ACCENT       = "#7c83fd"
BG_DARK      = "#1a1a2e"
BG_CARD      = "#16213e"
BG_INPUT     = "#0f3460"
TEXT_PRIMARY = "#e0e0e0"
TEXT_MUTED   = "#888888"
COLOR_GREEN  = "#3fb950"
COLOR_RED    = "#f85149"
FONT_FAMILY  = "Inter"
CORNER_R     = 12
PADDING      = 16

# Storage
DB_PATH = Path.home() / ".flashcards" / "flashcards.db"

# Claude
CLAUDE_MODEL = "claude-sonnet-4-6"
```

- [ ] **Step 4: Write .gitignore**

```
__pycache__/
*.pyc
.env
*.db
.superpowers/
```

- [ ] **Step 5: Install dependencies**

```bash
pip install -r requirements.txt
```

Expected: All packages install without errors.

- [ ] **Step 6: Commit**

```bash
git add requirements.txt config.py .gitignore data/__init__.py services/__init__.py ui/__init__.py tests/__init__.py
git commit -m "feat: project scaffolding"
```

---

## Task 2: Data Models

**Files:**
- Create: `data/models.py`
- Create: `tests/test_models.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_models.py
from datetime import datetime
from data.models import Card, Deck, ReviewSession, SessionCard

def test_card_defaults():
    c = Card(front="Q", back="A")
    assert c.memory_level == 50.0
    assert c.is_quiz is False
    assert c.id is None
    assert c.deck_id is None
    assert c.last_reviewed is None

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
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_models.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'data.models'`

- [ ] **Step 3: Write data/models.py**

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_models.py -v
```

Expected: 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add data/models.py tests/test_models.py
git commit -m "feat: data models"
```

---

## Task 3: Database Layer

**Files:**
- Create: `data/database.py`
- Create: `tests/test_database.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_database.py
import sqlite3
import pytest
from datetime import datetime
from data.models import Card, Deck
import data.database as db

@pytest.fixture(autouse=True)
def use_memory_db(monkeypatch, tmp_path):
    """Redirect all DB calls to a fresh in-memory DB for each test."""
    test_db = tmp_path / "test.db"
    monkeypatch.setattr(db, "_DB_PATH", test_db)
    db.init_db()

def test_create_and_get_deck():
    d = db.create_deck("Biology")
    assert d.id is not None
    decks = db.get_all_decks()
    assert len(decks) == 1
    assert decks[0].name == "Biology"

def test_rename_deck():
    d = db.create_deck("Bio")
    db.rename_deck(d.id, "Biology")
    assert db.get_all_decks()[0].name == "Biology"

def test_delete_deck_cascades():
    d = db.create_deck("Temp")
    c = Card(front="Q", back="A", deck_id=d.id)
    db.create_card(c)
    db.delete_deck(d.id)
    assert db.get_all_decks() == []
    assert db.get_all_cards() == []

def test_create_and_get_card():
    d = db.create_deck("Bio")
    c = Card(front="Q", back="A", deck_id=d.id)
    saved = db.create_card(c)
    assert saved.id is not None
    cards = db.get_cards_for_deck(d.id)
    assert len(cards) == 1
    assert cards[0].front == "Q"

def test_update_card():
    d = db.create_deck("Bio")
    c = db.create_card(Card(front="Q", back="A", deck_id=d.id))
    c.back = "Updated"
    db.update_card(c)
    assert db.get_cards_for_deck(d.id)[0].back == "Updated"

def test_update_card_memory():
    d = db.create_deck("Bio")
    c = db.create_card(Card(front="Q", back="A", deck_id=d.id))
    now = datetime.now()
    db.update_card_memory(c.id, 70.0, now)
    updated = db.get_cards_for_deck(d.id)[0]
    assert updated.memory_level == 70.0
    assert updated.last_reviewed is not None

def test_settings_defaults():
    assert db.get_setting("daily_goal") == "20"
    assert db.get_setting("decay_rate") == "5.0"

def test_set_and_get_setting():
    db.set_setting("daily_goal", "30")
    assert db.get_setting("daily_goal") == "30"

def test_get_today_reviewed_count():
    s = db.create_session()
    db.record_session_card_result(s.id, card_id=1, result="seen",
                                  memory_before=50, memory_after=60)
    db.record_session_card_result(s.id, card_id=2, result="correct",
                                  memory_before=40, memory_after=60)
    assert db.get_today_reviewed_count() == 2
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_database.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'data.database'`

- [ ] **Step 3: Write data/database.py**

```python
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional
from data.models import Card, Deck, ReviewSession, SessionCard
import config

_DB_PATH: Path = config.DB_PATH

def _conn() -> sqlite3.Connection:
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db() -> None:
    with _conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS decks (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT    NOT NULL,
                created_at  TEXT    NOT NULL
            );
            CREATE TABLE IF NOT EXISTS cards (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                deck_id       INTEGER NOT NULL REFERENCES decks(id) ON DELETE CASCADE,
                front         TEXT    NOT NULL,
                back          TEXT    NOT NULL,
                is_quiz       INTEGER NOT NULL DEFAULT 0,
                memory_level  REAL    NOT NULL DEFAULT 50.0,
                last_reviewed TEXT,
                created_at    TEXT    NOT NULL
            );
            CREATE TABLE IF NOT EXISTS review_sessions (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at     TEXT    NOT NULL,
                ended_at       TEXT,
                cards_reviewed INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS session_cards (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id    INTEGER NOT NULL REFERENCES review_sessions(id),
                card_id       INTEGER NOT NULL,
                reviewed_at   TEXT    NOT NULL,
                result        TEXT    NOT NULL,
                memory_before REAL    NOT NULL,
                memory_after  REAL    NOT NULL
            );
            CREATE TABLE IF NOT EXISTS settings (
                key   TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            INSERT OR IGNORE INTO settings VALUES ('daily_goal',    '20');
            INSERT OR IGNORE INTO settings VALUES ('notify_time',   '18:00');
            INSERT OR IGNORE INTO settings VALUES ('claude_api_key','');
            INSERT OR IGNORE INTO settings VALUES ('decay_rate',    '5.0');
        """)

# ── Decks ─────────────────────────────────────────────────────────────────────

def create_deck(name: str) -> Deck:
    with _conn() as conn:
        now = datetime.now().isoformat()
        cur = conn.execute("INSERT INTO decks (name, created_at) VALUES (?, ?)", (name, now))
        return Deck(name=name, id=cur.lastrowid, created_at=datetime.fromisoformat(now))

def get_all_decks() -> list[Deck]:
    with _conn() as conn:
        rows = conn.execute("SELECT * FROM decks ORDER BY created_at").fetchall()
        return [Deck(name=r["name"], id=r["id"],
                     created_at=datetime.fromisoformat(r["created_at"])) for r in rows]

def rename_deck(deck_id: int, name: str) -> None:
    with _conn() as conn:
        conn.execute("UPDATE decks SET name = ? WHERE id = ?", (name, deck_id))

def delete_deck(deck_id: int) -> None:
    with _conn() as conn:
        conn.execute("DELETE FROM decks WHERE id = ?", (deck_id,))

def get_deck_stats(deck_id: int) -> dict:
    """Returns {'card_count': int, 'avg_memory': float}."""
    with _conn() as conn:
        row = conn.execute(
            "SELECT COUNT(*) as cnt, AVG(memory_level) as avg FROM cards WHERE deck_id = ?",
            (deck_id,)
        ).fetchone()
        return {"card_count": row["cnt"] or 0, "avg_memory": round(row["avg"] or 0.0, 1)}

# ── Cards ──────────────────────────────────────────────────────────────────────

def _row_to_card(r: sqlite3.Row) -> Card:
    return Card(
        id=r["id"],
        deck_id=r["deck_id"],
        front=r["front"],
        back=r["back"],
        is_quiz=bool(r["is_quiz"]),
        memory_level=r["memory_level"],
        last_reviewed=datetime.fromisoformat(r["last_reviewed"]) if r["last_reviewed"] else None,
        created_at=datetime.fromisoformat(r["created_at"]),
    )

def create_card(card: Card) -> Card:
    with _conn() as conn:
        now = datetime.now().isoformat()
        cur = conn.execute(
            "INSERT INTO cards (deck_id, front, back, is_quiz, memory_level, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (card.deck_id, card.front, card.back, int(card.is_quiz), card.memory_level, now)
        )
        card.id = cur.lastrowid
        card.created_at = datetime.fromisoformat(now)
        return card

def get_cards_for_deck(deck_id: int) -> list[Card]:
    with _conn() as conn:
        rows = conn.execute("SELECT * FROM cards WHERE deck_id = ? ORDER BY created_at",
                            (deck_id,)).fetchall()
        return [_row_to_card(r) for r in rows]

def get_all_cards() -> list[Card]:
    with _conn() as conn:
        rows = conn.execute("SELECT * FROM cards").fetchall()
        return [_row_to_card(r) for r in rows]

def update_card(card: Card) -> None:
    with _conn() as conn:
        conn.execute(
            "UPDATE cards SET front=?, back=?, is_quiz=? WHERE id=?",
            (card.front, card.back, int(card.is_quiz), card.id)
        )

def delete_card(card_id: int) -> None:
    with _conn() as conn:
        conn.execute("DELETE FROM cards WHERE id = ?", (card_id,))

def update_card_memory(card_id: int, memory_level: float, last_reviewed: datetime) -> None:
    with _conn() as conn:
        conn.execute(
            "UPDATE cards SET memory_level=?, last_reviewed=? WHERE id=?",
            (memory_level, last_reviewed.isoformat(), card_id)
        )

# ── Sessions ───────────────────────────────────────────────────────────────────

def create_session() -> ReviewSession:
    with _conn() as conn:
        now = datetime.now().isoformat()
        cur = conn.execute("INSERT INTO review_sessions (started_at) VALUES (?)", (now,))
        return ReviewSession(id=cur.lastrowid, started_at=datetime.fromisoformat(now))

def end_session(session_id: int, cards_reviewed: int) -> None:
    with _conn() as conn:
        conn.execute(
            "UPDATE review_sessions SET ended_at=?, cards_reviewed=? WHERE id=?",
            (datetime.now().isoformat(), cards_reviewed, session_id)
        )

def record_session_card_result(session_id: int, card_id: int, result: str,
                                memory_before: float, memory_after: float) -> None:
    with _conn() as conn:
        conn.execute(
            "INSERT INTO session_cards (session_id, card_id, reviewed_at, result, "
            "memory_before, memory_after) VALUES (?, ?, ?, ?, ?, ?)",
            (session_id, card_id, datetime.now().isoformat(), result, memory_before, memory_after)
        )

def get_today_reviewed_count() -> int:
    today = datetime.now().date().isoformat()
    with _conn() as conn:
        row = conn.execute(
            "SELECT COUNT(DISTINCT card_id) as cnt FROM session_cards "
            "WHERE DATE(reviewed_at) = ?", (today,)
        ).fetchone()
        return row["cnt"] or 0

# ── Settings ───────────────────────────────────────────────────────────────────

def get_setting(key: str) -> str:
    with _conn() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return row["value"] if row else ""

def set_setting(key: str, value: str) -> None:
    with _conn() as conn:
        conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))

def get_all_settings() -> dict:
    with _conn() as conn:
        rows = conn.execute("SELECT key, value FROM settings").fetchall()
        return {r["key"]: r["value"] for r in rows}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_database.py -v
```

Expected: 9 tests PASS

- [ ] **Step 5: Commit**

```bash
git add data/database.py tests/test_database.py
git commit -m "feat: database layer with full CRUD"
```

---

## Task 4: Review Scheduler

**Files:**
- Create: `services/review_scheduler.py`
- Create: `tests/test_review_scheduler.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_review_scheduler.py
from datetime import datetime, timedelta
from data.models import Card
from services.review_scheduler import (
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
    assert new_level == 60.0

def test_apply_memory_delta_flip_repeat():
    c = _card(50.0)
    new_level = apply_memory_delta(c, result="seen", already_seen=True)
    assert new_level == 50.0

def test_apply_memory_delta_quiz_correct():
    c = _card(50.0, is_quiz=True)
    assert apply_memory_delta(c, result="correct", already_seen=False) == 70.0

def test_apply_memory_delta_quiz_wrong():
    c = _card(50.0, is_quiz=True)
    assert apply_memory_delta(c, result="incorrect", already_seen=False) == 40.0

def test_apply_memory_delta_clamps_at_100():
    c = _card(95.0, is_quiz=True)
    assert apply_memory_delta(c, result="correct", already_seen=False) == 100.0

def test_apply_memory_delta_clamps_at_zero():
    c = _card(5.0, is_quiz=True)
    assert apply_memory_delta(c, result="incorrect", already_seen=False) == 0.0
```

- [ ] **Step 2: Add missing import to test file**

Add at the top of `tests/test_review_scheduler.py`:

```python
import pytest
```

- [ ] **Step 3: Run test to verify it fails**

```bash
pytest tests/test_review_scheduler.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'services.review_scheduler'`

- [ ] **Step 4: Write services/review_scheduler.py**

```python
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
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/test_review_scheduler.py -v
```

Expected: 14 tests PASS

- [ ] **Step 6: Commit**

```bash
git add services/review_scheduler.py tests/test_review_scheduler.py
git commit -m "feat: review scheduler — decay, queue building, memory delta"
```

---

## Task 5: Claude Service

**Files:**
- Create: `services/claude_service.py`
- Create: `tests/test_claude_service.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_claude_service.py
import json
import pytest
from unittest.mock import MagicMock, patch
from services.claude_service import ClaudeService

@pytest.fixture
def svc():
    return ClaudeService(api_key="test-key")

def _mock_response(text: str):
    msg = MagicMock()
    msg.content = [MagicMock(text=text)]
    return msg

def test_generate_cards_from_text_parses_json(svc):
    payload = json.dumps([
        {"front": "What is ATP?", "back": "Energy currency of the cell", "is_quiz": True}
    ])
    with patch.object(svc.client.messages, "create", return_value=_mock_response(payload)):
        cards = svc.generate_cards_from_text("Some biology notes")
    assert len(cards) == 1
    assert cards[0]["front"] == "What is ATP?"
    assert cards[0]["is_quiz"] is True

def test_generate_cards_from_image_parses_json(svc):
    payload = json.dumps([{"front": "Capital of France?", "back": "Paris", "is_quiz": False}])
    with patch.object(svc.client.messages, "create", return_value=_mock_response(payload)):
        cards = svc.generate_cards_from_image(b"fake_image_bytes")
    assert cards[0]["back"] == "Paris"

def test_explain_answer_returns_string(svc):
    with patch.object(svc.client.messages, "create",
                      return_value=_mock_response("Because it produces ATP via oxidative phosphorylation.")):
        explanation = svc.explain_answer(
            front="What is the powerhouse of the cell?",
            back="Mitochondria"
        )
    assert "ATP" in explanation

def test_generate_cards_raises_on_invalid_json(svc):
    with patch.object(svc.client.messages, "create", return_value=_mock_response("not json")):
        with pytest.raises(ValueError, match="Claude returned invalid JSON"):
            svc.generate_cards_from_text("text")
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_claude_service.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'services.claude_service'`

- [ ] **Step 3: Write services/claude_service.py**

```python
import base64
import json
import anthropic
from config import CLAUDE_MODEL

class ClaudeService:
    def __init__(self, api_key: str):
        self.client = anthropic.Anthropic(api_key=api_key)

    def _parse_cards(self, raw: str) -> list[dict]:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            raise ValueError(f"Claude returned invalid JSON: {e}\nRaw: {raw[:200]}")
        return data

    def generate_cards_from_text(self, text: str) -> list[dict]:
        """Extract flashcard pairs from plain text. Returns list of {front, back, is_quiz}."""
        response = self.client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=2048,
            messages=[{
                "role": "user",
                "content": (
                    "Extract flashcards from the following text.\n"
                    "Return a JSON array of objects with keys:\n"
                    "  - \"front\": the question or term (string)\n"
                    "  - \"back\": the answer or definition (string)\n"
                    "  - \"is_quiz\": true only for strict definition cards where the user must recall the exact term (boolean)\n"
                    "Return ONLY valid JSON — no markdown, no commentary.\n\n"
                    f"Text:\n{text}"
                )
            }]
        )
        return self._parse_cards(response.content[0].text)

    def generate_cards_from_image(self, image_bytes: bytes) -> list[dict]:
        """Extract flashcard pairs from an image via Claude Vision. Returns list of {front, back, is_quiz}."""
        image_b64 = base64.standard_b64encode(image_bytes).decode("utf-8")
        response = self.client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=2048,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": image_b64,
                        },
                    },
                    {
                        "type": "text",
                        "text": (
                            "Extract flashcards from this image.\n"
                            "Return a JSON array of objects with keys:\n"
                            "  - \"front\": the question or term (string)\n"
                            "  - \"back\": the answer or definition (string)\n"
                            "  - \"is_quiz\": true only for strict definition cards (boolean)\n"
                            "Return ONLY valid JSON — no markdown, no commentary."
                        ),
                    },
                ],
            }]
        )
        return self._parse_cards(response.content[0].text)

    def explain_answer(self, front: str, back: str) -> str:
        """Return a short explanation of why `back` is the correct answer to `front`."""
        response = self.client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=256,
            messages=[{
                "role": "user",
                "content": (
                    f"Flashcard:\nQuestion: {front}\nCorrect Answer: {back}\n\n"
                    "In 2–3 plain sentences, explain why this is the correct answer. "
                    "Be concise and clear."
                )
            }]
        )
        return response.content[0].text.strip()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_claude_service.py -v
```

Expected: 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add services/claude_service.py tests/test_claude_service.py
git commit -m "feat: Claude service — card generation and answer explanation"
```

---

## Task 6: Scan Service

**Files:**
- Create: `services/scan_service.py`

(No unit tests — both methods depend on hardware (webcam) and file I/O. Manual testing in Task 14.)

- [ ] **Step 1: Write services/scan_service.py**

```python
from pathlib import Path
import cv2
import pdfplumber

class ScanService:
    def capture_from_camera(self) -> bytes:
        """
        Opens the default webcam, shows a preview window, captures a frame
        on SPACE key press, closes the window, and returns the JPEG bytes.
        Raises RuntimeError if no camera is found.
        """
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            raise RuntimeError("No camera found. Make sure a webcam is connected.")
        
        print("Camera preview open. Press SPACE to capture, Q to cancel.")
        captured = None
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            cv2.imshow("Capture — SPACE to snap, Q to cancel", frame)
            key = cv2.waitKey(1) & 0xFF
            if key == ord(' '):
                captured = frame
                break
            elif key == ord('q'):
                break
        
        cap.release()
        cv2.destroyAllWindows()
        
        if captured is None:
            raise RuntimeError("Capture cancelled.")
        
        success, buffer = cv2.imencode(".jpg", captured)
        if not success:
            raise RuntimeError("Failed to encode captured frame as JPEG.")
        return buffer.tobytes()

    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """
        Extracts all text from a PDF file, concatenating pages with newlines.
        Raises FileNotFoundError if the path does not exist.
        Raises ValueError if no text could be extracted.
        """
        path = Path(pdf_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")
        
        pages_text = []
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    pages_text.append(text)
        
        if not pages_text:
            raise ValueError("No extractable text found in PDF. It may be image-only.")
        
        return "\n\n".join(pages_text)
```

- [ ] **Step 2: Commit**

```bash
git add services/scan_service.py
git commit -m "feat: scan service — webcam capture and PDF text extraction"
```

---

## Task 7: Notification Service

**Files:**
- Create: `services/notification_service.py`

- [ ] **Step 1: Write services/notification_service.py**

```python
import threading
import time
from datetime import datetime
from typing import Callable
from plyer import notification
import pystray
from PIL import Image, ImageDraw

class NotificationService:
    """
    Background service that:
    1. Checks every 60s whether to fire a daily review reminder.
    2. Runs a system tray icon so the app can persist after the window is hidden.
    """

    def __init__(
        self,
        get_setting: Callable[[str], str],
        get_today_count: Callable[[], int],
    ):
        self._get_setting = get_setting
        self._get_today_count = get_today_count
        self._tray: pystray.Icon | None = None
        self._notified_today: str = ""   # date string — prevents duplicate notifications

    def start(self) -> None:
        """Start background threads. Call once at app launch."""
        t = threading.Thread(target=self._check_loop, daemon=True)
        t.start()
        self._start_tray()

    def stop(self) -> None:
        if self._tray:
            self._tray.stop()

    # ── Private ───────────────────────────────────────────────────────────────

    def _check_loop(self) -> None:
        while True:
            time.sleep(60)
            try:
                self._maybe_notify()
            except Exception:
                pass  # Never crash the background thread

    def _maybe_notify(self) -> None:
        notify_time = self._get_setting("notify_time")
        daily_goal  = int(self._get_setting("daily_goal"))
        today       = datetime.now().date().isoformat()
        now_hhmm    = datetime.now().strftime("%H:%M")

        if now_hhmm == notify_time and today != self._notified_today:
            count = self._get_today_count()
            if count < daily_goal:
                notification.notify(
                    title="Flashcard Review",
                    message=f"You've reviewed {count}/{daily_goal} cards today. Time to study!",
                    app_name="Flashcards",
                    timeout=10,
                )
                self._notified_today = today

    def _start_tray(self) -> None:
        img = Image.new("RGB", (64, 64), color="#7c83fd")
        draw = ImageDraw.Draw(img)
        draw.rectangle([16, 20, 48, 44], fill="white")

        def on_quit(icon, _item):
            icon.stop()

        menu = pystray.Menu(pystray.MenuItem("Quit", on_quit))
        self._tray = pystray.Icon("flashcards", img, "Flashcards", menu)
        t = threading.Thread(target=self._tray.run, daemon=True)
        t.start()
```

- [ ] **Step 2: Commit**

```bash
git add services/notification_service.py
git commit -m "feat: notification service — tray icon and daily reminder"
```

---

## Task 8: UI App Shell

**Files:**
- Create: `ui/app.py`

- [ ] **Step 1: Write ui/app.py**

```python
import customtkinter as ctk
from config import BG_DARK, ACCENT

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class App(ctk.CTk):
    """
    Root window and screen router. All service references are stored here
    so every screen can access them via self.master (or self.app).
    """

    def __init__(self, db, review_scheduler_mod, claude_service, scan_service, notification_service):
        super().__init__()
        self.title("Flashcards")
        self.geometry("960x660")
        self.resizable(False, False)
        self.configure(fg_color=BG_DARK)

        # Service references — screens read these via self.app
        self.db = db
        self.rs = review_scheduler_mod   # the review_scheduler module (functions, not a class)
        self.claude = claude_service
        self.scan = scan_service
        self.notif = notification_service

        self._screen = None
        self.show_home()

    # ── Screen routing ─────────────────────────────────────────────────────────

    def _switch(self, screen: ctk.CTkFrame) -> None:
        if self._screen:
            self._screen.destroy()
        self._screen = screen
        screen.pack(fill="both", expand=True)

    def show_home(self) -> None:
        from ui.home_screen import HomeScreen
        self._switch(HomeScreen(self))

    def show_review(self) -> None:
        from ui.review_screen import ReviewScreen
        self._switch(ReviewScreen(self))

    def show_create(self, deck_id: int | None = None) -> None:
        from ui.create_screen import CreateScreen
        self._switch(CreateScreen(self, deck_id=deck_id))

    def show_deck(self, deck_id: int) -> None:
        from ui.deck_screen import DeckScreen
        self._switch(DeckScreen(self, deck_id=deck_id))

    def show_settings(self) -> None:
        from ui.settings_screen import SettingsScreen
        self._switch(SettingsScreen(self))
```

- [ ] **Step 2: Commit**

```bash
git add ui/app.py
git commit -m "feat: UI app shell and screen router"
```

---

## Task 9: HomeScreen

**Files:**
- Create: `ui/home_screen.py`

- [ ] **Step 1: Write ui/home_screen.py**

```python
import customtkinter as ctk
from config import (ACCENT, BG_CARD, BG_DARK, TEXT_PRIMARY, TEXT_MUTED,
                    CORNER_R, PADDING, FONT_FAMILY, COLOR_GREEN)

class HomeScreen(ctk.CTkFrame):
    def __init__(self, app):
        super().__init__(app, fg_color=BG_DARK, corner_radius=0)
        self.app = app
        self._build()
        self._load()

    def _build(self):
        # ── Top bar ──────────────────────────────────────────────────────────
        top = ctk.CTkFrame(self, fg_color=BG_DARK, corner_radius=0)
        top.pack(fill="x", padx=PADDING, pady=(PADDING, 0))

        ctk.CTkLabel(top, text="Flashcards", font=ctk.CTkFont(FONT_FAMILY, 24, "bold"),
                     text_color=TEXT_PRIMARY).pack(side="left")

        ctk.CTkButton(top, text="⚙ Settings", width=100, fg_color=BG_CARD,
                      hover_color=ACCENT, corner_radius=CORNER_R,
                      command=self.app.show_settings).pack(side="right")

        # ── Daily goal bar ────────────────────────────────────────────────────
        goal_frame = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=CORNER_R)
        goal_frame.pack(fill="x", padx=PADDING, pady=(12, 0))

        inner = ctk.CTkFrame(goal_frame, fg_color="transparent")
        inner.pack(fill="x", padx=PADDING, pady=10)

        self._goal_label = ctk.CTkLabel(inner, text="Loading...",
                                        font=ctk.CTkFont(FONT_FAMILY, 13),
                                        text_color=TEXT_MUTED)
        self._goal_label.pack(side="left")

        self._progress = ctk.CTkProgressBar(inner, width=220, height=10,
                                            progress_color=ACCENT, corner_radius=5)
        self._progress.set(0)
        self._progress.pack(side="right")

        # ── Action buttons ────────────────────────────────────────────────────
        btn_row = ctk.CTkFrame(self, fg_color=BG_DARK)
        btn_row.pack(fill="x", padx=PADDING, pady=(12, 0))

        for text, cmd in [
            ("▶  Start Review", self.app.show_review),
            ("+  New Card",     self.app.show_create),
            ("↑  Import",       self._open_import),
        ]:
            ctk.CTkButton(btn_row, text=text, height=40, fg_color=ACCENT,
                          hover_color="#5a61e8", corner_radius=CORNER_R,
                          font=ctk.CTkFont(FONT_FAMILY, 13, "bold"),
                          command=cmd).pack(side="left", padx=(0, 8))

        # ── Deck grid (scrollable) ────────────────────────────────────────────
        self._scroll = ctk.CTkScrollableFrame(self, fg_color=BG_DARK, corner_radius=0)
        self._scroll.pack(fill="both", expand=True, padx=PADDING, pady=PADDING)
        self._scroll.columnconfigure((0, 1, 2), weight=1)

    def _load(self):
        # Goal progress
        goal   = int(self.app.db.get_setting("daily_goal"))
        count  = self.app.db.get_today_reviewed_count()
        ratio  = min(1.0, count / max(goal, 1))
        self._goal_label.configure(text=f"{count} / {goal} cards reviewed today")
        self._progress.set(ratio)

        # Deck tiles
        for widget in self._scroll.winfo_children():
            widget.destroy()

        decks = self.app.db.get_all_decks()
        if not decks:
            ctk.CTkLabel(self._scroll, text="No decks yet — create your first card!",
                         text_color=TEXT_MUTED,
                         font=ctk.CTkFont(FONT_FAMILY, 14)).grid(row=0, column=0,
                                                                   columnspan=3, pady=40)
            return

        for i, deck in enumerate(decks):
            stats = self.app.db.get_deck_stats(deck.id)
            self._deck_tile(deck, stats, row=i // 3, col=i % 3)

    def _deck_tile(self, deck, stats, row, col):
        tile = ctk.CTkFrame(self._scroll, fg_color=BG_CARD, corner_radius=CORNER_R,
                            cursor="hand2")
        tile.grid(row=row, column=col, padx=6, pady=6, sticky="nsew")

        ctk.CTkLabel(tile, text=deck.name, font=ctk.CTkFont(FONT_FAMILY, 15, "bold"),
                     text_color=TEXT_PRIMARY).pack(anchor="w", padx=12, pady=(12, 4))

        ctk.CTkLabel(tile, text=f"{stats['card_count']} cards",
                     font=ctk.CTkFont(FONT_FAMILY, 12), text_color=TEXT_MUTED).pack(anchor="w", padx=12)

        mem_color = COLOR_GREEN if stats["avg_memory"] >= 60 else ACCENT
        ctk.CTkLabel(tile, text=f"Memory: {stats['avg_memory']:.0f}%",
                     font=ctk.CTkFont(FONT_FAMILY, 12),
                     text_color=mem_color).pack(anchor="w", padx=12, pady=(0, 12))

        tile.bind("<Button-1>", lambda e, did=deck.id: self.app.show_deck(did))
        for child in tile.winfo_children():
            child.bind("<Button-1>", lambda e, did=deck.id: self.app.show_deck(did))

    def _open_import(self):
        from ui.create_screen import CreateScreen
        self.app.show_create()
```

- [ ] **Step 2: Commit**

```bash
git add ui/home_screen.py
git commit -m "feat: HomeScreen with deck grid and daily goal progress"
```

---

## Task 10: ReviewScreen

**Files:**
- Create: `ui/review_screen.py`

- [ ] **Step 1: Write ui/review_screen.py**

```python
import customtkinter as ctk
from datetime import datetime
from config import (ACCENT, BG_CARD, BG_DARK, BG_INPUT, TEXT_PRIMARY, TEXT_MUTED,
                    CORNER_R, PADDING, FONT_FAMILY, COLOR_GREEN, COLOR_RED)
import data.database as db
from services.review_scheduler import build_review_queue, answers_match, apply_memory_delta

class ReviewScreen(ctk.CTkFrame):
    def __init__(self, app):
        super().__init__(app, fg_color=BG_DARK, corner_radius=0)
        self.app  = app
        self._queue: list    = []
        self._index: int     = 0
        self._seen: set      = set()    # card IDs seen this session
        self._session_id: int | None = None
        self._showing_front  = True
        self._animating      = False
        self._card_orig_w: int | None = None
        self._build()
        self._start_session()

    # ── Build UI ──────────────────────────────────────────────────────────────

    def _build(self):
        # Top bar
        top = ctk.CTkFrame(self, fg_color=BG_DARK)
        top.pack(fill="x", padx=PADDING, pady=(PADDING, 0))

        ctk.CTkButton(top, text="← Home", width=80, fg_color=BG_CARD,
                      hover_color=ACCENT, corner_radius=CORNER_R,
                      command=self._end_session).pack(side="left")

        self._progress_label = ctk.CTkLabel(top, text="",
                                            font=ctk.CTkFont(FONT_FAMILY, 13),
                                            text_color=TEXT_MUTED)
        self._progress_label.pack(side="right")

        # Memory bar
        mem_row = ctk.CTkFrame(self, fg_color=BG_DARK)
        mem_row.pack(fill="x", padx=PADDING, pady=(8, 0))
        self._mem_label = ctk.CTkLabel(mem_row, text="Memory: —",
                                       font=ctk.CTkFont(FONT_FAMILY, 12), text_color=TEXT_MUTED)
        self._mem_label.pack(side="left")
        self._mem_bar = ctk.CTkProgressBar(mem_row, width=180, height=8,
                                           progress_color=ACCENT, corner_radius=4)
        self._mem_bar.set(0.5)
        self._mem_bar.pack(side="right")

        # Card area
        card_container = ctk.CTkFrame(self, fg_color=BG_DARK)
        card_container.pack(fill="both", expand=True, padx=PADDING, pady=PADDING)

        self._card_frame = ctk.CTkFrame(card_container, fg_color=BG_CARD,
                                        corner_radius=20, width=600, height=280)
        self._card_frame.pack(expand=True)
        self._card_frame.pack_propagate(False)

        self._side_label = ctk.CTkLabel(self._card_frame, text="FRONT",
                                        font=ctk.CTkFont(FONT_FAMILY, 10),
                                        text_color=TEXT_MUTED)
        self._side_label.pack(pady=(16, 0))

        self._card_text = ctk.CTkLabel(self._card_frame, text="",
                                       font=ctk.CTkFont(FONT_FAMILY, 20),
                                       wraplength=520, text_color=TEXT_PRIMARY)
        self._card_text.pack(expand=True, padx=20)

        # Quiz input (hidden until needed)
        self._quiz_frame = ctk.CTkFrame(self._card_frame, fg_color="transparent")
        self._quiz_entry = ctk.CTkEntry(self._quiz_frame, width=440, height=36,
                                        fg_color=BG_INPUT, corner_radius=8,
                                        placeholder_text="Type your answer…")
        self._quiz_entry.pack(side="left", padx=(0, 8))
        ctk.CTkButton(self._quiz_frame, text="Submit", width=80, fg_color=ACCENT,
                      corner_radius=8, command=self._submit_quiz).pack(side="left")

        # Explanation label (quiz wrong feedback)
        self._explanation = ctk.CTkLabel(self._card_frame, text="",
                                         font=ctk.CTkFont(FONT_FAMILY, 12),
                                         text_color=TEXT_MUTED, wraplength=520)
        self._explanation.pack(pady=(0, 8))

        # Bottom navigation
        nav = ctk.CTkFrame(self, fg_color=BG_DARK)
        nav.pack(fill="x", padx=PADDING, pady=(0, PADDING))

        self._prev_btn = ctk.CTkButton(nav, text="← Previous", width=120,
                                       fg_color=BG_CARD, hover_color=ACCENT,
                                       corner_radius=CORNER_R, command=self._go_prev)
        self._prev_btn.pack(side="left")

        self._action_btn = ctk.CTkButton(nav, text="Flip", width=160,
                                         fg_color=ACCENT, hover_color="#5a61e8",
                                         corner_radius=CORNER_R, command=self._flip)
        self._action_btn.pack(side="left", padx=8)

        self._next_btn = ctk.CTkButton(nav, text="Next →", width=120,
                                       fg_color=BG_CARD, hover_color=ACCENT,
                                       corner_radius=CORNER_R, command=self._go_next)
        self._next_btn.pack(side="left")

    # ── Session logic ─────────────────────────────────────────────────────────

    def _start_session(self):
        decay = float(db.get_setting("decay_rate"))
        cards = db.get_all_cards()
        self._queue = build_review_queue(cards, decay_rate=decay)

        if not self._queue:
            self._card_text.configure(text="No cards yet!\nCreate some cards first.")
            self._action_btn.configure(state="disabled")
            return

        session = db.create_session()
        self._session_id = session.id
        self._show_card()

    def _show_card(self):
        self._showing_front = True
        self._explanation.configure(text="")
        self._quiz_frame.pack_forget()
        card = self._queue[self._index]

        self._card_text.configure(text=card.front)
        self._side_label.configure(text="FRONT")
        self._mem_label.configure(text=f"Memory: {card.memory_level:.0f}%")
        self._mem_bar.set(card.memory_level / 100)
        self._progress_label.configure(
            text=f"{self._index + 1} / {len(self._queue)}"
        )
        self._prev_btn.configure(state="normal" if self._index > 0 else "disabled")

        if card.is_quiz:
            self._action_btn.configure(text="Submit", state="disabled")
            self._quiz_entry.delete(0, "end")
            self._quiz_frame.pack(pady=(0, 12))
            self._quiz_entry.bind("<Return>", lambda e: self._submit_quiz())
        else:
            self._action_btn.configure(text="Flip", state="normal",
                                       command=self._flip)

    def _flip(self):
        """Animate card flip and reveal the back."""
        if self._animating:
            return
        card = self._queue[self._index]

        if self._showing_front:
            self._animate_flip(lambda: self._reveal_back(card))
        else:
            # Already flipped — advance
            self._record_and_advance(card, "seen")

    def _reveal_back(self, card):
        self._showing_front = False
        self._card_text.configure(text=card.back)
        self._side_label.configure(text="BACK")
        self._action_btn.configure(text="Next →", command=lambda: self._record_and_advance(card, "seen"))

    def _submit_quiz(self):
        card = self._queue[self._index]
        user_ans = self._quiz_entry.get().strip()
        if not user_ans:
            return

        self._quiz_frame.pack_forget()

        if answers_match(user_ans, card.back):
            self._card_text.configure(text=f"✓ Correct!\n\nAnswer: {card.back}",
                                      text_color=COLOR_GREEN)
            self._record_and_advance(card, "correct", delay_ms=1500)
        else:
            self._card_text.configure(text=f"✗ Incorrect\n\nCorrect answer: {card.back}",
                                      text_color=COLOR_RED)
            self._explanation.configure(text="Fetching explanation…")
            self.after(100, lambda: self._fetch_explanation(card, user_ans))

    def _fetch_explanation(self, card, _user_ans):
        try:
            explanation = self.app.claude.explain_answer(card.front, card.back)
        except Exception as e:
            explanation = f"(Could not fetch explanation: {e})"
        self._explanation.configure(text=explanation, text_color=TEXT_MUTED)
        self._record_and_advance(card, "incorrect", delay_ms=4000)

    def _record_and_advance(self, card, result: str, delay_ms: int = 0):
        already_seen = card.id in self._seen
        new_level    = apply_memory_delta(card, result=result, already_seen=already_seen)
        self._seen.add(card.id)
        card.memory_level = new_level

        db.update_card_memory(card.id, new_level, datetime.now())
        if self._session_id:
            mem_before = card.memory_level
            db.record_session_card_result(
                self._session_id, card.id, result,
                memory_before=mem_before, memory_after=new_level
            )

        if delay_ms:
            self.after(delay_ms, self._advance)
        else:
            self._advance()

    def _advance(self):
        self._card_text.configure(text_color=TEXT_PRIMARY)
        if self._index < len(self._queue) - 1:
            self._index += 1
            self._show_card()
        else:
            self._card_text.configure(text="Session complete! 🎉")
            self._action_btn.configure(state="disabled")
            self.after(2000, self._end_session)

    def _go_prev(self):
        if self._index > 0:
            self._index -= 1
            self._show_card()

    def _go_next(self):
        if self._index < len(self._queue) - 1:
            self._index += 1
            self._show_card()

    def _end_session(self):
        if self._session_id:
            db.end_session(self._session_id, len(self._seen))
        self.app.show_home()

    # ── Flip animation ────────────────────────────────────────────────────────

    def _animate_flip(self, on_midpoint):
        """Fade card to black, call on_midpoint, fade back."""
        fade_out = ["#16213e", "#131827", "#100f15", "#080808", "#000000"]
        fade_in  = ["#080808", "#100f15", "#131827", "#16213e"]
        self._animating = True

        def step_out(i=0):
            if i < len(fade_out):
                self._card_frame.configure(fg_color=fade_out[i])
                self.after(25, lambda: step_out(i + 1))
            else:
                on_midpoint()
                step_in(0)

        def step_in(i=0):
            if i < len(fade_in):
                self._card_frame.configure(fg_color=fade_in[i])
                self.after(25, lambda: step_in(i + 1))
            else:
                self._card_frame.configure(fg_color=BG_CARD)
                self._animating = False

        step_out()
```

- [ ] **Step 2: Commit**

```bash
git add ui/review_screen.py
git commit -m "feat: ReviewScreen with flip animation, quiz mode, back/forward nav"
```

---

## Task 11: CreateScreen

**Files:**
- Create: `ui/create_screen.py`

- [ ] **Step 1: Write ui/create_screen.py**

```python
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
from config import (ACCENT, BG_CARD, BG_DARK, BG_INPUT, TEXT_PRIMARY, TEXT_MUTED,
                    CORNER_R, PADDING, FONT_FAMILY)
import data.database as db
from data.models import Card

class CreateScreen(ctk.CTkFrame):
    def __init__(self, app, deck_id: int | None = None):
        super().__init__(app, fg_color=BG_DARK, corner_radius=0)
        self.app     = app
        self._deck_id = deck_id
        self._build()
        self._load_decks()

    def _build(self):
        # Header
        top = ctk.CTkFrame(self, fg_color=BG_DARK)
        top.pack(fill="x", padx=PADDING, pady=(PADDING, 0))
        ctk.CTkButton(top, text="← Back", width=80, fg_color=BG_CARD,
                      hover_color=ACCENT, corner_radius=CORNER_R,
                      command=self.app.show_home).pack(side="left")
        ctk.CTkLabel(top, text="New Card", font=ctk.CTkFont(FONT_FAMILY, 20, "bold"),
                     text_color=TEXT_PRIMARY).pack(side="left", padx=12)

        form = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=CORNER_R)
        form.pack(fill="x", padx=PADDING, pady=PADDING)

        # Deck selector
        row = ctk.CTkFrame(form, fg_color="transparent")
        row.pack(fill="x", padx=PADDING, pady=(PADDING, 0))
        ctk.CTkLabel(row, text="Deck", font=ctk.CTkFont(FONT_FAMILY, 13),
                     text_color=TEXT_MUTED, width=60, anchor="w").pack(side="left")
        self._deck_var = ctk.StringVar(value="")
        self._deck_menu = ctk.CTkOptionMenu(row, variable=self._deck_var, width=260,
                                            fg_color=BG_INPUT, button_color=ACCENT)
        self._deck_menu.pack(side="left", padx=(8, 0))
        ctk.CTkButton(row, text="+ New Deck", width=90, fg_color="transparent",
                      text_color=ACCENT, hover_color=BG_INPUT,
                      command=self._new_deck_dialog).pack(side="left", padx=8)

        # Front / Back
        for attr, label in [("_front_box", "Front"), ("_back_box", "Back")]:
            r = ctk.CTkFrame(form, fg_color="transparent")
            r.pack(fill="x", padx=PADDING, pady=(10, 0))
            ctk.CTkLabel(r, text=label, font=ctk.CTkFont(FONT_FAMILY, 13),
                         text_color=TEXT_MUTED, width=60, anchor="w").pack(side="left")
            tb = ctk.CTkTextbox(r, height=70, width=500, fg_color=BG_INPUT,
                                corner_radius=8, font=ctk.CTkFont(FONT_FAMILY, 13))
            tb.pack(side="left", padx=8)
            setattr(self, attr, tb)

        # is_quiz toggle
        quiz_row = ctk.CTkFrame(form, fg_color="transparent")
        quiz_row.pack(fill="x", padx=PADDING, pady=(10, 0))
        ctk.CTkLabel(quiz_row, text="", width=60).pack(side="left")
        self._quiz_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(quiz_row, text="Quiz card (user must type the answer)",
                        variable=self._quiz_var,
                        font=ctk.CTkFont(FONT_FAMILY, 13), text_color=TEXT_MUTED,
                        checkmark_color="white", fg_color=ACCENT).pack(side="left")

        # Save button
        btn_row = ctk.CTkFrame(form, fg_color="transparent")
        btn_row.pack(fill="x", padx=PADDING, pady=PADDING)
        ctk.CTkButton(btn_row, text="Save Card", width=140, fg_color=ACCENT,
                      hover_color="#5a61e8", corner_radius=CORNER_R,
                      command=self._save_card).pack(side="left")
        ctk.CTkButton(btn_row, text="📷 Scan", width=100, fg_color=BG_INPUT,
                      hover_color=ACCENT, corner_radius=CORNER_R,
                      command=self._scan_camera).pack(side="left", padx=8)
        ctk.CTkButton(btn_row, text="📄 Import PDF", width=120, fg_color=BG_INPUT,
                      hover_color=ACCENT, corner_radius=CORNER_R,
                      command=self._import_pdf).pack(side="left")

        # Generated cards review area
        self._gen_scroll = ctk.CTkScrollableFrame(self, fg_color=BG_DARK,
                                                   label_text="Generated cards — review before saving",
                                                   label_font=ctk.CTkFont(FONT_FAMILY, 13),
                                                   label_text_color=TEXT_MUTED)

    def _load_decks(self):
        decks = db.get_all_decks()
        names = [d.name for d in decks]
        self._deck_map = {d.name: d.id for d in decks}
        if names:
            self._deck_menu.configure(values=names)
            if self._deck_id:
                for d in decks:
                    if d.id == self._deck_id:
                        self._deck_var.set(d.name)
                        break
            else:
                self._deck_var.set(names[0])
        else:
            self._deck_menu.configure(values=["(no decks — create one)"])

    def _get_selected_deck_id(self) -> int | None:
        return self._deck_map.get(self._deck_var.get())

    def _new_deck_dialog(self):
        dialog = ctk.CTkInputDialog(text="Deck name:", title="New Deck")
        name = dialog.get_input()
        if name and name.strip():
            d = db.create_deck(name.strip())
            self._deck_map[d.name] = d.id
            names = list(self._deck_map.keys())
            self._deck_menu.configure(values=names)
            self._deck_var.set(d.name)

    def _save_card(self):
        front = self._front_box.get("1.0", "end").strip()
        back  = self._back_box.get("1.0", "end").strip()
        deck_id = self._get_selected_deck_id()

        if not front or not back:
            messagebox.showwarning("Missing content", "Both front and back are required.")
            return
        if deck_id is None:
            messagebox.showwarning("No deck", "Please select or create a deck first.")
            return

        card = Card(front=front, back=back, is_quiz=self._quiz_var.get(), deck_id=deck_id)
        db.create_card(card)
        self._front_box.delete("1.0", "end")
        self._back_box.delete("1.0", "end")
        messagebox.showinfo("Saved", "Card saved successfully!")

    def _scan_camera(self):
        deck_id = self._get_selected_deck_id()
        if deck_id is None:
            messagebox.showwarning("No deck", "Please select or create a deck first.")
            return
        try:
            image_bytes = self.app.scan.capture_from_camera()
            cards_data  = self.app.claude.generate_cards_from_image(image_bytes)
            self._show_generated_cards(cards_data, deck_id)
        except Exception as e:
            messagebox.showerror("Scan failed", str(e))

    def _import_pdf(self):
        deck_id = self._get_selected_deck_id()
        if deck_id is None:
            messagebox.showwarning("No deck", "Please select or create a deck first.")
            return
        path = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
        if not path:
            return
        try:
            text      = self.app.scan.extract_text_from_pdf(path)
            cards_data = self.app.claude.generate_cards_from_text(text)
            self._show_generated_cards(cards_data, deck_id)
        except Exception as e:
            messagebox.showerror("Import failed", str(e))

    def _show_generated_cards(self, cards_data: list[dict], deck_id: int):
        for w in self._gen_scroll.winfo_children():
            w.destroy()
        self._gen_scroll.pack(fill="both", expand=True, padx=PADDING, pady=(0, PADDING))

        self._gen_entries = []
        for i, cd in enumerate(cards_data):
            row_frame = ctk.CTkFrame(self._gen_scroll, fg_color=BG_CARD, corner_radius=CORNER_R)
            row_frame.pack(fill="x", pady=4)

            front_e = ctk.CTkEntry(row_frame, width=380, fg_color=BG_INPUT, corner_radius=6)
            front_e.insert(0, cd.get("front", ""))
            front_e.pack(side="left", padx=8, pady=8)

            back_e = ctk.CTkEntry(row_frame, width=380, fg_color=BG_INPUT, corner_radius=6)
            back_e.insert(0, cd.get("back", ""))
            back_e.pack(side="left", padx=8)

            quiz_var = ctk.BooleanVar(value=cd.get("is_quiz", False))
            ctk.CTkCheckBox(row_frame, text="Quiz", variable=quiz_var,
                            fg_color=ACCENT, checkmark_color="white").pack(side="left", padx=8)

            del_btn = ctk.CTkButton(row_frame, text="✕", width=30, fg_color=COLOR_RED,
                                    hover_color="#c0392b", corner_radius=6)
            del_btn.pack(side="right", padx=8)

            self._gen_entries.append((front_e, back_e, quiz_var, row_frame))
            del_btn.configure(command=lambda rf=row_frame, idx=len(self._gen_entries)-1:
                              self._remove_gen_row(rf, idx))

        ctk.CTkButton(self._gen_scroll, text="Save All Cards", fg_color=ACCENT,
                      hover_color="#5a61e8", corner_radius=CORNER_R,
                      command=lambda: self._save_generated(deck_id)).pack(pady=8)

    def _remove_gen_row(self, row_frame, idx):
        row_frame.destroy()

    def _save_generated(self, deck_id: int):
        saved = 0
        for front_e, back_e, quiz_var, row_frame in self._gen_entries:
            if not row_frame.winfo_exists():
                continue
            front = front_e.get().strip()
            back  = back_e.get().strip()
            if front and back:
                db.create_card(Card(front=front, back=back,
                                    is_quiz=quiz_var.get(), deck_id=deck_id))
                saved += 1
        messagebox.showinfo("Saved", f"{saved} cards saved to deck.")
        self._gen_scroll.pack_forget()


# Fix missing COLOR_RED import
from config import COLOR_RED
```

- [ ] **Step 2: Fix the COLOR_RED import — move it to the top of the file**

Edit the top import line in `ui/create_screen.py`:

```python
from config import (ACCENT, BG_CARD, BG_DARK, BG_INPUT, TEXT_PRIMARY, TEXT_MUTED,
                    CORNER_R, PADDING, FONT_FAMILY, COLOR_RED)
```

And remove the duplicate import at the bottom.

- [ ] **Step 3: Commit**

```bash
git add ui/create_screen.py
git commit -m "feat: CreateScreen with manual entry, camera scan, PDF import"
```

---

## Task 12: DeckScreen

**Files:**
- Create: `ui/deck_screen.py`

- [ ] **Step 1: Write ui/deck_screen.py**

```python
from tkinter import messagebox
import customtkinter as ctk
from config import (ACCENT, BG_CARD, BG_DARK, BG_INPUT, TEXT_PRIMARY, TEXT_MUTED,
                    CORNER_R, PADDING, FONT_FAMILY, COLOR_RED)
import data.database as db
from data.models import Card

class DeckScreen(ctk.CTkFrame):
    def __init__(self, app, deck_id: int):
        super().__init__(app, fg_color=BG_DARK, corner_radius=0)
        self.app     = app
        self._deck_id = deck_id
        self._build()
        self._load()

    def _build(self):
        top = ctk.CTkFrame(self, fg_color=BG_DARK)
        top.pack(fill="x", padx=PADDING, pady=(PADDING, 0))

        ctk.CTkButton(top, text="← Back", width=80, fg_color=BG_CARD,
                      hover_color=ACCENT, corner_radius=CORNER_R,
                      command=self.app.show_home).pack(side="left")

        self._title = ctk.CTkLabel(top, text="",
                                   font=ctk.CTkFont(FONT_FAMILY, 20, "bold"),
                                   text_color=TEXT_PRIMARY)
        self._title.pack(side="left", padx=12)

        ctk.CTkButton(top, text="✎ Rename", width=90, fg_color=BG_CARD,
                      hover_color=ACCENT, corner_radius=CORNER_R,
                      command=self._rename_deck).pack(side="right")

        ctk.CTkButton(top, text="+ Add Card", width=100, fg_color=ACCENT,
                      hover_color="#5a61e8", corner_radius=CORNER_R,
                      command=lambda: self.app.show_create(deck_id=self._deck_id)).pack(side="right", padx=(0, 8))

        # Search bar
        search_row = ctk.CTkFrame(self, fg_color=BG_DARK)
        search_row.pack(fill="x", padx=PADDING, pady=(10, 0))
        self._search_var = ctk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._load())
        ctk.CTkEntry(search_row, textvariable=self._search_var, width=320,
                     placeholder_text="Search cards…", fg_color=BG_INPUT,
                     corner_radius=8).pack(side="left")

        # Card list
        self._scroll = ctk.CTkScrollableFrame(self, fg_color=BG_DARK, corner_radius=0)
        self._scroll.pack(fill="both", expand=True, padx=PADDING, pady=PADDING)

    def _load(self):
        query = self._search_var.get().lower()
        for w in self._scroll.winfo_children():
            w.destroy()

        # Fetch deck name
        decks = db.get_all_decks()
        for d in decks:
            if d.id == self._deck_id:
                self._title.configure(text=d.name)
                break

        cards = db.get_cards_for_deck(self._deck_id)
        filtered = [c for c in cards if query in c.front.lower() or query in c.back.lower()]

        if not filtered:
            ctk.CTkLabel(self._scroll, text="No cards found.", text_color=TEXT_MUTED,
                         font=ctk.CTkFont(FONT_FAMILY, 14)).pack(pady=30)
            return

        for card in filtered:
            self._card_row(card)

    def _card_row(self, card: Card):
        row = ctk.CTkFrame(self._scroll, fg_color=BG_CARD, corner_radius=CORNER_R)
        row.pack(fill="x", pady=4)

        info = ctk.CTkFrame(row, fg_color="transparent")
        info.pack(side="left", fill="x", expand=True, padx=12, pady=8)

        tag = " [Quiz]" if card.is_quiz else ""
        ctk.CTkLabel(info, text=card.front + tag,
                     font=ctk.CTkFont(FONT_FAMILY, 13, "bold"),
                     text_color=TEXT_PRIMARY, anchor="w").pack(fill="x")
        ctk.CTkLabel(info, text=card.back,
                     font=ctk.CTkFont(FONT_FAMILY, 12),
                     text_color=TEXT_MUTED, anchor="w").pack(fill="x")

        mem_label = ctk.CTkLabel(row, text=f"Mem: {card.memory_level:.0f}%",
                                  font=ctk.CTkFont(FONT_FAMILY, 11), text_color=TEXT_MUTED)
        mem_label.pack(side="right", padx=12)

        ctk.CTkButton(row, text="✕", width=28, height=28, fg_color=COLOR_RED,
                      hover_color="#c0392b", corner_radius=6,
                      command=lambda c=card: self._delete_card(c)).pack(side="right", padx=(0, 8))

        ctk.CTkButton(row, text="✎", width=28, height=28, fg_color=BG_INPUT,
                      hover_color=ACCENT, corner_radius=6,
                      command=lambda c=card: self._edit_card(c)).pack(side="right")

    def _edit_card(self, card: Card):
        modal = ctk.CTkToplevel(self)
        modal.title("Edit Card")
        modal.geometry("560x320")
        modal.configure(fg_color=BG_DARK)
        modal.grab_set()

        for attr, label, value in [
            ("_e_front", "Front", card.front),
            ("_e_back",  "Back",  card.back),
        ]:
            r = ctk.CTkFrame(modal, fg_color="transparent")
            r.pack(fill="x", padx=20, pady=(16 if attr == "_e_front" else 8, 0))
            ctk.CTkLabel(r, text=label, width=50, anchor="w",
                         font=ctk.CTkFont(FONT_FAMILY, 13), text_color=TEXT_MUTED).pack(side="left")
            tb = ctk.CTkTextbox(r, height=70, width=440, fg_color=BG_INPUT,
                                corner_radius=8, font=ctk.CTkFont(FONT_FAMILY, 13))
            tb.insert("1.0", value)
            tb.pack(side="left", padx=8)
            setattr(self, attr, tb)

        quiz_var = ctk.BooleanVar(value=card.is_quiz)
        ctk.CTkCheckBox(modal, text="Quiz card", variable=quiz_var,
                        fg_color=ACCENT, checkmark_color="white",
                        font=ctk.CTkFont(FONT_FAMILY, 13),
                        text_color=TEXT_MUTED).pack(anchor="w", padx=72, pady=8)

        def save():
            card.front   = self._e_front.get("1.0", "end").strip()
            card.back    = self._e_back.get("1.0", "end").strip()
            card.is_quiz = quiz_var.get()
            db.update_card(card)
            modal.destroy()
            self._load()

        ctk.CTkButton(modal, text="Save", fg_color=ACCENT, hover_color="#5a61e8",
                      corner_radius=CORNER_R, command=save).pack(pady=12)

    def _delete_card(self, card: Card):
        if messagebox.askyesno("Delete card", f"Delete '{card.front}'?"):
            db.delete_card(card.id)
            self._load()

    def _rename_deck(self):
        dialog = ctk.CTkInputDialog(text="New deck name:", title="Rename Deck")
        name = dialog.get_input()
        if name and name.strip():
            db.rename_deck(self._deck_id, name.strip())
            self._load()
```

- [ ] **Step 2: Commit**

```bash
git add ui/deck_screen.py
git commit -m "feat: DeckScreen with card list, edit modal, delete, search"
```

---

## Task 13: SettingsScreen

**Files:**
- Create: `ui/settings_screen.py`

- [ ] **Step 1: Write ui/settings_screen.py**

```python
from tkinter import messagebox
import customtkinter as ctk
from config import (ACCENT, BG_CARD, BG_DARK, BG_INPUT, TEXT_PRIMARY, TEXT_MUTED,
                    CORNER_R, PADDING, FONT_FAMILY)
import data.database as db

class SettingsScreen(ctk.CTkFrame):
    def __init__(self, app):
        super().__init__(app, fg_color=BG_DARK, corner_radius=0)
        self.app = app
        self._build()
        self._load()

    def _build(self):
        top = ctk.CTkFrame(self, fg_color=BG_DARK)
        top.pack(fill="x", padx=PADDING, pady=(PADDING, 0))
        ctk.CTkButton(top, text="← Back", width=80, fg_color=BG_CARD,
                      hover_color=ACCENT, corner_radius=CORNER_R,
                      command=self.app.show_home).pack(side="left")
        ctk.CTkLabel(top, text="Settings", font=ctk.CTkFont(FONT_FAMILY, 20, "bold"),
                     text_color=TEXT_PRIMARY).pack(side="left", padx=12)

        form = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=CORNER_R)
        form.pack(fill="x", padx=PADDING, pady=PADDING)

        self._fields = {}
        for key, label, kwargs in [
            ("daily_goal",    "Daily goal (cards)",     {"width": 100}),
            ("notify_time",   "Notify at (HH:MM)",      {"width": 100}),
            ("claude_api_key","Claude API key",          {"width": 400, "show": "*"}),
        ]:
            row = ctk.CTkFrame(form, fg_color="transparent")
            row.pack(fill="x", padx=PADDING, pady=(PADDING, 0))
            ctk.CTkLabel(row, text=label, width=180, anchor="w",
                         font=ctk.CTkFont(FONT_FAMILY, 13),
                         text_color=TEXT_MUTED).pack(side="left")
            show = kwargs.pop("show", "")
            entry = ctk.CTkEntry(row, fg_color=BG_INPUT, corner_radius=8,
                                 show=show, **kwargs)
            entry.pack(side="left", padx=8)
            self._fields[key] = entry

            # Show/hide toggle for API key
            if key == "claude_api_key":
                vis_var = ctk.BooleanVar(value=False)
                def toggle_vis(var=vis_var, e=entry):
                    e.configure(show="" if var.get() else "*")
                ctk.CTkCheckBox(row, text="Show", variable=vis_var,
                                command=toggle_vis, fg_color=ACCENT,
                                checkmark_color="white",
                                font=ctk.CTkFont(FONT_FAMILY, 12),
                                text_color=TEXT_MUTED).pack(side="left", padx=8)

        # Decay rate slider
        decay_row = ctk.CTkFrame(form, fg_color="transparent")
        decay_row.pack(fill="x", padx=PADDING, pady=(PADDING, 0))
        ctk.CTkLabel(decay_row, text="Decay rate (pts/day)", width=180, anchor="w",
                     font=ctk.CTkFont(FONT_FAMILY, 13),
                     text_color=TEXT_MUTED).pack(side="left")
        self._decay_var = ctk.DoubleVar(value=5.0)
        self._decay_label = ctk.CTkLabel(decay_row, text="5.0",
                                          font=ctk.CTkFont(FONT_FAMILY, 13),
                                          text_color=TEXT_PRIMARY, width=30)
        self._decay_label.pack(side="right", padx=(0, PADDING))
        ctk.CTkSlider(decay_row, from_=0, to=20, variable=self._decay_var,
                      width=200, progress_color=ACCENT,
                      command=lambda v: self._decay_label.configure(
                          text=f"{v:.1f}")).pack(side="left", padx=8)

        # Save button
        ctk.CTkButton(form, text="Save Settings", fg_color=ACCENT,
                      hover_color="#5a61e8", corner_radius=CORNER_R,
                      command=self._save).pack(anchor="e", padx=PADDING, pady=PADDING)

    def _load(self):
        settings = db.get_all_settings()
        for key, entry in self._fields.items():
            entry.delete(0, "end")
            entry.insert(0, settings.get(key, ""))
        decay = float(settings.get("decay_rate", "5.0"))
        self._decay_var.set(decay)
        self._decay_label.configure(text=f"{decay:.1f}")

    def _save(self):
        for key, entry in self._fields.items():
            db.set_setting(key, entry.get().strip())
        db.set_setting("decay_rate", f"{self._decay_var.get():.1f}")
        messagebox.showinfo("Saved", "Settings saved.")
        self.app.show_home()
```

- [ ] **Step 2: Commit**

```bash
git add ui/settings_screen.py
git commit -m "feat: SettingsScreen with daily goal, notify time, API key, decay rate"
```

---

## Task 14: main.py — Wire Everything Together

**Files:**
- Create: `main.py`

- [ ] **Step 1: Write main.py**

```python
import data.database as db
from services.claude_service import ClaudeService
from services.scan_service import ScanService
from services.notification_service import NotificationService
import services.review_scheduler as review_scheduler
from ui.app import App

def main():
    # 1. Initialise database (creates file + tables on first run)
    db.init_db()

    # 2. Build services
    api_key          = db.get_setting("claude_api_key")
    claude_service   = ClaudeService(api_key=api_key)
    scan_service     = ScanService()
    notification_svc = NotificationService(
        get_setting=db.get_setting,
        get_today_count=db.get_today_reviewed_count,
    )

    # 3. Start background notification thread + tray icon
    notification_svc.start()

    # 4. Launch UI
    app = App(
        db=db,
        review_scheduler_mod=review_scheduler,
        claude_service=claude_service,
        scan_service=scan_service,
        notification_service=notification_svc,
    )
    app.mainloop()

if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run the app**

```bash
python main.py
```

Expected: App window opens in dark theme. HomeScreen visible with "No decks yet" message. No errors in terminal.

- [ ] **Step 3: Manual smoke test**

Run through these in order:
1. Open Settings → enter a Claude API key → Save
2. HomeScreen → New Card → create a deck called "Test" → add a regular card (front: "Capital of France?", back: "Paris") → Save
3. HomeScreen → New Card → add a quiz card (front: "Formula for water?", back: "H2O", is_quiz checked) → Save
4. HomeScreen → Start Review → verify card appears → flip regular card → verify memory bar updates
5. On quiz card → type wrong answer → verify correct answer shown + Claude explanation loads
6. Navigate Previous → verify earlier card shown (read-only, memory bar unchanged)
7. Settings → change daily goal to 1 → verify progress bar on HomeScreen shows 100% after reviewing 1 card
8. HomeScreen → click a deck tile → verify DeckScreen opens → edit a card → verify changes saved → delete a card with confirmation
9. HomeScreen → New Card → Import PDF (any PDF) → verify generated cards appear for review → Save All

- [ ] **Step 4: Run all tests one final time**

```bash
pytest -v
```

Expected: All tests PASS.

- [ ] **Step 5: Final commit**

```bash
git add main.py
git commit -m "feat: main entry point — wire all services and launch app"
```

---

## Self-Review Against Spec

| Requirement | Covered by |
|---|---|
| Create flashcards manually | Task 11 (CreateScreen form) |
| Scan paper via camera | Task 6 (ScanService), Task 11 (_scan_camera) |
| Import PDF | Task 6 (ScanService), Task 11 (_import_pdf) |
| Memory levels per card | Task 4 (apply_memory_delta), Task 3 (DB) |
| Prioritise low-memory cards in review | Task 4 (build_review_queue 75/25) |
| Save flashcards (persist to SQLite) | Task 3 (database.py) |
| Push notifications for review | Task 7 (NotificationService) |
| Daily goal setting | Task 13 (SettingsScreen), Task 9 (HomeScreen progress bar) |
| One-sided quiz cards with answer eval | Task 10 (ReviewScreen _submit_quiz + _fetch_explanation) |
| Wrong answer → show correct + explain | Task 5 (ClaudeService.explain_answer), Task 10 |
| 75% low-memory + 25% random queue | Task 4 (build_review_queue) |
| Python | All tasks |
| Go back to previous cards in session | Task 10 (_go_prev, _go_next) |
| Dark theme | Task 8 (App, ctk dark mode), config.py |
| Animations + rounded corners | Task 10 (_animate_flip), corner_radius throughout |
| +10 on first review per session | Task 4 (apply_memory_delta already_seen=False) |
| +20 correct quiz, -10 wrong quiz | Task 4 (apply_memory_delta) |
| Memory decay over time | Task 4 (compute_effective_level) |
| Edit flashcards outside review | Task 12 (DeckScreen _edit_card) |
| Claude API for generation + explanation | Task 5 (ClaudeService) |
