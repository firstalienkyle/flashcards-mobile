import os
from pathlib import Path

# On Android (python-for-android), ANDROID_PRIVATE is set to the app's
# internal private storage directory (/data/data/<package>/files).
# Path.home() is unreliable on Android if HOME env var isn't set.
_android_private = os.environ.get('ANDROID_PRIVATE')
if _android_private:
    DB_PATH = Path(_android_private) / 'flashcards.db'
else:
    DB_PATH = Path.home() / '.flashcards_mobile' / 'flashcards.db'

CLAUDE_MODEL = 'claude-sonnet-4-6'
