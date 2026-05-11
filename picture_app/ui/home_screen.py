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
    SECONDARY, MUTED, TEXT, SUCCESS, DANGER, PRIMARY,
    FONT_TITLE, FONT_BODY, FONT_SMALL,
    BTN_H, ROW_H, PAD, GAP,
)

_HARD_DELTA = -20.0
_OK_DELTA   = +10.0
_EASY_DELTA = +25.0


class HomeScreen(Screen):
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self._buttons = []
        self._current = None
        self._build()

    def _build(self):
        apply_bg(self)
        root = BoxLayout(orientation='vertical', padding=PAD, spacing=GAP)

        # ── Header ───────────────────────────────────────────────────────────
        header = BoxLayout(size_hint_y=None, height=ROW_H, spacing=8)
        header.add_widget(Widget())
        settings_btn = btn('Settings', color=SECONDARY, height=ROW_H)
        settings_btn.size_hint_x = None
        settings_btn.width = 200
        settings_btn.bind(on_press=lambda _: self.app.show_settings())
        header.add_widget(settings_btn)
        root.add_widget(header)

        # ── Caption + memory level ────────────────────────────────────────────
        self._caption = lbl('', font_size=FONT_TITLE, bold=True,
                             halign='center', size_hint_y=None, height=56)
        root.add_widget(self._caption)

        self._mem_label = lbl('', font_size=FONT_SMALL, color=MUTED,
                               halign='center', size_hint_y=None, height=36)
        root.add_widget(self._mem_label)

        # ── Picture ───────────────────────────────────────────────────────────
        self._image = Image(allow_stretch=True, keep_ratio=True)
        root.add_widget(self._image)

        # ── Memory rating row ─────────────────────────────────────────────────
        rating_row = BoxLayout(size_hint_y=None, height=BTN_H, spacing=GAP)
        hard_btn = btn('Hard', color=DANGER, height=BTN_H)
        hard_btn.bind(on_press=lambda _: self._rate(_HARD_DELTA))
        ok_btn = btn('OK', color=SECONDARY, height=BTN_H)
        ok_btn.bind(on_press=lambda _: self._rate(_OK_DELTA))
        easy_btn = btn('Easy', color=SUCCESS, height=BTN_H)
        easy_btn.bind(on_press=lambda _: self._rate(_EASY_DELTA))
        rating_row.add_widget(hard_btn)
        rating_row.add_widget(ok_btn)
        rating_row.add_widget(easy_btn)
        root.add_widget(rating_row)

        # ── Skip (random without rating) ─────────────────────────────────────
        skip_btn = btn('Skip', color=SECONDARY, height=BTN_H)
        skip_btn.bind(on_press=lambda _: self._show_random())
        root.add_widget(skip_btn)

        self.add_widget(root)

    def on_enter(self):
        self._buttons = db.get_all_buttons()
        self._show_random()

    def _show_random(self):
        self._buttons = db.get_all_buttons()
        if not self._buttons:
            self._caption.text = 'No pictures yet'
            self._mem_label.text = 'Go to Settings to add pictures'
            self._image.source = ''
            self._current = None
            return

        sorted_btns = sorted(self._buttons, key=lambda b: b.memory_level)
        min_lvl = sorted_btns[0].memory_level
        lowest = [b for b in sorted_btns if b.memory_level <= min_lvl + 0.5]
        others  = [b for b in sorted_btns if b.memory_level >  min_lvl + 0.5]
        self._current = (random.choice(lowest)
                         if (not others or random.random() < 0.75)
                         else random.choice(others))
        self._refresh_display()

    def _refresh_display(self):
        pb = self._current
        if pb is None:
            return
        self._caption.text = pb.label
        self._mem_label.text = f'Memory: {pb.memory_level:.0f}%  ·  Reviewed {pb.review_count}×'
        self._image.source = pb.path if Path(pb.path).exists() else ''

    def _rate(self, delta: float):
        if self._current is None:
            return
        new_level = max(0.0, min(100.0, self._current.memory_level + delta))
        db.update_picture_memory(self._current.id, new_level)
        self._show_random()
