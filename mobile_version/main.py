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
