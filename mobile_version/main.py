import sys
import os

_app_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _app_dir)

# Only set a desktop preview window size — on Android Kivy uses the real screen
if not os.environ.get('ANDROID_ARGUMENT'):
    os.environ.setdefault('KIVY_WINDOW_WIDTH', '400')
    os.environ.setdefault('KIVY_WINDOW_HEIGHT', '760')

import data.database as db
import services.review_scheduler as review_scheduler
from sync_client import SyncClient
from ui.app import FlashcardsApp


def main():
    db.init_db()
    desktop_ip = db.get_setting('desktop_ip') or ''
    sync_client = SyncClient(base_url=desktop_ip or 'http://localhost:5000')

    FlashcardsApp(
        db=db,
        review_scheduler_mod=review_scheduler,
        sync_client=sync_client,
    ).run()


if __name__ == '__main__':
    main()
