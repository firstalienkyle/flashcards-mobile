import threading
from kivy.clock import Clock
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.widget import Widget
from kivy.uix.textinput import TextInput
from ui.theme import (
    apply_bg, btn, lbl,
    SURFACE, SECONDARY, MUTED, TEXT,
    FONT_TITLE, FONT_BODY, FONT_SMALL,
    BTN_H, ROW_H, PAD, GAP,
)


def _field_row(label, key, hint, password=False):
    """Build a label + TextInput row. Returns (row_widget, input_widget)."""
    row = BoxLayout(size_hint_y=None, height=44, spacing=10)
    row.add_widget(lbl(label + ':', height=44,
                        size_hint_x=None, width=148, color=MUTED))
    inp = TextInput(
        hint_text=hint,
        multiline=False,
        password=password,
        size_hint_x=1,
        size_hint_y=None,
        height=44,
        background_color=SURFACE,
        foreground_color=TEXT,
    )
    row.add_widget(inp)
    return row, inp


class SettingsScreen(Screen):
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self._inputs = {}
        self._build()

    def _build(self):
        apply_bg(self)
        root = BoxLayout(orientation='vertical', padding=PAD, spacing=GAP)

        # ── Header ──────────────────────────────────────────────────────────
        header = BoxLayout(size_hint_y=None, height=ROW_H, spacing=8)
        back = btn('Back', color=SECONDARY, height=ROW_H)
        back.size_hint_x = 0.25
        back.bind(on_press=lambda _: self.app.show_home())
        header.add_widget(back)
        header.add_widget(lbl('Settings', font_size=FONT_TITLE, bold=True,
                               height=ROW_H))
        header.add_widget(Widget())
        root.add_widget(header)

        # ── General (matches desktop) ────────────────────────────────────────
        root.add_widget(lbl('General', font_size=FONT_SMALL, color=MUTED,
                             bold=True, height=30))

        row, inp = _field_row('Daily Goal', 'daily_goal', '20')
        self._inputs['daily_goal'] = inp
        root.add_widget(row)

        row, inp = _field_row('Notify at', 'notify_time', '18:00')
        self._inputs['notify_time'] = inp
        root.add_widget(row)

        save_general = btn('Save')
        save_general.bind(on_press=self._save)
        root.add_widget(save_general)

        # ── Sync ─────────────────────────────────────────────────────────────
        root.add_widget(lbl('Sync', font_size=FONT_SMALL, color=MUTED,
                             bold=True, height=34))
        root.add_widget(lbl(
            'Run sync_server.py on your Mac, then enter its local IP.',
            font_size=FONT_SMALL, color=MUTED, height=28,
        ))

        row, inp = _field_row('Desktop IP', 'desktop_ip', 'http://192.168.x.x:5000')
        self._inputs['desktop_ip'] = inp
        root.add_widget(row)

        sync_row = BoxLayout(size_hint_y=None, height=BTN_H, spacing=8)
        pull = btn('Pull from Desktop', color=SECONDARY)
        pull.bind(on_press=lambda _: self._sync('pull'))
        push = btn('Push to Desktop', color=SECONDARY)
        push.bind(on_press=lambda _: self._sync('push'))
        sync_row.add_widget(pull)
        sync_row.add_widget(push)
        root.add_widget(sync_row)

        # ── Claude setup ─────────────────────────────────────────────────────
        root.add_widget(lbl('Claude AI  (one-time setup)', font_size=FONT_SMALL,
                             color=MUTED, bold=True, height=34))

        row, inp = _field_row('API Key', 'claude_api_key', 'sk-ant-...', password=True)
        self._inputs['claude_api_key'] = inp
        root.add_widget(row)

        save_key = btn('Save API Key', color=SECONDARY)
        save_key.bind(on_press=self._save)
        root.add_widget(save_key)

        self._status = lbl('', font_size=FONT_SMALL, color=MUTED, height=30)
        root.add_widget(self._status)
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
        # Keep sync client URL in sync
        ip = self.app.db.get_setting('desktop_ip') or ''
        if ip:
            self.app.sync.base_url = ip.rstrip('/')
        # Keep claude service api key in sync
        api_key = self.app.db.get_setting('claude_api_key') or ''
        if api_key:
            import anthropic
            self.app.claude.client = anthropic.Anthropic(api_key=api_key)
        self._status.text = 'Saved.'

    def _sync(self, direction):
        # Save the IP field first so the sync client uses the latest value
        ip = self._inputs['desktop_ip'].text.strip()
        if ip:
            self.app.db.set_setting('desktop_ip', ip)
            self.app.sync.base_url = ip.rstrip('/')

        if not self.app.sync.base_url or self.app.sync.base_url in ('http://localhost:5000', ''):
            self._status.text = 'Set Desktop IP first.'
            return

        self._status.text = 'Pulling...' if direction == 'pull' else 'Pushing...'

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
            Clock.schedule_once(lambda dt: setattr(self._status, 'text', msg))

        threading.Thread(target=_run, daemon=True).start()
