import sqlite3
import shutil
from datetime import datetime
from pathlib import Path
from data.models import PictureButton
import config

_DB_PATH: Path = config.DB_PATH
_IMAGES_DIR: Path = config.IMAGES_DIR


def _conn() -> sqlite3.Connection:
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    _IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    with _conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS picture_buttons (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                label      TEXT    NOT NULL,
                path       TEXT    NOT NULL,
                position   INTEGER NOT NULL DEFAULT 0,
                created_at TEXT    NOT NULL
            );
        """)


def _row_to_button(r: sqlite3.Row) -> PictureButton:
    return PictureButton(
        id=r['id'],
        label=r['label'],
        path=r['path'],
        position=r['position'],
        created_at=datetime.fromisoformat(r['created_at']),
    )


def get_all_buttons() -> list[PictureButton]:
    with _conn() as conn:
        rows = conn.execute(
            'SELECT * FROM picture_buttons ORDER BY position, created_at'
        ).fetchall()
        return [_row_to_button(r) for r in rows]


def create_button(label: str, src_path: str) -> PictureButton:
    """Copy the image into the app images dir and store a record."""
    _IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    src = Path(src_path)
    dest = _IMAGES_DIR / f'{datetime.now().strftime("%Y%m%d_%H%M%S_%f")}{src.suffix}'
    shutil.copy2(src, dest)
    now = datetime.now().isoformat()
    with _conn() as conn:
        cur = conn.execute(
            'INSERT INTO picture_buttons (label, path, position, created_at) VALUES (?, ?, ?, ?)',
            (label, str(dest), 0, now),
        )
        return PictureButton(id=cur.lastrowid, label=label, path=str(dest),
                             created_at=datetime.fromisoformat(now))


def update_label(button_id: int, label: str) -> None:
    with _conn() as conn:
        conn.execute('UPDATE picture_buttons SET label=? WHERE id=?', (label, button_id))


def delete_button(button_id: int) -> None:
    with _conn() as conn:
        row = conn.execute('SELECT path FROM picture_buttons WHERE id=?',
                           (button_id,)).fetchone()
        if row:
            try:
                Path(row['path']).unlink(missing_ok=True)
            except Exception:
                pass
        conn.execute('DELETE FROM picture_buttons WHERE id=?', (button_id,))
