from kivy.app import App
from kivy.core.window import Window
from kivy.uix.screenmanager import ScreenManager


class PictureApp(App):
    title = 'Pictures'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.sm = None

    def build(self):
        Window.bind(on_keyboard=self._on_keyboard)
        self.sm = ScreenManager()
        self.show_home()
        return self.sm

    def _on_keyboard(self, window, key, *largs):
        if key == 27:  # Android back button
            if self.sm and self.sm.current != 'home':
                self.show_home()
                return True
        return False

    def _switch(self, screen):
        name = screen.name
        if self.sm.has_screen(name):
            self.sm.remove_widget(self.sm.get_screen(name))
        self.sm.add_widget(screen)
        self.sm.current = name

    def show_home(self):
        from ui.home_screen import HomeScreen
        self._switch(HomeScreen(self, name='home'))

    def show_settings(self):
        from ui.settings_screen import SettingsScreen
        self._switch(SettingsScreen(self, name='settings'))
