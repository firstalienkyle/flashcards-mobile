from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget
from kivy.uix.popup import Popup
import threading


class SettingsScreen(Screen):
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self._build()

    def _build(self):
        root = BoxLayout(orientation='vertical', padding=16, spacing=12)

        top = BoxLayout(size_hint_y=None, height=48, spacing=8)
        back_btn = Button(text='← Back', size_hint_x=None, width=100)
        back_btn.bind(on_press=lambda _: self.app.show_home())
        top.add_widget(back_btn)
        top.add_widget(Label(text='Settings', font_size='18sp', bold=True))
        top.add_widget(Widget())
        root.add_widget(top)

        fields = [
            ('Desktop IP', 'desktop_ip', 'http://192.168.1.x:5000', False),
            ('Daily goal', 'daily_goal', '20', False),
            ('Claude API key', 'claude_api_key', 'sk-ant-...', True),
            ('Decay rate', 'decay_rate', '5', False),
        ]
        self._inputs = {}
        for label, key, hint, password in fields:
            row = BoxLayout(size_hint_y=None, height=44, spacing=8)
            row.add_widget(Label(text=label + ':', size_hint_x=None, width=140))
            inp = TextInput(hint_text=hint, multiline=False,
                            password=password, size_hint_x=1)
            self._inputs[key] = inp
            row.add_widget(inp)
            root.add_widget(row)

        save_btn = Button(text='Save Settings', size_hint_y=None, height=48)
        save_btn.bind(on_press=self._save)
        root.add_widget(save_btn)

        root.add_widget(Label(text='Sync', font_size='16sp', bold=True,
                               size_hint_y=None, height=32))
        sync_row = BoxLayout(size_hint_y=None, height=48, spacing=8)
        pull_btn = Button(text='⬇ Pull from Desktop')
        pull_btn.bind(on_press=lambda _: self._sync('pull'))
        push_btn = Button(text='⬆ Push to Desktop')
        push_btn.bind(on_press=lambda _: self._sync('push'))
        sync_row.add_widget(pull_btn)
        sync_row.add_widget(push_btn)
        root.add_widget(sync_row)

        self._status_label = Label(text='', size_hint_y=None, height=32,
                                    color=(0.5, 0.5, 0.5, 1))
        root.add_widget(self._status_label)
        root.add_widget(Widget())

        self.add_widget(root)

    def on_enter(self):
        for key, inp in self._inputs.items():
            inp.text = self.app.db.get_setting(key) or ''

    def _save(self, _):
        for key, inp in self._inputs.items():
            val = inp.text.strip()
            if val:
                self.app.db.set_setting(key, val)
        # Update sync client URL
        ip = self.app.db.get_setting('desktop_ip') or 'http://localhost:5000'
        self.app.sync.base_url = ip.rstrip('/')
        self._status_label.text = 'Settings saved.'

    def _sync(self, direction):
        self._status_label.text = f'{"Pulling" if direction == "pull" else "Pushing"}...'
        def _run():
            try:
                if direction == 'pull':
                    self.app.sync.pull()
                    msg = 'Pull complete.'
                else:
                    self.app.sync.push()
                    msg = 'Push complete.'
            except Exception as e:
                msg = f'Error: {e}'
            from kivy.clock import Clock
            Clock.schedule_once(lambda dt: setattr(self._status_label, 'text', msg))
        threading.Thread(target=_run, daemon=True).start()
