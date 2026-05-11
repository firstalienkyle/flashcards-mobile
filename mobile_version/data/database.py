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
                mastery_count INTEGER NOT NULL DEFAULT 0,
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
        try:
            conn.execute("ALTER TABLE cards ADD COLUMN mastery_count INTEGER NOT NULL DEFAULT 0")
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
        mastery_count=r["mastery_count"],
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
        # Increment mastery_count if reaching 100 (natural progression, not via buttons)
        mastery_increment = "mastery_count + 1" if memory_level >= 100.0 else "mastery_count"
        conn.execute(
            f"UPDATE cards SET memory_level=?, last_reviewed=?, review_count=review_count+1, "
            f"mastery_count = {mastery_increment} WHERE id=?",
            (memory_level, last_reviewed.isoformat(), card_id)
        )

def update_card_memory_from_button(card_id: int, memory_level: float) -> None:
    """Update memory WITHOUT affecting mastery_count (used by ✓/✗ buttons)."""
    with _conn() as conn:
        conn.execute(
            "UPDATE cards SET memory_level=? WHERE id=?",
            (memory_level, card_id)
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
