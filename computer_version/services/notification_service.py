import threading
import time
from datetime import datetime
from typing import Callable
from plyer import notification
from PyQt5.QtWidgets import QSystemTrayIcon, QMenu, QAction, QApplication
from PyQt5.QtGui import QIcon, QPixmap, QColor


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
        self._tray: QSystemTrayIcon | None = None
        self._notified_today: str = ""   # date string — prevents duplicate notifications

    def start(self) -> None:
        """Start background threads. Call once at app launch."""
        t = threading.Thread(target=self._check_loop, daemon=True)
        t.start()
        self._start_tray()

    def stop(self) -> None:
        if self._tray:
            self._tray.hide()

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
        pixmap = QPixmap(64, 64)
        pixmap.fill(QColor("#7c83fd"))
        icon = QIcon(pixmap)

        self._tray = QSystemTrayIcon(icon)
        self._tray.setToolTip("Flashcards")

        menu = QMenu()
        quit_action = QAction("Quit")
        quit_action.triggered.connect(QApplication.quit)
        menu.addAction(quit_action)
        self._tray.setContextMenu(menu)

        self._tray.show()
