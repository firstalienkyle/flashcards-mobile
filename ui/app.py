import customtkinter as ctk
from config import BG_DARK, ACCENT

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class App(ctk.CTk):
    """
    Root window and screen router. All service references are stored here
    so every screen can access them via self.master (or self.app).
    """

    def __init__(self, db, review_scheduler_mod, claude_service, scan_service, notification_service):
        super().__init__()
        self.title("Flashcards")
        self.geometry("960x660")
        self.resizable(False, False)
        self.configure(fg_color=BG_DARK)

        # Service references — screens read these via self.app
        self.db = db
        self.rs = review_scheduler_mod   # the review_scheduler module (functions, not a class)
        self.claude = claude_service
        self.scan = scan_service
        self.notif = notification_service

        self._screen = None
        self.show_home()

    # ── Screen routing ─────────────────────────────────────────────────────────

    def _switch(self, screen: ctk.CTkFrame) -> None:
        if self._screen:
            self._screen.destroy()
        self._screen = screen
        screen.pack(fill="both", expand=True)

    def show_home(self) -> None:
        from ui.home_screen import HomeScreen
        self._switch(HomeScreen(self))

    def show_review(self) -> None:
        from ui.review_screen import ReviewScreen
        self._switch(ReviewScreen(self))

    def show_create(self, deck_id: int | None = None) -> None:
        from ui.create_screen import CreateScreen
        self._switch(CreateScreen(self, deck_id=deck_id))

    def show_deck(self, deck_id: int) -> None:
        from ui.deck_screen import DeckScreen
        self._switch(DeckScreen(self, deck_id=deck_id))

    def show_settings(self) -> None:
        from ui.settings_screen import SettingsScreen
        self._switch(SettingsScreen(self))
