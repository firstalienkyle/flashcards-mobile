from pathlib import Path

ACCENT    = '#7c83fd'
BG        = '#1a1a2e'
CARD_BG   = '#16213e'
TEXT      = '#e0e0e0'
MUTED     = '#888888'
GREEN     = '#3fb950'
RED       = '#f85149'

CLAUDE_MODEL = 'claude-sonnet-4-6'

try:
    from android.storage import app_storage_path
    DB_PATH = Path(app_storage_path()) / 'flashcards.db'
except ImportError:
    DB_PATH = Path.home() / '.flashcards_mobile' / 'flashcards.db'
