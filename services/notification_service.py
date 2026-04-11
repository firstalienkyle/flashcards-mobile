import threading
import time
from datetime import datetime
from typing import Callable


class NotificationService:
    """Background service: fires a daily reminder notification. No tray icon on mobile."""

    def __init__(self, get_setting: Callable, get_today_count: Callable):
        self._get_setting    = get_setting
        self._get_today_count = get_today_count
        self._notified_today = ""

    def start(self) -> None:
        t = threading.Thread(target=self._check_loop, daemon=True)
        t.start()

    def stop(self) -> None:
        pass

    def _check_loop(self) -> None:
        while True:
            time.sleep(60)
            try:
                self._maybe_notify()
            except Exception:
                pass

    def _maybe_notify(self) -> None:
        notify_time = self._get_setting("notify_time")
        daily_goal  = int(self._get_setting("daily_goal") or 20)
        today       = datetime.now().date().isoformat()
        now_hhmm    = datetime.now().strftime("%H:%M")

        if now_hhmm == notify_time and today != self._notified_today:
            count = self._get_today_count()
            if count < daily_goal:
                try:
                    from plyer import notification
                    notification.notify(
                        title="Flashcard Review",
                        message=f"You've reviewed {count}/{daily_goal} cards today. Time to study!",
                        timeout=10,
                    )
                except Exception:
                    pass
                self._notified_today = today
