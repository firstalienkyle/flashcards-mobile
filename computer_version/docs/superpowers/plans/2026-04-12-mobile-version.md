# Mobile Version Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python/Kivy Android flashcard app in `mobile_version/` that shares a SQLite database with the desktop via WiFi sync, and supports all 5 screens (Home, Deck, Create, Review, Settings).

**Architecture:** The `mobile_version/` directory is a self-contained Python project — `data/` and `services/` are copied verbatim from `computer_version/` (with import paths fixed). The UI layer is rebuilt in Kivy using `ScreenManager`. A Flask server added to `computer_version/sync_server.py` exposes `GET /export` and `POST /import`; the phone calls these via `requests` when the user taps Sync.

**Tech Stack:** Python 3.11+, Kivy 2.3, SQLite, Flask 3.0, requests, openpyxl, plyer (TTS), anthropic SDK

---

## File Map

| Path | Action | Purpose |
|---|---|---|
| `mobile_version/` | Create dir | Root of mobile project |
| `mobile_version/requirements.txt` | Create | Kivy + deps |
| `mobile_version/config.py` | Create | DB path, Claude model constant |
| `mobile_version/data/__init__.py` | Create | Empty |
| `mobile_version/data/models.py` | Copy + fix imports | Card, Deck, ReviewSession, SessionCard dataclasses |
| `mobile_version/data/database.py` | Copy + fix imports | All DB functions |
| `mobile_version/services/__init__.py` | Create | Empty |
| `mobile_version/services/review_scheduler.py` | Copy + fix imports | build_review_queue, answers_match, apply_memory_delta |
| `mobile_version/services/claude_service.py` | Copy + fix imports | ClaudeService |
| `mobile_version/sync_client.py` | Create | pull() and push() over HTTP |
| `mobile_version/main.py` | Create | Kivy App entry point, service wiring |
| `mobile_version/ui/__init__.py` | Create | Empty |
| `mobile_version/ui/app.py` | Create | FlashcardsApp(App) with ScreenManager + show_* methods |
| `mobile_version/ui/home_screen.py` | Create | Deck grid, daily goal, Start Review / New Card |
| `mobile_version/ui/deck_screen.py` | Create | Card list, search, edit/delete |
| `mobile_version/ui/create_screen.py` | Create | Manual entry + TXT/Excel import with dupe detection |
| `mobile_version/ui/review_screen.py` | Create | Flip, quiz, Claude explanation, Android TTS |
| `mobile_version/ui/settings_screen.py` | Create | IP, daily goal, API key, decay rate, Sync button |
| `computer_version/sync_server.py` | Create | Flask GET /export + POST /import |

---

### Task 1: Scaffold mobile_version directory and copy data/services layers

**Files:**
- Create: `mobile_version/requirements.txt`
- Create: `mobile_version/config.py`
- Create: `mobile_version/data/__init__.py`
- Create: `mobile_version/data/models.py`
- Create: `mobile_version/data/database.py`
- Create: `mobile_version/services/__init__.py`
- Create: `mobile_version/services/review_scheduler.py`
- Create: `mobile_version/services/claude_service.py`

- [ ] **Step 1: Create requirements.txt**

```
kivy>=2.3.0
anthropic>=0.25.0
openpyxl>=3.1.0
plyer>=2.1.0
Pillow>=10.3.0
requests>=2.31.0
```

- [ ] **Step 2: Create config.py**

```python
from pathlib import Path

DB_PATH = Path.home() / ".flashcards_mobile" / "flashcards.db"
CLAUDE_MODEL = "claude-sonnet-4-6"
```

- [ ] **Step 3: Create data/__init__.py and services/__init__.py**

Both files are empty — just `touch` them.

- [ ] **Step 4: Create data/models.py**

Identical to `computer_version/data/models.py` — no import changes needed (no imports from the project):

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal, Optional

@dataclass
class Card:
    front: str
    back: str
    is_quiz: bool = False
    memory_level: float = 0.0
    id: Optional[int] = None
    deck_id: Optional[int] = None
    last_reviewed: Optional[datetime] = None
    review_count: int = 0
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
    result: Literal['seen', 'correct', 'incorrect']
    memory_before: float
    memory_after: float
    id: Optional[int] = None
    reviewed_at: datetime = field(default_factory=datetime.now)
```

- [ ] **Step 5: Create data/database.py**

Copy of `computer_version/data/database.py` with two import lines fixed:

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
                memory_level  REAL    NOT NULL DEFAULT 0.0,
                last_reviewed TEXT,
                review_count  INTEGER NOT NULL DEFAULT 0,
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
        """)
        try:
            conn.execute("ALTER TABLE cards ADD COLUMN review_count INTEGER NOT NULL DEFAULT 0")
        except Exception:
            pass

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
    with _conn() as conn:
        row = conn.execute(
            "SELECT COUNT(*) as cnt, AVG(memory_level) as avg FROM cards WHERE deck_id = ?",
            (deck_id,)
        ).fetchone()
        return {"card_count": row["cnt"] or 0, "avg_memory": round(row["avg"] or 0.0, 1)}

def _row_to_card(r: sqlite3.Row) -> Card:
    return Card(
        id=r["id"],
        deck_id=r["deck_id"],
        front=r["front"],
        back=r["back"],
        is_quiz=bool(r["is_quiz"]),
        memory_level=r["memory_level"],
        last_reviewed=datetime.fromisoformat(r["last_reviewed"]) if r["last_reviewed"] else None,
        review_count=r["review_count"],
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
        return Card(
            id=cur.lastrowid, deck_id=card.deck_id, front=card.front, back=card.back,
            is_quiz=card.is_quiz, memory_level=card.memory_level,
            created_at=datetime.fromisoformat(now),
        )

def get_cards_for_deck(deck_id: int) -> list[Card]:
    with _conn() as conn:
        rows = conn.execute("SELECT * FROM cards WHERE deck_id = ? ORDER BY created_at",
                            (deck_id,)).fetchall()
        return [_row_to_card(r) for r in rows]

def get_all_cards() -> list[Card]:
    with _conn() as conn:
        rows = conn.execute("SELECT * FROM cards ORDER BY created_at").fetchall()
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
            "UPDATE cards SET memory_level=?, last_reviewed=?, review_count=review_count+1 WHERE id=?",
            (memory_level, last_reviewed.isoformat(), card_id)
        )

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

- [ ] **Step 6: Create services/review_scheduler.py**

Copy of `computer_version/services/review_scheduler.py` — import is already `from data.models import Card` so no change needed. Write it verbatim:

```python
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
        delta = max(5.0, 20.0 - level * 0.1)
    else:
        delta = -(5.0 + level * 0.1)
    return max(0.0, min(100.0, level + delta))
```

- [ ] **Step 7: Create services/claude_service.py**

Copy of `computer_version/services/claude_service.py` with one import fixed:

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
        if not isinstance(data, list):
            raise ValueError(f"Claude returned unexpected type: {type(data).__name__}")
        return data

    def generate_cards_from_text(self, text: str) -> list[dict]:
        response = self.client.messages.create(
            system="You are a flashcard extraction assistant. Always respond with raw JSON only.",
            model=CLAUDE_MODEL,
            max_tokens=2048,
            messages=[{"role": "user", "content": (
                "Extract flashcards from the following text.\n"
                "Return a JSON array of objects with keys:\n"
                "  - \"front\": the question or term (string)\n"
                "  - \"back\": the answer or definition (string)\n"
                "  - \"is_quiz\": true only for strict definition cards (boolean)\n"
                "Return ONLY valid JSON.\n\n"
                f"Text:\n{text}"
            )}]
        )
        return self._parse_cards(response.content[0].text)

    def explain_answer(self, front: str, back: str) -> str:
        response = self.client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=256,
            messages=[{"role": "user", "content": (
                f"Flashcard:\nQuestion: {front}\nCorrect Answer: {back}\n\n"
                "In 2–3 plain sentences, explain why this is the correct answer."
            )}]
        )
        return response.content[0].text.strip()
```

- [ ] **Step 8: Verify imports work**

```bash
cd /Users/meimozhu/Desktop/flashcards/mobile_version
python3 -c "from data.models import Card, Deck; from data.database import init_db; from services.review_scheduler import build_review_queue; print('OK')"
```

Expected: `OK`

- [ ] **Step 9: Commit**

```bash
cd /Users/meimozhu/Desktop/flashcards
git add mobile_version/
git commit -m "feat: scaffold mobile_version data and services layers"
```

---

### Task 2: Sync server (desktop side)

**Files:**
- Create: `computer_version/sync_server.py`

- [ ] **Step 1: Write a test for the export endpoint**

Create `computer_version/tests/test_sync_server.py`:

```python
import json
import pytest
import data.database as db
from sync_server import create_app

@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr("data.database._DB_PATH", tmp_path / "test.db")
    db.init_db()
    db.create_deck("Spanish")
    from data.models import Card
    db.create_card(Card(front="hola", back="hello", deck_id=1))
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c

def test_export_returns_decks_and_cards(client):
    resp = client.get("/export")
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert len(data["decks"]) == 1
    assert data["decks"][0]["name"] == "Spanish"
    assert len(data["cards"]) == 1
    assert data["cards"][0]["front"] == "hola"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /Users/meimozhu/Desktop/flashcards/computer_version
python3 -m pytest tests/test_sync_server.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'sync_server'`

- [ ] **Step 3: Install flask on desktop**

```bash
pip3 install flask
```

- [ ] **Step 4: Create sync_server.py**

```python
"""
Run with: python sync_server.py
Listens on 0.0.0.0:5000. Phone connects to http://<your-mac-ip>:5000
"""
from flask import Flask, jsonify, request
import data.database as db
from data.models import Card, Deck
from datetime import datetime


def create_app() -> Flask:
    app = Flask(__name__)

    @app.route("/export")
    def export():
        decks = db.get_all_decks()
        cards = db.get_all_cards()
        return jsonify({
            "decks": [
                {"id": d.id, "name": d.name, "created_at": d.created_at.isoformat()}
                for d in decks
            ],
            "cards": [
                {
                    "id": c.id, "deck_id": c.deck_id,
                    "front": c.front, "back": c.back,
                    "is_quiz": c.is_quiz, "memory_level": c.memory_level,
                    "last_reviewed": c.last_reviewed.isoformat() if c.last_reviewed else None,
                    "review_count": c.review_count,
                    "created_at": c.created_at.isoformat(),
                }
                for c in cards
            ],
        })

    @app.route("/import", methods=["POST"])
    def import_data():
        payload = request.get_json(force=True)
        for d in payload.get("decks", []):
            existing = db.get_all_decks()
            ids = {deck.id for deck in existing}
            if d["id"] not in ids:
                db.create_deck(d["name"])
        for c in payload.get("cards", []):
            existing_cards = db.get_all_cards()
            existing_ids = {card.id for card in existing_cards}
            if c["id"] not in existing_ids:
                card = Card(
                    front=c["front"], back=c["back"],
                    is_quiz=c["is_quiz"], memory_level=c["memory_level"],
                    deck_id=c["deck_id"],
                    last_reviewed=datetime.fromisoformat(c["last_reviewed"]) if c["last_reviewed"] else None,
                    review_count=c["review_count"],
                )
                db.create_card(card)
        return jsonify({"status": "ok"})

    return app


if __name__ == "__main__":
    db.init_db()
    app = create_app()
    print("Sync server running on port 5000")
    print("Connect phone to: http://<this-machine-ip>:5000")
    app.run(host="0.0.0.0", port=5000)
```

- [ ] **Step 5: Run test to verify it passes**

```bash
cd /Users/meimozhu/Desktop/flashcards/computer_version
python3 -m pytest tests/test_sync_server.py -v
```

Expected: PASS

- [ ] **Step 6: Commit**

```bash
cd /Users/meimozhu/Desktop/flashcards/computer_version
git add sync_server.py tests/test_sync_server.py
git commit -m "feat: add sync server with GET /export and POST /import"
```

---

### Task 3: Sync client (mobile side)

**Files:**
- Create: `mobile_version/sync_client.py`

- [ ] **Step 1: Write failing tests**

Create `mobile_version/tests/__init__.py` (empty) and `mobile_version/tests/test_sync_client.py`:

```python
import json
import pytest
from unittest.mock import patch, MagicMock
from sync_client import SyncClient

@pytest.fixture
def client():
    return SyncClient(base_url="http://192.168.1.1:5000")

def test_pull_replaces_local_db(client, tmp_path, monkeypatch):
    import data.database as db
    monkeypatch.setattr("data.database._DB_PATH", tmp_path / "test.db")
    db.init_db()

    mock_response = MagicMock()
    mock_response.json.return_value = {
        "decks": [{"id": 1, "name": "Spanish", "created_at": "2026-01-01T00:00:00"}],
        "cards": [{"id": 1, "deck_id": 1, "front": "hola", "back": "hello",
                   "is_quiz": False, "memory_level": 0.0, "last_reviewed": None,
                   "review_count": 0, "created_at": "2026-01-01T00:00:00"}],
    }
    mock_response.raise_for_status = MagicMock()

    with patch("requests.get", return_value=mock_response):
        client.pull()

    decks = db.get_all_decks()
    assert len(decks) == 1
    assert decks[0].name == "Spanish"

def test_push_posts_local_db(client, tmp_path, monkeypatch):
    import data.database as db
    monkeypatch.setattr("data.database._DB_PATH", tmp_path / "test.db")
    db.init_db()
    db.create_deck("Spanish")
    from data.models import Card
    db.create_card(Card(front="adios", back="goodbye", deck_id=1))

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()

    with patch("requests.post", return_value=mock_response) as mock_post:
        client.push()

    assert mock_post.called
    payload = mock_post.call_args[1]["json"]
    assert payload["decks"][0]["name"] == "Spanish"
    assert payload["cards"][0]["front"] == "adios"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/meimozhu/Desktop/flashcards/mobile_version
python3 -m pytest tests/test_sync_client.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'sync_client'`

- [ ] **Step 3: Create sync_client.py**

```python
import requests
import data.database as db
from data.models import Card, Deck
from datetime import datetime


class SyncClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    def pull(self) -> None:
        """Replace local DB with data from desktop."""
        resp = requests.get(f"{self.base_url}/export", timeout=10)
        resp.raise_for_status()
        payload = resp.json()

        # Wipe and re-import all decks and cards
        for deck in db.get_all_decks():
            db.delete_deck(deck.id)

        for d in payload["decks"]:
            db.create_deck(d["name"])

        all_decks = db.get_all_decks()
        # Map original desktop deck ids to new local ids by position/name
        deck_name_to_id = {d.name: d.id for d in all_decks}

        for c in payload["cards"]:
            # Find matching deck by name
            desktop_decks = payload["decks"]
            deck_name = next((d["name"] for d in desktop_decks if d["id"] == c["deck_id"]), None)
            local_deck_id = deck_name_to_id.get(deck_name)
            if local_deck_id is None:
                continue
            card = Card(
                front=c["front"], back=c["back"],
                is_quiz=c["is_quiz"], memory_level=c["memory_level"],
                deck_id=local_deck_id,
                last_reviewed=datetime.fromisoformat(c["last_reviewed"]) if c["last_reviewed"] else None,
                review_count=c["review_count"],
            )
            db.create_card(card)

    def push(self) -> None:
        """Send local DB to desktop for merging."""
        decks = db.get_all_decks()
        cards = db.get_all_cards()
        payload = {
            "decks": [
                {"id": d.id, "name": d.name, "created_at": d.created_at.isoformat()}
                for d in decks
            ],
            "cards": [
                {
                    "id": c.id, "deck_id": c.deck_id,
                    "front": c.front, "back": c.back,
                    "is_quiz": c.is_quiz, "memory_level": c.memory_level,
                    "last_reviewed": c.last_reviewed.isoformat() if c.last_reviewed else None,
                    "review_count": c.review_count,
                    "created_at": c.created_at.isoformat(),
                }
                for c in cards
            ],
        }
        resp = requests.post(f"{self.base_url}/import", json=payload, timeout=10)
        resp.raise_for_status()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /Users/meimozhu/Desktop/flashcards/mobile_version
python3 -m pytest tests/test_sync_client.py -v
```

Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
cd /Users/meimozhu/Desktop/flashcards
git add mobile_version/sync_client.py mobile_version/tests/
git commit -m "feat: mobile sync client with pull and push"
```

---

### Task 4: Kivy App shell and HomeScreen

**Files:**
- Create: `mobile_version/main.py`
- Create: `mobile_version/ui/__init__.py`
- Create: `mobile_version/ui/app.py`
- Create: `mobile_version/ui/home_screen.py`

- [ ] **Step 1: Install Kivy**

```bash
pip3 install kivy
```

- [ ] **Step 2: Create ui/__init__.py**

Empty file.

- [ ] **Step 3: Create ui/app.py**

```python
from kivy.app import App
from kivy.uix.screenmanager import ScreenManager


class FlashcardsApp(App):
    def __init__(self, db, review_scheduler_mod, claude_service, sync_client, **kwargs):
        super().__init__(**kwargs)
        self.db = db
        self.rs = review_scheduler_mod
        self.claude = claude_service
        self.sync = sync_client
        self.sm = ScreenManager()

    def build(self):
        self.show_home()
        return self.sm

    def _switch(self, screen):
        name = screen.name
        if self.sm.has_screen(name):
            self.sm.remove_widget(self.sm.get_screen(name))
        self.sm.add_widget(screen)
        self.sm.current = name

    def show_home(self):
        from ui.home_screen import HomeScreen
        self._switch(HomeScreen(self, name='home'))

    def show_deck(self, deck_id):
        from ui.deck_screen import DeckScreen
        self._switch(DeckScreen(self, deck_id=deck_id, name='deck'))

    def show_create(self, deck_id=None):
        from ui.create_screen import CreateScreen
        self._switch(CreateScreen(self, deck_id=deck_id, name='create'))

    def show_review(self):
        from ui.review_screen import ReviewScreen
        self._switch(ReviewScreen(self, name='review'))

    def show_settings(self):
        from ui.settings_screen import SettingsScreen
        self._switch(SettingsScreen(self, name='settings'))
```

- [ ] **Step 4: Create ui/home_screen.py**

```python
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.progressbar import ProgressBar
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget


class HomeScreen(Screen):
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self._build()

    def _build(self):
        root = BoxLayout(orientation='vertical', padding=16, spacing=12)

        # Top bar
        top = BoxLayout(size_hint_y=None, height=48, spacing=8)
        top.add_widget(Label(text='Flashcards', font_size='20sp', bold=True,
                             size_hint_x=None, width=200, halign='left'))
        top.add_widget(Widget())
        settings_btn = Button(text='⚙ Settings', size_hint_x=None, width=120)
        settings_btn.bind(on_press=lambda _: self.app.show_settings())
        top.add_widget(settings_btn)
        root.add_widget(top)

        # Daily goal
        goal_row = BoxLayout(size_hint_y=None, height=40, spacing=8)
        self._goal_label = Label(text='Loading...', halign='left')
        goal_row.add_widget(self._goal_label)
        self._progress = ProgressBar(max=10, value=0, size_hint_x=None, width=200)
        goal_row.add_widget(self._progress)
        root.add_widget(goal_row)

        # Action buttons
        btn_row = BoxLayout(size_hint_y=None, height=48, spacing=8)
        review_btn = Button(text='▶  Start Review', size_hint_x=None, width=160)
        review_btn.bind(on_press=lambda _: self.app.show_review())
        btn_row.add_widget(review_btn)
        new_btn = Button(text='+  New Card', size_hint_x=None, width=140)
        new_btn.bind(on_press=lambda _: self.app.show_create())
        btn_row.add_widget(new_btn)
        btn_row.add_widget(Widget())
        root.add_widget(btn_row)

        # Deck grid
        scroll = ScrollView()
        self._grid = GridLayout(cols=2, spacing=8, size_hint_y=None, padding=4)
        self._grid.bind(minimum_height=self._grid.setter('height'))
        scroll.add_widget(self._grid)
        root.add_widget(scroll)

        self.add_widget(root)

    def on_enter(self):
        self._load()

    def _load(self):
        goal = int(self.app.db.get_setting('daily_goal') or 10)
        count = self.app.db.get_today_reviewed_count()
        self._goal_label.text = f'{count} / {goal} cards reviewed today'
        self._progress.max = goal
        self._progress.value = min(count, goal)

        self._grid.clear_widgets()
        decks = self.app.db.get_all_decks()
        if not decks:
            self._grid.add_widget(Label(text='No decks yet — create your first card!'))
            return
        for deck in decks:
            stats = self.app.db.get_deck_stats(deck.id)
            tile = Button(
                text=f'{deck.name}\n{stats["card_count"]} cards\nMemory: {stats["avg_memory"]:.0f}%',
                size_hint_y=None, height=100,
                halign='left', valign='top',
            )
            tile.bind(on_press=lambda _, did=deck.id: self.app.show_deck(did))
            self._grid.add_widget(tile)
```

- [ ] **Step 5: Create main.py**

```python
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import data.database as db
from services.claude_service import ClaudeService
import services.review_scheduler as review_scheduler
from sync_client import SyncClient
from ui.app import FlashcardsApp


def main():
    db.init_db()
    api_key = db.get_setting('claude_api_key')
    claude_service = ClaudeService(api_key=api_key)
    desktop_ip = db.get_setting('desktop_ip') or 'http://localhost:5000'
    sync_client = SyncClient(base_url=desktop_ip)

    FlashcardsApp(
        db=db,
        review_scheduler_mod=review_scheduler,
        claude_service=claude_service,
        sync_client=sync_client,
    ).run()


if __name__ == '__main__':
    main()
```

- [ ] **Step 6: Smoke test — app launches and shows HomeScreen**

```bash
cd /Users/meimozhu/Desktop/flashcards/mobile_version
python3 main.py
```

Expected: Kivy window opens showing "Flashcards" title and daily goal bar.

- [ ] **Step 7: Commit**

```bash
cd /Users/meimozhu/Desktop/flashcards
git add mobile_version/main.py mobile_version/ui/
git commit -m "feat: Kivy app shell and HomeScreen"
```

---

### Task 5: DeckScreen

**Files:**
- Create: `mobile_version/ui/deck_screen.py`

- [ ] **Step 1: Create ui/deck_screen.py**

```python
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.uix.widget import Widget
from data.models import Card


class DeckScreen(Screen):
    def __init__(self, app, deck_id, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self._deck_id = deck_id
        self._build()

    def _build(self):
        root = BoxLayout(orientation='vertical', padding=16, spacing=10)

        top = BoxLayout(size_hint_y=None, height=48, spacing=8)
        back_btn = Button(text='← Back', size_hint_x=None, width=100)
        back_btn.bind(on_press=lambda _: self.app.show_home())
        top.add_widget(back_btn)
        self._title = Label(text='Deck', font_size='18sp', bold=True)
        top.add_widget(self._title)
        top.add_widget(Widget())
        add_btn = Button(text='+ Card', size_hint_x=None, width=90)
        add_btn.bind(on_press=lambda _: self.app.show_create(self._deck_id))
        top.add_widget(add_btn)
        root.add_widget(top)

        self._search = TextInput(hint_text='Search cards...', size_hint_y=None,
                                  height=40, multiline=False)
        self._search.bind(text=self._on_search)
        root.add_widget(self._search)

        scroll = ScrollView()
        self._card_list = GridLayout(cols=1, spacing=4, size_hint_y=None, padding=4)
        self._card_list.bind(minimum_height=self._card_list.setter('height'))
        scroll.add_widget(self._card_list)
        root.add_widget(scroll)

        self.add_widget(root)

    def on_enter(self):
        self._load()

    def _load(self, filter_text=''):
        decks = self.app.db.get_all_decks()
        deck = next((d for d in decks if d.id == self._deck_id), None)
        if deck:
            self._title.text = deck.name

        cards = self.app.db.get_cards_for_deck(self._deck_id)
        if filter_text:
            q = filter_text.lower()
            cards = [c for c in cards if q in c.front.lower() or q in c.back.lower()]

        self._card_list.clear_widgets()
        for card in cards:
            row = BoxLayout(size_hint_y=None, height=56, spacing=6)
            lbl = Label(
                text=f'{card.front[:40]}  →  {card.back[:40]}',
                halign='left', size_hint_x=1,
            )
            row.add_widget(lbl)
            edit_btn = Button(text='Edit', size_hint_x=None, width=70)
            edit_btn.bind(on_press=lambda _, c=card: self._edit_dialog(c))
            row.add_widget(edit_btn)
            del_btn = Button(text='Del', size_hint_x=None, width=60)
            del_btn.bind(on_press=lambda _, cid=card.id: self._delete_card(cid))
            row.add_widget(del_btn)
            self._card_list.add_widget(row)

    def _on_search(self, instance, value):
        self._load(filter_text=value)

    def _delete_card(self, card_id):
        self.app.db.delete_card(card_id)
        self._load(filter_text=self._search.text)

    def _edit_dialog(self, card):
        content = BoxLayout(orientation='vertical', padding=10, spacing=8)
        front_input = TextInput(text=card.front, multiline=True, size_hint_y=None, height=80)
        back_input = TextInput(text=card.back, multiline=True, size_hint_y=None, height=80)
        content.add_widget(Label(text='Front:', size_hint_y=None, height=28))
        content.add_widget(front_input)
        content.add_widget(Label(text='Back:', size_hint_y=None, height=28))
        content.add_widget(back_input)
        btn_row = BoxLayout(size_hint_y=None, height=44, spacing=8)

        popup = Popup(title='Edit Card', content=content, size_hint=(0.9, 0.7))

        def _save(_):
            card.front = front_input.text.strip()
            card.back = back_input.text.strip()
            if card.front and card.back:
                self.app.db.update_card(card)
                popup.dismiss()
                self._load(filter_text=self._search.text)

        save_btn = Button(text='Save')
        save_btn.bind(on_press=_save)
        cancel_btn = Button(text='Cancel')
        cancel_btn.bind(on_press=popup.dismiss)
        btn_row.add_widget(save_btn)
        btn_row.add_widget(cancel_btn)
        content.add_widget(btn_row)
        popup.open()
```

- [ ] **Step 2: Smoke test — tap a deck tile on HomeScreen, DeckScreen opens**

```bash
cd /Users/meimozhu/Desktop/flashcards/mobile_version
python3 main.py
```

Expected: Tap a deck → DeckScreen shows card list with Edit / Del buttons.

- [ ] **Step 3: Commit**

```bash
cd /Users/meimozhu/Desktop/flashcards
git add mobile_version/ui/deck_screen.py
git commit -m "feat: mobile DeckScreen with card list, search, edit, delete"
```

---

### Task 6: CreateScreen

**Files:**
- Create: `mobile_version/ui/create_screen.py`

- [ ] **Step 1: Create ui/create_screen.py**

```python
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from kivy.uix.scrollview import ScrollView
from kivy.uix.popup import Popup
from kivy.uix.widget import Widget
from data.models import Card


class CreateScreen(Screen):
    def __init__(self, app, deck_id=None, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self._deck_id = deck_id
        self._deck_map = {}
        self._gen_rows = []
        self._build()

    def _build(self):
        root = BoxLayout(orientation='vertical', padding=16, spacing=10)

        top = BoxLayout(size_hint_y=None, height=48, spacing=8)
        back_btn = Button(text='← Back', size_hint_x=None, width=100)
        back_btn.bind(on_press=lambda _: self.app.show_home())
        top.add_widget(back_btn)
        top.add_widget(Label(text='New Card', font_size='18sp', bold=True))
        top.add_widget(Widget())
        root.add_widget(top)

        # Deck selector
        deck_row = BoxLayout(size_hint_y=None, height=44, spacing=8)
        deck_row.add_widget(Label(text='Deck:', size_hint_x=None, width=60))
        self._deck_spinner = Spinner(text='Select deck', values=[], size_hint_x=1)
        deck_row.add_widget(self._deck_spinner)
        new_deck_btn = Button(text='+ New', size_hint_x=None, width=80)
        new_deck_btn.bind(on_press=self._new_deck_dialog)
        deck_row.add_widget(new_deck_btn)
        root.add_widget(deck_row)

        # Front / Back inputs
        root.add_widget(Label(text='Front:', size_hint_y=None, height=28, halign='left'))
        self._front_input = TextInput(multiline=True, size_hint_y=None, height=80)
        root.add_widget(self._front_input)
        root.add_widget(Label(text='Back:', size_hint_y=None, height=28, halign='left'))
        self._back_input = TextInput(multiline=True, size_hint_y=None, height=80)
        root.add_widget(self._back_input)

        # Buttons
        btn_row = BoxLayout(size_hint_y=None, height=48, spacing=8)
        save_btn = Button(text='Save Card', size_hint_x=None, width=130)
        save_btn.bind(on_press=self._save_card)
        btn_row.add_widget(save_btn)
        txt_btn = Button(text='📄 Import TXT', size_hint_x=None, width=150)
        txt_btn.bind(on_press=self._import_txt_dialog)
        btn_row.add_widget(txt_btn)
        btn_row.add_widget(Widget())
        root.add_widget(btn_row)

        # Generated cards area
        self._gen_label = Label(text='Imported cards — review before saving',
                                size_hint_y=None, height=28, bold=True)
        self._gen_label.opacity = 0
        root.add_widget(self._gen_label)

        scroll = ScrollView()
        self._gen_layout = GridLayout(cols=1, spacing=4, size_hint_y=None, padding=4)
        self._gen_layout.bind(minimum_height=self._gen_layout.setter('height'))
        scroll.add_widget(self._gen_layout)
        root.add_widget(scroll)

        self.add_widget(root)

    def on_enter(self):
        self._load_decks()

    def _load_decks(self):
        decks = self.app.db.get_all_decks()
        self._deck_map = {d.name: d.id for d in decks}
        self._deck_spinner.values = list(self._deck_map.keys())
        if self._deck_id is not None:
            for d in decks:
                if d.id == self._deck_id:
                    self._deck_spinner.text = d.name
                    break
        elif decks:
            self._deck_spinner.text = decks[0].name

    def _get_selected_deck_id(self):
        return self._deck_map.get(self._deck_spinner.text)

    def _new_deck_dialog(self, _):
        content = BoxLayout(orientation='vertical', padding=10, spacing=8)
        name_input = TextInput(hint_text='Deck name', multiline=False,
                               size_hint_y=None, height=44)
        content.add_widget(name_input)
        btn_row = BoxLayout(size_hint_y=None, height=44, spacing=8)
        popup = Popup(title='New Deck', content=content, size_hint=(0.8, 0.4))

        def _create(_):
            name = name_input.text.strip()
            if name:
                d = self.app.db.create_deck(name)
                self._deck_map[d.name] = d.id
                self._deck_spinner.values = list(self._deck_map.keys())
                self._deck_spinner.text = d.name
                popup.dismiss()

        create_btn = Button(text='Create')
        create_btn.bind(on_press=_create)
        cancel_btn = Button(text='Cancel')
        cancel_btn.bind(on_press=popup.dismiss)
        btn_row.add_widget(create_btn)
        btn_row.add_widget(cancel_btn)
        content.add_widget(btn_row)
        popup.open()

    def _save_card(self, _):
        front = self._front_input.text.strip()
        back = self._back_input.text.strip()
        deck_id = self._get_selected_deck_id()
        if not front or not back or deck_id is None:
            return
        self.app.db.create_card(Card(front=front, back=back, deck_id=deck_id))
        self._front_input.text = ''
        self._back_input.text = ''

    def _import_txt_dialog(self, _):
        content = BoxLayout(orientation='vertical', padding=10, spacing=8)
        path_input = TextInput(hint_text='/path/to/file.txt', multiline=False,
                               size_hint_y=None, height=44)
        content.add_widget(Label(text='Enter full path to TXT file:', size_hint_y=None, height=28))
        content.add_widget(path_input)
        btn_row = BoxLayout(size_hint_y=None, height=44, spacing=8)
        popup = Popup(title='Import TXT', content=content, size_hint=(0.9, 0.45))

        def _load(_):
            popup.dismiss()
            self._import_txt(path_input.text.strip())

        ok_btn = Button(text='Import')
        ok_btn.bind(on_press=_load)
        cancel_btn = Button(text='Cancel')
        cancel_btn.bind(on_press=popup.dismiss)
        btn_row.add_widget(ok_btn)
        btn_row.add_widget(cancel_btn)
        content.add_widget(btn_row)
        popup.open()

    def _import_txt(self, path):
        deck_id = self._get_selected_deck_id()
        if not deck_id or not path:
            return
        try:
            with open(path, encoding='utf-8') as f:
                text = f.read()
        except Exception:
            return
        blocks = [b.strip() for b in text.split('\n\n') if b.strip()]
        if len(blocks) < 2:
            return
        cards_data = []
        for i in range(0, len(blocks) - 1, 2):
            cards_data.append({'front': blocks[i], 'back': blocks[i + 1]})
        existing = {c.front.strip().lower()
                    for c in self.app.db.get_cards_for_deck(deck_id)}
        unique = [cd for cd in cards_data
                  if cd['front'].strip().lower() not in existing]
        if not unique:
            return
        self._show_generated(unique, deck_id)

    def _show_generated(self, cards_data, deck_id):
        self._gen_rows = []
        self._gen_layout.clear_widgets()
        self._gen_label.opacity = 1

        for cd in cards_data:
            row = BoxLayout(size_hint_y=None, height=52, spacing=6)
            front_e = TextInput(text=cd['front'], multiline=False, size_hint_x=0.45)
            back_e = TextInput(text=cd['back'], multiline=False, size_hint_x=0.45)
            del_btn = Button(text='✕', size_hint_x=None, width=44)
            del_btn.bind(on_press=lambda _, r=row: (
                self._gen_layout.remove_widget(r),
                self._gen_rows.remove(r) if r in self._gen_rows else None,
            ))
            row.add_widget(front_e)
            row.add_widget(back_e)
            row.add_widget(del_btn)
            self._gen_layout.add_widget(row)
            self._gen_rows.append((front_e, back_e, row))

        save_all = Button(text='Save All Cards', size_hint_y=None, height=48)
        save_all.bind(on_press=lambda _: self._save_generated(deck_id))
        self._gen_layout.add_widget(save_all)

    def _save_generated(self, deck_id):
        saved = 0
        for front_e, back_e, row in self._gen_rows:
            if row.parent is None:
                continue
            front = front_e.text.strip()
            back = back_e.text.strip()
            if front and back:
                self.app.db.create_card(Card(front=front, back=back, deck_id=deck_id))
                saved += 1
        self._gen_layout.clear_widgets()
        self._gen_rows = []
        self._gen_label.opacity = 0
```

- [ ] **Step 2: Smoke test**

```bash
cd /Users/meimozhu/Desktop/flashcards/mobile_version
python3 main.py
```

Expected: Tap "+ New Card" → CreateScreen with deck selector, front/back inputs, Save and Import TXT buttons.

- [ ] **Step 3: Commit**

```bash
cd /Users/meimozhu/Desktop/flashcards
git add mobile_version/ui/create_screen.py
git commit -m "feat: mobile CreateScreen with manual entry and TXT import"
```

---

### Task 7: ReviewScreen

**Files:**
- Create: `mobile_version/ui/review_screen.py`

- [ ] **Step 1: Create ui/review_screen.py**

```python
import threading
from datetime import datetime
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget
from kivy.clock import Clock
from services.review_scheduler import (
    build_review_queue, answers_match, apply_memory_delta,
)
import data.database as db


def _extract_word(text: str) -> str:
    for line in text.splitlines():
        line = line.strip()
        if line:
            return line
    return text.strip()


def _speak(text: str, lang: str = 'en'):
    def _run():
        try:
            from plyer import tts
            tts.speak(_extract_word(text))
        except Exception:
            pass
    threading.Thread(target=_run, daemon=True).start()


class ReviewScreen(Screen):
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self._queue = []
        self._index = 0
        self._seen = set()
        self._session_id = None
        self._showing_front = True
        self._play_counts = {}
        self._build()

    def _build(self):
        root = BoxLayout(orientation='vertical', padding=16, spacing=10)

        top = BoxLayout(size_hint_y=None, height=48, spacing=8)
        home_btn = Button(text='← Home', size_hint_x=None, width=100)
        home_btn.bind(on_press=lambda _: self._end_session())
        top.add_widget(home_btn)
        top.add_widget(Widget())
        self._progress_label = Label(text='')
        top.add_widget(self._progress_label)
        root.add_widget(top)

        # Card area
        self._side_label = Label(text='FRONT', size_hint_y=None, height=24,
                                  color=(0.5, 0.5, 0.5, 1), font_size='11sp')
        root.add_widget(self._side_label)

        self._card_label = Label(text='', font_size='20sp', bold=True,
                                  size_hint_y=1, halign='left', valign='top',
                                  text_size=(None, None))
        self._card_label.bind(size=lambda inst, val: setattr(inst, 'text_size', (val[0], None)))
        root.add_widget(self._card_label)

        self._speak_btn = Button(text='🔊 Speak', size_hint_y=None, height=44,
                                  size_hint_x=None, width=120)
        self._speak_btn.bind(on_press=lambda _: self._play_audio())
        root.add_widget(self._speak_btn)

        self._quiz_input = TextInput(hint_text='Type your answer…', size_hint_y=None,
                                      height=44, multiline=False)
        self._quiz_input.opacity = 0
        self._quiz_input.disabled = True
        root.add_widget(self._quiz_input)

        self._feedback_label = Label(text='', size_hint_y=None, height=36,
                                      font_size='16sp')
        root.add_widget(self._feedback_label)

        self._explanation_label = Label(text='', size_hint_y=None, height=60,
                                         color=(0.5, 0.5, 0.5, 1), font_size='12sp',
                                         halign='left', valign='top')
        self._explanation_label.bind(size=lambda inst, val: setattr(inst, 'text_size', (val[0], None)))
        root.add_widget(self._explanation_label)

        # Nav buttons
        nav = BoxLayout(size_hint_y=None, height=52, spacing=8)
        self._prev_btn = Button(text='← Prev', size_hint_x=None, width=100)
        self._prev_btn.bind(on_press=lambda _: self._go_prev())
        nav.add_widget(self._prev_btn)

        self._action_btn = Button(text='Flip', size_hint_x=1)
        self._action_btn.bind(on_press=lambda _: self._on_action())
        nav.add_widget(self._action_btn)

        self._next_btn = Button(text='Next →', size_hint_x=None, width=100)
        self._next_btn.bind(on_press=lambda _: self._go_next())
        nav.add_widget(self._next_btn)
        root.add_widget(nav)

        self.add_widget(root)

    def on_enter(self):
        self._start_session()

    def _start_session(self):
        decay_rate = float(self.app.db.get_setting('decay_rate') or 5)
        all_cards = db.get_all_cards()
        self._queue = build_review_queue(all_cards, decay_rate)
        if not self._queue:
            self._card_label.text = 'No cards to review!'
            return
        self._index = 0
        self._seen = set()
        self._session_id = db.create_session().id
        self._show_card()

    def _show_card(self):
        card = self._queue[self._index]
        self._showing_front = True
        self._side_label.text = 'FRONT'
        self._card_label.text = card.front
        self._feedback_label.text = ''
        self._explanation_label.text = ''
        self._quiz_input.text = ''
        self._quiz_input.opacity = 0
        self._quiz_input.disabled = True
        self._action_btn.text = 'Flip'
        self._progress_label.text = f'{self._index + 1} / {len(self._queue)}'
        self._speak_btn.opacity = 1
        self._speak_btn.disabled = False

    def _on_action(self):
        if self._action_btn.text == 'Flip':
            self._flip()
        elif self._action_btn.text == 'Submit':
            self._submit_quiz()

    def _flip(self):
        card = self._queue[self._index]
        self._showing_front = False
        self._side_label.text = 'BACK'
        self._card_label.text = card.back

        if card.is_quiz:
            self._quiz_input.opacity = 1
            self._quiz_input.disabled = False
            self._action_btn.text = 'Submit'
        else:
            already_seen = card.id in self._seen
            self._seen.add(card.id)
            new_level = apply_memory_delta(card, 'seen', already_seen)
            self._record(card, 'seen', new_level)
            self._action_btn.text = 'Next →'

    def _submit_quiz(self):
        card = self._queue[self._index]
        user_ans = self._quiz_input.text.strip()
        correct = card.back
        already_seen = card.id in self._seen
        self._seen.add(card.id)
        if answers_match(user_ans, correct):
            self._feedback_label.text = '✓ Correct!'
            self._feedback_label.color = (0.2, 0.8, 0.2, 1)
            new_level = apply_memory_delta(card, 'correct', already_seen)
            self._record(card, 'correct', new_level)
        else:
            self._feedback_label.text = f'✗ Incorrect — {_extract_word(correct)}'
            self._feedback_label.color = (0.9, 0.2, 0.2, 1)
            new_level = apply_memory_delta(card, 'incorrect', already_seen)
            self._record(card, 'incorrect', new_level)
            self._fetch_explanation(card)
        self._quiz_input.disabled = True
        self._action_btn.text = 'Next →'

    def _record(self, card, result, new_level):
        db.record_session_card_result(
            self._session_id, card.id, result, card.memory_level, new_level
        )
        db.update_card_memory(card.id, new_level, datetime.now())
        card.memory_level = new_level

    def _fetch_explanation(self, card):
        def _run():
            try:
                text = self.app.claude.explain_answer(card.front, card.back)
            except Exception:
                text = ''
            Clock.schedule_once(lambda dt: setattr(self._explanation_label, 'text', text))
        threading.Thread(target=_run, daemon=True).start()

    def _go_next(self):
        if self._index < len(self._queue) - 1:
            self._index += 1
            self._show_card()
        else:
            self._end_session()

    def _go_prev(self):
        if self._index > 0:
            self._index -= 1
            self._show_card()

    def _play_audio(self):
        card = self._queue[self._index]
        lang = 'es' if self._showing_front else 'en'
        text = card.front if self._showing_front else card.back
        _speak(text, lang=lang)

    def _end_session(self):
        if self._session_id:
            db.end_session(self._session_id, len(self._seen))
            self._session_id = None
        self.app.show_home()
```

- [ ] **Step 2: Smoke test**

```bash
cd /Users/meimozhu/Desktop/flashcards/mobile_version
python3 main.py
```

Expected: Tap "▶ Start Review" → ReviewScreen shows first card front, Flip button, Speak button.

- [ ] **Step 3: Commit**

```bash
cd /Users/meimozhu/Desktop/flashcards
git add mobile_version/ui/review_screen.py
git commit -m "feat: mobile ReviewScreen with flip, quiz, TTS, Claude explanation"
```

---

### Task 8: SettingsScreen

**Files:**
- Create: `mobile_version/ui/settings_screen.py`

- [ ] **Step 1: Create ui/settings_screen.py**

```python
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget
from kivy.uix.popup import Popup
import threading


class SettingsScreen(Screen):
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self._build()

    def _build(self):
        root = BoxLayout(orientation='vertical', padding=16, spacing=12)

        top = BoxLayout(size_hint_y=None, height=48, spacing=8)
        back_btn = Button(text='← Back', size_hint_x=None, width=100)
        back_btn.bind(on_press=lambda _: self.app.show_home())
        top.add_widget(back_btn)
        top.add_widget(Label(text='Settings', font_size='18sp', bold=True))
        top.add_widget(Widget())
        root.add_widget(top)

        fields = [
            ('Desktop IP', 'desktop_ip', 'http://192.168.1.x:5000', False),
            ('Daily goal', 'daily_goal', '20', False),
            ('Claude API key', 'claude_api_key', 'sk-ant-...', True),
            ('Decay rate', 'decay_rate', '5', False),
        ]
        self._inputs = {}
        for label, key, hint, password in fields:
            row = BoxLayout(size_hint_y=None, height=44, spacing=8)
            row.add_widget(Label(text=label + ':', size_hint_x=None, width=140))
            inp = TextInput(hint_text=hint, multiline=False,
                            password=password, size_hint_x=1)
            self._inputs[key] = inp
            row.add_widget(inp)
            root.add_widget(row)

        save_btn = Button(text='Save Settings', size_hint_y=None, height=48)
        save_btn.bind(on_press=self._save)
        root.add_widget(save_btn)

        root.add_widget(Label(text='Sync', font_size='16sp', bold=True,
                               size_hint_y=None, height=32))
        sync_row = BoxLayout(size_hint_y=None, height=48, spacing=8)
        pull_btn = Button(text='⬇ Pull from Desktop')
        pull_btn.bind(on_press=lambda _: self._sync('pull'))
        push_btn = Button(text='⬆ Push to Desktop')
        push_btn.bind(on_press=lambda _: self._sync('push'))
        sync_row.add_widget(pull_btn)
        sync_row.add_widget(push_btn)
        root.add_widget(sync_row)

        self._status_label = Label(text='', size_hint_y=None, height=32,
                                    color=(0.5, 0.5, 0.5, 1))
        root.add_widget(self._status_label)
        root.add_widget(Widget())

        self.add_widget(root)

    def on_enter(self):
        for key, inp in self._inputs.items():
            inp.text = self.app.db.get_setting(key) or ''

    def _save(self, _):
        for key, inp in self._inputs.items():
            val = inp.text.strip()
            if val:
                self.app.db.set_setting(key, val)
        # Update sync client URL
        ip = self.app.db.get_setting('desktop_ip') or 'http://localhost:5000'
        self.app.sync.base_url = ip.rstrip('/')
        self._status_label.text = 'Settings saved.'

    def _sync(self, direction):
        self._status_label.text = f'{"Pulling" if direction == "pull" else "Pushing"}...'
        def _run():
            try:
                if direction == 'pull':
                    self.app.sync.pull()
                    msg = 'Pull complete.'
                else:
                    self.app.sync.push()
                    msg = 'Push complete.'
            except Exception as e:
                msg = f'Error: {e}'
            from kivy.clock import Clock
            Clock.schedule_once(lambda dt: setattr(self._status_label, 'text', msg))
        threading.Thread(target=_run, daemon=True).start()
```

- [ ] **Step 2: Smoke test**

```bash
cd /Users/meimozhu/Desktop/flashcards/mobile_version
python3 main.py
```

Expected: Tap "⚙ Settings" → SettingsScreen shows IP, daily goal, API key, decay rate fields, Save button, Pull/Push buttons.

- [ ] **Step 3: Commit**

```bash
cd /Users/meimozhu/Desktop/flashcards
git add mobile_version/ui/settings_screen.py
git commit -m "feat: mobile SettingsScreen with save and sync buttons"
```

---

### Task 9: End-to-end smoke test

- [ ] **Step 1: Full app launch test**

```bash
cd /Users/meimozhu/Desktop/flashcards/mobile_version
python3 main.py
```

Walk through:
1. HomeScreen loads — shows daily goal bar and deck grid
2. Tap "+ New Card" → CreateScreen, create a deck and card → tap Save Card
3. Tap "← Back" → HomeScreen shows the new deck tile
4. Tap deck tile → DeckScreen shows the card, Edit and Del work
5. Tap "▶ Start Review" → ReviewScreen shows card, Flip works, Next advances
6. Tap "⚙ Settings" → SettingsScreen, type values, tap Save — status shows "Settings saved."

Expected: All 5 screens navigate correctly with no crashes.

- [ ] **Step 2: Sync test (requires desktop running sync_server.py)**

On desktop:
```bash
cd /Users/meimozhu/Desktop/flashcards/computer_version
python3 sync_server.py
```

On phone (or laptop simulating phone):
- Open Settings, set Desktop IP to `http://<mac-local-ip>:5000`
- Tap "⬇ Pull from Desktop"

Expected: Status shows "Pull complete." and HomeScreen shows desktop decks after navigating back.

- [ ] **Step 3: Final commit**

```bash
cd /Users/meimozhu/Desktop/flashcards
git add .
git commit -m "feat: mobile version complete — Kivy app with all 5 screens and WiFi sync"
```

---

## Self-Review

**Spec coverage:**
- ✅ `mobile_version/` directory with all layers — Tasks 1, 4–8
- ✅ `data/` and `services/` copied with fixed imports — Task 1
- ✅ Flask sync server `GET /export` + `POST /import` — Task 2
- ✅ Sync client `pull()` and `push()` — Task 3
- ✅ All 5 Kivy screens — Tasks 4–8
- ✅ Android TTS via `plyer.tts` replacing macOS `say` — Task 7
- ✅ Duplicate detection on TXT import — Task 6
- ✅ Manual sync via Settings screen button — Task 8
- ✅ Desktop IP stored in settings DB — Task 8

**Placeholder scan:** No TBDs or vague steps. All code blocks complete.

**Type consistency:** `SyncClient` defined in Task 3, used in Task 4 (`main.py`) and Task 8 (settings). `FlashcardsApp.sync` attribute set in Task 4 and accessed in Task 8. `app.db`, `app.rs`, `app.claude`, `app.sync` all consistent throughout.
