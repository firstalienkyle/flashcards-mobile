import data.database as db
from services.claude_service import ClaudeService
from services.notification_service import NotificationService
from ui.app import FlashcardsApp


def main():
    db.init_db()
    api_key = db.get_setting("claude_api_key") or ""
    claude = ClaudeService(api_key=api_key)
    notif = NotificationService(
        get_setting=db.get_setting,
        get_today_count=db.get_today_reviewed_count,
    )
    notif.start()
    app = FlashcardsApp(claude_service=claude, notification_service=notif)
    app.run()


if __name__ == "__main__":
    main()
