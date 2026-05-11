from PyQt5.QtWidgets import QMainWindow


class App(QMainWindow):
    """
    Root window and screen router. All service references are stored here
    so every screen can access them via self.app.
    """

    def __init__(self, db, review_scheduler_mod, claude_service,
                 scan_service, notification_service):
        super().__init__()
        self.setWindowTitle("Flashcards")
        self.setFixedSize(960, 660)

        self.db     = db
        self.rs     = review_scheduler_mod
        self.claude = claude_service
        self.scan   = scan_service
        self.notif  = notification_service

        self.show_home()

    def _switch(self, screen) -> None:
        old = self.centralWidget()
        self.setCentralWidget(screen)
        if old is not None:
            old.deleteLater()

    def show_home(self) -> None:
        from computer_version.ui.home_screen import HomeScreen
        self._switch(HomeScreen(self))

    def show_review(self) -> None:
        from computer_version.ui.review_screen import ReviewScreen
        self._switch(ReviewScreen(self))

    def show_create(self, deck_id=None) -> None:
        from computer_version.ui.create_screen import CreateScreen
        self._switch(CreateScreen(self, deck_id=deck_id))

    def show_deck(self, deck_id: int) -> None:
        from computer_version.ui.deck_screen import DeckScreen
        self._switch(DeckScreen(self, deck_id=deck_id))

    def show_settings(self) -> None:
        from computer_version.ui.settings_screen import SettingsScreen
        self._switch(SettingsScreen(self))
