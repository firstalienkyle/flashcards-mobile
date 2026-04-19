import sys
import faulthandler
import signal
faulthandler.enable()

def _log_signal(sig, frame):
    import traceback
    print(f"\n[main] killed by signal {sig}", flush=True)
    traceback.print_stack(frame)
    sys.exit(1)

for _s in (signal.SIGTERM, signal.SIGHUP, signal.SIGINT):
    signal.signal(_s, _log_signal)

import data.database as db
from PyQt5.QtWidgets import QApplication
from services.claude_service import ClaudeService
from services.scan_service import ScanService
from services.notification_service import NotificationService
import services.review_scheduler as review_scheduler
from ui.app import App


def main():
    qt_app = QApplication(sys.argv)

    db.init_db()

    api_key          = db.get_setting("claude_api_key")
    claude_service   = ClaudeService(api_key=api_key)
    scan_service     = ScanService()
    notification_svc = NotificationService(
        get_setting=db.get_setting,
        get_today_count=db.get_today_reviewed_count,
    )
    notification_svc.start()

    app = App(
        db=db,
        review_scheduler_mod=review_scheduler,
        claude_service=claude_service,
        scan_service=scan_service,
        notification_service=notification_svc,
    )
    app.show()

    sys.exit(qt_app.exec_())


if __name__ == "__main__":
    main()
