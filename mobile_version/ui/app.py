from kivy.app import App
from kivy.uix.screenmanager import ScreenManager


class FlashcardsApp(App):
    def __init__(self, db, review_scheduler_mod, claude_service, sync_client, **kwargs):
        super().__init__(**kwargs)
        self.db = db
        self.rs = review_scheduler_mod
        self.claude = claude_service
        self.sync = sync_client
        self.sm = ScreenManager()

    def build(self):
        self.show_home()
        return self.sm

    def _switch(self, screen):
        name = screen.name
        if self.sm.has_screen(name):
            self.sm.remove_widget(self.sm.get_screen(name))
        self.sm.add_widget(screen)
        self.sm.current = name

    def show_home(self):
        from ui.home_screen import HomeScreen
        self._switch(HomeScreen(self, name='home'))

    def show_deck(self, deck_id):
        from ui.deck_screen import DeckScreen
        self._switch(DeckScreen(self, deck_id=deck_id, name='deck'))

    def show_create(self, deck_id=None):
        from ui.create_screen import CreateScreen
        self._switch(CreateScreen(self, deck_id=deck_id, name='create'))

    def show_review(self):
        from ui.review_screen import ReviewScreen
        self._switch(ReviewScreen(self, name='review'))

    def show_settings(self):
        from ui.settings_screen import SettingsScreen
        self._switch(SettingsScreen(self, name='settings'))
