import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

# Set phone-sized window before Kivy initialises
os.environ.setdefault('KIVY_WINDOW_WIDTH', '400')
os.environ.setdefault('KIVY_WINDOW_HEIGHT', '760')

import data.database as db
from services.claude_service import ClaudeService
import services.review_scheduler as review_scheduler
from sync_client import SyncClient
from ui.app import FlashcardsApp


def main():
    db.init_db()

    # API key: env var takes priority (desktop), then stored setting (mobile/Android)
    api_key = os.environ.get('ANTHROPIC_API_KEY') or db.get_setting('claude_api_key') or ''
    claude_service = ClaudeService(api_key=api_key)

    desktop_ip = db.get_setting('desktop_ip') or ''
    sync_client = SyncClient(base_url=desktop_ip or 'http://localhost:5000')

    FlashcardsApp(
        db=db,
        review_scheduler_mod=review_scheduler,
        claude_service=claude_service,
        sync_client=sync_client,
    ).run()


if __name__ == '__main__':
    main()
