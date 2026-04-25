import os
from pathlib import Path

_android_private = os.environ.get('ANDROID_PRIVATE')
if _android_private:
    DB_PATH = Path(_android_private) / 'picture_app.db'
else:
    DB_PATH = Path.home() / '.picture_app' / 'picture_app.db'
