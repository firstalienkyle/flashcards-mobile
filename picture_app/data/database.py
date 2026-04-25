import sqlite3
from datetime import datetime
from pathlib import Path
from data.models import PictureButton
import config

_DB_PATH: Path = config.DB_PATH


def _conn() -> sqlite3.Connection:
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS picture_buttons (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                label         TEXT    NOT NULL,
                path          TEXT    NOT NULL,
                position      INTEGER NOT NULL DEFAULT 0,
                memory_level  REAL    NOT NULL DEFAULT 0.0,
                last_reviewed TEXT,
                review_count  INTEGER NOT NULL DEFAULT 0,
                created_at    TEXT    NOT NULL
            );
        """)
        for col, defn in [
            ('memory_level',  'REAL NOT NULL DEFAULT 0.0'),
            ('last_reviewed', 'TEXT'),
            ('review_count',  'INTEGER NOT NULL DEFAULT 0'),
        ]:
            try:
                conn.execute(f'ALTER TABLE picture_buttons ADD COLUMN {col} {defn}')
            except Exception:
                pass


def _row_to_button(r: sqlite3.Row) -> PictureButton:
    return PictureButton(
        id=r['id'],
        label=r['label'],
        path=r['path'],
        position=r['position'],
        memory_level=r['memory_level'],
        last_reviewed=datetime.fromisoformat(r['last_reviewed']) if r['last_reviewed'] else None,
        review_count=r['review_count'],
        created_at=datetime.fromisoformat(r['created_at']),
    )


def get_all_buttons() -> list[PictureButton]:
    with _conn() as conn:
        rows = conn.execute(
            'SELECT * FROM picture_buttons ORDER BY position, created_at'
        ).fetchall()
        return [_row_to_button(r) for r in rows]


def create_button(label: str, src_path: str) -> PictureButton:
    """Store the original image path — the file is never copied."""
    now = datetime.now().isoformat()
    with _conn() as conn:
        cur = conn.execute(
            'INSERT INTO picture_buttons (label, path, position, created_at) VALUES (?, ?, ?, ?)',
            (label, src_path, 0, now),
        )
        return PictureButton(id=cur.lastrowid, label=label, path=src_path,
                             created_at=datetime.fromisoformat(now))


def update_label(button_id: int, label: str) -> None:
    with _conn() as conn:
        conn.execute('UPDATE picture_buttons SET label=? WHERE id=?', (label, button_id))


def update_picture_memory(button_id: int, memory_level: float) -> None:
    with _conn() as conn:
        conn.execute(
            'UPDATE picture_buttons SET memory_level=?, last_reviewed=?, '
            'review_count=review_count+1 WHERE id=?',
            (memory_level, datetime.now().isoformat(), button_id),
        )


def delete_button(button_id: int) -> None:
    with _conn() as conn:
        conn.execute('DELETE FROM picture_buttons WHERE id=?', (button_id,))
