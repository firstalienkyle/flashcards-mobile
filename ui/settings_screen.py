import data.database as db
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.metrics import dp
from ui._widgets import btn, lbl, top_bar


class SettingsScreen(Screen):
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self._build()
        self._load()

    def _build(self):
        root = BoxLayout(orientation='vertical', padding=dp(16), spacing=dp(16))
        root.add_widget(top_bar('Settings', on_back=lambda _: self.app.show_home()))

        form = BoxLayout(orientation='vertical', spacing=dp(14), size_hint_y=None)
        form.bind(minimum_height=form.setter('height'))

        # Daily goal
        root.add_widget(lbl('Daily goal (cards):', size=15))
        self._goal_ti = TextInput(
            hint_text='e.g. 20',
            multiline=False,
            input_filter='int',
            size_hint_y=None,
            height=dp(44),
        )
        root.add_widget(self._goal_ti)

        # Notify time
        root.add_widget(lbl('Notify at (HH:MM):', size=15))
        self._notify_ti = TextInput(
            hint_text='e.g. 18:00',
            multiline=False,
            size_hint_y=None,
            height=dp(44),
        )
        root.add_widget(self._notify_ti)

        root.add_widget(btn('Save Settings', on_press=self._save))
        root.add_widget(BoxLayout())  # spacer

        self.add_widget(root)

    def _load(self):
        settings = db.get_all_settings()
        self._goal_ti.text   = settings.get('daily_goal', '20')
        self._notify_ti.text = settings.get('notify_time', '18:00')

    def _save(self, _):
        goal = self._goal_ti.text.strip()
        if goal and not goal.isdigit():
            _alert('Validation', 'Daily goal must be a whole number.')
            return
        db.set_setting('daily_goal', goal)
        db.set_setting('notify_time', self._notify_ti.text.strip())
        _alert('Saved', 'Settings saved.', on_dismiss=lambda _: self.app.show_home())


def _alert(title, message, on_dismiss=None):
    from kivy.uix.label import Label
    content = BoxLayout(orientation='vertical', padding=dp(12), spacing=dp(8))
    content.add_widget(Label(text=message, halign='center'))
    popup = Popup(title=title, content=content,
                  size_hint=(0.8, None), height=dp(160))
    ok_btn = btn('OK', on_press=lambda _: popup.dismiss())
    content.add_widget(ok_btn)
    if on_dismiss:
        popup.bind(on_dismiss=on_dismiss)
    popup.open()
