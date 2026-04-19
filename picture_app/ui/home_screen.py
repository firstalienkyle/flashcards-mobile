import random
from pathlib import Path

from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.widget import Widget
from kivy.uix.image import Image
from kivy.uix.label import Label

import data.database as db
from ui.theme import (
    apply_bg, btn, lbl,
    SECONDARY, MUTED, TEXT,
    FONT_TITLE, FONT_BODY, FONT_SMALL,
    BTN_H, ROW_H, PAD, GAP,
)


class HomeScreen(Screen):
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self._buttons = []
        self._build()

    def _build(self):
        apply_bg(self)
        root = BoxLayout(orientation='vertical', padding=PAD, spacing=GAP)

        # ── Header: title + Settings top-right ──────────────────────────────
        header = BoxLayout(size_hint_y=None, height=ROW_H, spacing=8)
        header.add_widget(Widget())  # spacer so Settings hugs the right
        settings_btn = btn('Settings', color=SECONDARY, height=ROW_H)
        settings_btn.size_hint_x = None
        settings_btn.width = 200
        settings_btn.bind(on_press=lambda _: self.app.show_settings())
        header.add_widget(settings_btn)
        root.add_widget(header)

        # ── Picture label ────────────────────────────────────────────────────
        self._caption = lbl('', font_size=FONT_TITLE, bold=True,
                             halign='center', size_hint_y=None, height=56)
        root.add_widget(self._caption)

        # ── Picture (fills remaining space) ─────────────────────────────────
        self._image = Image(allow_stretch=True, keep_ratio=True)
        root.add_widget(self._image)

        # ── Random button ────────────────────────────────────────────────────
        random_btn = btn('Random', height=BTN_H)
        random_btn.bind(on_press=lambda _: self._show_random())
        root.add_widget(random_btn)

        self.add_widget(root)

    def on_enter(self):
        self._buttons = db.get_all_buttons()
        self._show_random()

    def _show_random(self):
        self._buttons = db.get_all_buttons()
        if not self._buttons:
            self._caption.text = 'No pictures yet'
            self._image.source = ''
            return
        pb = random.choice(self._buttons)
        self._caption.text = pb.label
        self._image.source = pb.path if Path(pb.path).exists() else ''
