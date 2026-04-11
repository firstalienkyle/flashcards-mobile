from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, SlideTransition
import data.database as db
import services.review_scheduler as review_scheduler


class FlashcardsApp(App):
    def __init__(self, claude_service, notification_service, **kwargs):
        super().__init__(**kwargs)
        self.db     = db
        self.rs     = review_scheduler
        self.claude = claude_service
        self.notif  = notification_service

    def build(self):
        self.sm = ScreenManager(transition=SlideTransition())
        self.show_home()
        return self.sm

    # ── Navigation ────────────────────────────────────────────────────────────

    def _switch(self, screen):
        self.sm.clear_widgets()
        self.sm.add_widget(screen)

    def show_home(self):
        from ui.home_screen import HomeScreen
        self._switch(HomeScreen(app=self, name='home'))

    def show_review(self):
        from ui.review_screen import ReviewScreen
        self._switch(ReviewScreen(app=self, name='review'))

    def show_create(self, deck_id=None):
        from ui.create_screen import CreateScreen
        self._switch(CreateScreen(app=self, deck_id=deck_id, name='create'))

    def show_deck(self, deck_id: int):
        from ui.deck_screen import DeckScreen
        self._switch(DeckScreen(app=self, deck_id=deck_id, name='deck'))

    def show_settings(self):
        from ui.settings_screen import SettingsScreen
        self._switch(SettingsScreen(app=self, name='settings'))
