import threading
import time
from datetime import datetime
from typing import Callable
from plyer import notification
import pystray
from PIL import Image, ImageDraw

class NotificationService:
    """
    Background service that:
    1. Checks every 60s whether to fire a daily review reminder.
    2. Runs a system tray icon so the app can persist after the window is hidden.
    """

    def __init__(
        self,
        get_setting: Callable[[str], str],
        get_today_count: Callable[[], int],
    ):
        self._get_setting = get_setting
        self._get_today_count = get_today_count
        self._tray: pystray.Icon | None = None
        self._notified_today: str = ""   # date string — prevents duplicate notifications

    def start(self) -> None:
        """Start background threads. Call once at app launch."""
        t = threading.Thread(target=self._check_loop, daemon=True)
        t.start()
        self._start_tray()

    def stop(self) -> None:
        if self._tray:
            self._tray.stop()

    # ── Private ───────────────────────────────────────────────────────────────

    def _check_loop(self) -> None:
        while True:
            time.sleep(60)
            try:
                self._maybe_notify()
            except Exception:
                pass  # Never crash the background thread

    def _maybe_notify(self) -> None:
        notify_time = self._get_setting("notify_time")
        daily_goal  = int(self._get_setting("daily_goal"))
        today       = datetime.now().date().isoformat()
        now_hhmm    = datetime.now().strftime("%H:%M")

        if now_hhmm == notify_time and today != self._notified_today:
            count = self._get_today_count()
            if count < daily_goal:
                notification.notify(
                    title="Flashcard Review",
                    message=f"You've reviewed {count}/{daily_goal} cards today. Time to study!",
                    app_name="Flashcards",
                    timeout=10,
                )
                self._notified_today = today

    def _start_tray(self) -> None:
        img = Image.new("RGB", (64, 64), color="#7c83fd")
        draw = ImageDraw.Draw(img)
        draw.rectangle([16, 20, 48, 44], fill="white")

        def on_quit(icon, _item):
            icon.stop()

        menu = pystray.Menu(pystray.MenuItem("Quit", on_quit))
        self._tray = pystray.Icon("flashcards", img, "Flashcards", menu)
        t = threading.Thread(target=self._tray.run, daemon=True)
        t.start()
