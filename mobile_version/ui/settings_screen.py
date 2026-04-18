import os
from pathlib import Path
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
import data.database as db
from ui.theme import (
    apply_bg, btn, lbl,
    SURFACE, SECONDARY, SUCCESS, DANGER, MUTED, TEXT,
    FONT_TITLE, FONT_BODY, FONT_SMALL,
    BTN_H, ROW_H, PAD, GAP,
)

SECTION_GAP = 44


class SettingsScreen(Screen):
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self._inputs = {}
        self._build()

    def _build(self):
        apply_bg(self)
        outer = BoxLayout(orientation='vertical', padding=0, spacing=0)

        # ── Fixed header ──────────────────────────────────────────────────────
        header = BoxLayout(size_hint_y=None, height=ROW_H,
                           padding=[PAD, 0], spacing=8)
        back = btn('Back', color=SECONDARY, height=ROW_H)
        back.size_hint_x = 0.28
        back.bind(on_press=lambda _: self.app.show_home())
        header.add_widget(back)
        header.add_widget(Widget(size_hint_x=None, width=20))
        header.add_widget(lbl('Settings', font_size=FONT_TITLE, bold=True,
                               height=ROW_H))
        outer.add_widget(header)

        # ── Scrollable body ───────────────────────────────────────────────────
        scroll = ScrollView(do_scroll_x=False)
        body = BoxLayout(orientation='vertical', padding=[PAD, PAD * 2],
                         spacing=SECTION_GAP, size_hint_y=None)
        body.bind(minimum_height=body.setter('height'))

        # General section label
        body.add_widget(lbl('General', font_size=FONT_BODY, color=MUTED,
                             bold=True, height=44))

        for label, key, hint in [
            ('Daily Goal', 'daily_goal', '20'),
            ('Notify at',  'notify_time', '18:00'),
        ]:
            item = BoxLayout(orientation='vertical', size_hint_y=None,
                             height=BTN_H + 50, spacing=10)
            item.add_widget(lbl(label, font_size=FONT_BODY, color=MUTED, height=40))
            inp = TextInput(
                hint_text=hint, multiline=False,
                size_hint_y=None, height=BTN_H,
                background_color=SURFACE, foreground_color=TEXT,
                font_size=FONT_BODY,
            )
            self._inputs[key] = inp
            item.add_widget(inp)
            body.add_widget(item)

        save_btn = btn('Save')
        save_btn.bind(on_press=self._save)
        body.add_widget(save_btn)

        self._save_status = lbl('', font_size=FONT_SMALL, color=SUCCESS,
                                 height=44, halign='center')
        body.add_widget(self._save_status)

        # Export section
        body.add_widget(lbl('Export', font_size=FONT_BODY, color=MUTED,
                             bold=True, height=44))
        body.add_widget(lbl(
            'Export all cards to a .txt file in the same format used for import.',
            font_size=FONT_SMALL, color=MUTED, height=60,
        ))

        export_btn = btn('Export TXT', color=SECONDARY)
        export_btn.bind(on_press=lambda _: self._export_txt())
        body.add_widget(export_btn)

        self._export_status = lbl('', font_size=FONT_SMALL, color=MUTED,
                                   height=60, halign='center')
        body.add_widget(self._export_status)

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
        self._save_status.text = 'Saved.'

    def _export_txt(self):
        decks = db.get_all_decks()
        lines = []
        for deck in decks:
            cards = db.get_cards_for_deck(deck.id)
            if not cards:
                continue
            lines.append(f'# {deck.name}')
            lines.append('')
            for card in cards:
                lines.append(card.front)
                lines.append('')
                lines.append(card.back)
                lines.append('')

        if not lines:
            self._export_status.color = DANGER
            self._export_status.text = 'No cards to export.'
            return

        android_private = os.environ.get('ANDROID_PRIVATE')
        if android_private:
            out_path = Path(android_private) / 'flashcards_export.txt'
        else:
            out_path = Path.home() / '.flashcards_mobile' / 'flashcards_export.txt'
        out_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            out_path.write_text('\n'.join(lines), encoding='utf-8')
            self._export_status.color = SUCCESS
            self._export_status.text = f'Saved to:\n{out_path}'
        except Exception as e:
            self._export_status.color = DANGER
            self._export_status.text = f'Export failed: {e}'
