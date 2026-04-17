import threading
from kivy.clock import Clock
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget
from kivy.uix.textinput import TextInput
from ui.theme import (
    apply_bg, btn, lbl,
    SURFACE, SECONDARY, MUTED, TEXT,
    FONT_TITLE, FONT_BODY, FONT_SMALL,
    BTN_H, ROW_H, PAD, GAP,
)


class SettingsScreen(Screen):
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self._inputs = {}
        self._build()

    def _build(self):
        apply_bg(self)
        outer = BoxLayout(orientation='vertical', padding=0, spacing=0)

        # ── Fixed header (stays visible while scrolling) ─────────────────────
        header = BoxLayout(size_hint_y=None, height=ROW_H,
                           padding=[PAD, 0], spacing=8)
        back = btn('Back', color=SECONDARY, height=ROW_H)
        back.size_hint_x = 0.28
        back.bind(on_press=lambda _: self.app.show_home())
        header.add_widget(back)
        header.add_widget(lbl('Settings', font_size=FONT_TITLE, bold=True,
                               height=ROW_H))
        header.add_widget(Widget())
        outer.add_widget(header)

        # ── Scrollable body ───────────────────────────────────────────────────
        scroll = ScrollView(do_scroll_x=False)
        body = BoxLayout(orientation='vertical', padding=PAD, spacing=GAP,
                         size_hint_y=None)
        body.bind(minimum_height=body.setter('height'))

        # General section
        body.add_widget(lbl('General', font_size=FONT_SMALL, color=MUTED,
                             bold=True, height=34))

        for label, key, hint in [
            ('Daily Goal', 'daily_goal', '20'),
            ('Notify at',  'notify_time', '18:00'),
        ]:
            body.add_widget(lbl(label, font_size=FONT_SMALL, color=MUTED, height=30))
            inp = TextInput(
                hint_text=hint, multiline=False,
                size_hint_y=None, height=BTN_H,
                background_color=SURFACE, foreground_color=TEXT,
                font_size=FONT_BODY,
            )
            self._inputs[key] = inp
            body.add_widget(inp)

        save_btn = btn('Save')
        save_btn.bind(on_press=self._save)
        body.add_widget(save_btn)

        # Sync section
        body.add_widget(lbl('Sync', font_size=FONT_SMALL, color=MUTED,
                             bold=True, height=34))
        body.add_widget(lbl(
            'Run sync_server.py on your Mac, enter its IP below.',
            font_size=FONT_SMALL, color=MUTED, height=44,
        ))

        body.add_widget(lbl('Desktop IP', font_size=FONT_SMALL, color=MUTED, height=30))
        inp = TextInput(
            hint_text='http://192.168.x.x:5000', multiline=False,
            size_hint_y=None, height=BTN_H,
            background_color=SURFACE, foreground_color=TEXT,
            font_size=FONT_BODY,
        )
        self._inputs['desktop_ip'] = inp
        body.add_widget(inp)

        sync_row = BoxLayout(size_hint_y=None, height=BTN_H, spacing=8)
        pull = btn('Pull from Desktop', color=SECONDARY)
        pull.bind(on_press=lambda _: self._sync('pull'))
        push = btn('Push to Desktop', color=SECONDARY)
        push.bind(on_press=lambda _: self._sync('push'))
        sync_row.add_widget(pull)
        sync_row.add_widget(push)
        body.add_widget(sync_row)

        self._status = lbl('', font_size=FONT_SMALL, color=MUTED, height=40)
        body.add_widget(self._status)

        scroll.add_widget(body)
        outer.add_widget(scroll)
        self.add_widget(outer)

    def on_enter(self):
        for key, inp in self._inputs.items():
            inp.text = self.app.db.get_setting(key) or ''

    def _save(self, _):
        for key, inp in self._inputs.items():
            val = inp.text.strip()
            if val:
                self.app.db.set_setting(key, val)
        ip = self.app.db.get_setting('desktop_ip') or ''
        if ip:
            self.app.sync.base_url = ip.rstrip('/')
        self._status.text = 'Saved.'

    def _sync(self, direction):
        ip = self._inputs['desktop_ip'].text.strip()
        if ip:
            self.app.db.set_setting('desktop_ip', ip)
            self.app.sync.base_url = ip.rstrip('/')

        if not self.app.sync.base_url or self.app.sync.base_url == 'http://localhost:5000':
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
