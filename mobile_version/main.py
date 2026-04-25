import sys
import os

_app_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _app_dir)

# Set phone-sized preview window on desktop — must happen before any kivy import
if not os.environ.get('ANDROID_ARGUMENT'):
    from kivy.config import Config
    Config.set('graphics', 'width',  '393')   # Samsung Galaxy A34 aspect ratio
    Config.set('graphics', 'height', '876')   # 1080x2408 scaled down
    Config.set('graphics', 'resizable', '0')

import data.database as db
import services.review_scheduler as review_scheduler
from sync_client import SyncClient
from ui.app import FlashcardsApp


def main():
    import traceback

    android_private = os.environ.get('ANDROID_PRIVATE')
    log_path = os.path.join(android_private, 'crash.log') if android_private else None

    def _log(msg):
        if log_path:
            try:
                with open(log_path, 'a') as f:
                    f.write(msg + '\n')
            except Exception:
                pass

    try:
        _log('--- app start ---')
        db.init_db()
        _log('db init ok')
        desktop_ip = db.get_setting('desktop_ip') or ''
        sync_client = SyncClient(base_url=desktop_ip or 'http://localhost:5000')
        _log('sync client ok')

        FlashcardsApp(
            db=db,
            review_scheduler_mod=review_scheduler,
            sync_client=sync_client,
        ).run()
    except Exception:
        err = traceback.format_exc()
        _log(err)
        raise


if __name__ == '__main__':
    main()
