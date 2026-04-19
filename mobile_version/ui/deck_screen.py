import os
import threading

from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.widget import Widget
from kivy.uix.textinput import TextInput
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.graphics import Color, RoundedRectangle, Rectangle
from data.models import Card
from ui.theme import (
    apply_bg, btn, lbl,
    BG, SURFACE, SECONDARY, DANGER, MUTED, TEXT, PRIMARY,
    FONT_TITLE, FONT_BODY, FONT_SMALL,
    BTN_H, ROW_H, PAD, GAP, SPK_W, CJK_FONT,
)

LINE_H = 52   # matches review_screen

_VOICE_MAP = {'es': 'Monica', 'en': 'Samantha', 'zh': 'Ting-Ting'}

def _speak(text: str, lang: str = 'en'):
    word = text.strip().splitlines()[0] if text.strip() else ''
    if not word:
        return
    def _run():
        if os.environ.get('ANDROID_ARGUMENT'):
            try:
                from plyer import tts
                tts.speak(word)
            except Exception:
                pass
        else:
            import subprocess
            voice = _VOICE_MAP.get(lang, 'Samantha')
            try:
                subprocess.Popen(['say', '-v', voice, word])
            except Exception:
                pass
    threading.Thread(target=_run, daemon=True).start()


class DeckScreen(Screen):
    def __init__(self, app, deck_id, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self._deck_id = deck_id
        self._build()

    def _build(self):
        apply_bg(self)
        root = BoxLayout(orientation='vertical', padding=PAD, spacing=GAP)

        # ── Header ──────────────────────────────────────────────────────────
        header = BoxLayout(size_hint_y=None, height=ROW_H, spacing=8)
        back = btn('Back', color=SECONDARY, height=ROW_H)
        back.size_hint_x = 0.28
        back.bind(on_press=lambda _: self.app.show_home())
        header.add_widget(back)
        self._title = lbl('Deck', font_size=FONT_TITLE, bold=True, height=ROW_H)
        header.add_widget(self._title)
        add = btn('+ Card', height=ROW_H)
        add.size_hint_x = 0.28
        add.bind(on_press=lambda _: self.app.show_create(self._deck_id))
        header.add_widget(add)
        root.add_widget(header)

        # ── Search ───────────────────────────────────────────────────────────
        self._search = TextInput(
            hint_text='Search cards...',
            size_hint_y=None, height=BTN_H,
            multiline=False,
            foreground_color=TEXT,
            background_color=SURFACE,
            font_size=FONT_BODY,
        )
        self._search.bind(text=self._on_search)
        root.add_widget(self._search)

        # ── Card list ─────────────────────────────────────────────────────────
        scroll = ScrollView()
        self._card_list = GridLayout(cols=1, spacing=8, size_hint_y=None, padding=0)
        self._card_list.bind(minimum_height=self._card_list.setter('height'))
        scroll.add_widget(self._card_list)
        root.add_widget(scroll)

        self.add_widget(root)

    def on_enter(self):
        self._load()

    def _load(self, filter_text=''):
        decks = self.app.db.get_all_decks()
        deck = next((d for d in decks if d.id == self._deck_id), None)
        if deck:
            self._title.text = deck.name

        cards = self.app.db.get_cards_for_deck(self._deck_id)
        if filter_text:
            q = filter_text.lower()
            cards = [c for c in cards if q in c.front.lower() or q in c.back.lower()]

        self._card_list.clear_widgets()
        BTN_HALF = (BTN_H - 4) // 2  # two buttons + 4px spacing fit exactly in BTN_H
        for card in cards:
            row = BoxLayout(size_hint_y=None, height=BTN_H, spacing=6)

            # Left: wrapping front -> back text
            text_lbl = lbl(
                f'{card.front}  ->  {card.back}',
                font_size=FONT_SMALL, color=TEXT,
                halign='left',
            )
            # size_hint_y=None lets us control height; start at BTN_H
            text_lbl.size_hint_y = None
            text_lbl.height = BTN_H

            def _on_width(inst, width, r=row, l=text_lbl):
                l.text_size = (width, None)
                l.texture_update()
                new_h = max(int(l.texture_size[1]) + 24, BTN_H)
                if r.height != new_h:
                    r.height = new_h
                    l.height = new_h

            text_lbl.bind(width=_on_width)
            # Tap the text to preview the full card
            from kivy.uix.button import Button as _Btn
            preview_tap = _Btn(
                text='',
                size_hint=(1, 1),
                background_normal='',
                background_color=(0, 0, 0, 0),  # fully transparent overlay
            )
            preview_tap.bind(on_press=lambda _, c=card: self._preview_card(c))
            # Float the transparent tap target over the label
            from kivy.uix.floatlayout import FloatLayout
            text_fl = FloatLayout()
            text_lbl.size_hint = (1, 1)
            text_fl.add_widget(text_lbl)
            text_fl.add_widget(preview_tap)
            row.add_widget(text_fl)

            # Right: Edit + Del stacked, heights sum exactly to row height
            actions = BoxLayout(orientation='vertical',
                                size_hint_x=None, width=90, spacing=4)
            edit = btn('Edit', color=SECONDARY, height=BTN_HALF)
            edit.bind(on_press=lambda _, c=card: self._edit_dialog(c))
            delete = btn('Del', color=DANGER, height=BTN_HALF)
            delete.bind(on_press=lambda _, cid=card.id: self._delete_card(cid))
            actions.add_widget(edit)
            actions.add_widget(delete)
            row.add_widget(actions)

            self._card_list.add_widget(row)

    def _preview_card(self, card):
        """Full-screen modal that mirrors the review session layout exactly."""
        from kivy.uix.modalview import ModalView
        showing_front = [True]

        # ── ModalView: guaranteed full-screen, blocks background touches ──────
        mv = ModalView(size_hint=(1, 1), auto_dismiss=False,
                       background='', background_color=BG)

        root = BoxLayout(orientation='vertical', padding=PAD, spacing=GAP)

        # ── Side badge ────────────────────────────────────────────────────────
        side_lbl = lbl('FRONT', font_size=FONT_SMALL, color=MUTED,
                        height=32, halign='center')
        root.add_widget(side_lbl)

        # ── Card panel ────────────────────────────────────────────────────────
        ref = {}
        panel = BoxLayout(orientation='vertical', padding=16, spacing=8)
        with panel.canvas.before:
            ref['c'] = Color(*SURFACE)
            ref['r'] = RoundedRectangle(pos=panel.pos, size=panel.size, radius=[18])
        panel.bind(pos=lambda w, _: setattr(ref['r'], 'pos', w.pos))
        panel.bind(size=lambda w, _: setattr(ref['r'], 'size', w.size))

        card_scroll = ScrollView(do_scroll_x=False)
        card_content = BoxLayout(orientation='vertical', size_hint_y=None,
                                  spacing=6, padding=[0, 4])
        card_content.bind(minimum_height=card_content.setter('height'))
        card_scroll.add_widget(card_content)
        panel.add_widget(card_scroll)
        root.add_widget(panel)

        # ── Nav row: Flip | Close ─────────────────────────────────────────────
        nav = BoxLayout(size_hint_y=None, height=BTN_H, spacing=10)
        flip_btn = btn('Flip')
        close_btn = btn('Close', color=SECONDARY)
        nav.add_widget(flip_btn)
        nav.add_widget(close_btn)
        root.add_widget(nav)

        mv.add_widget(root)

        # ── Helper: build per-line rows ───────────────────────────────────────
        def _build_lines(text, lang):
            card_content.clear_widgets()
            for line in text.splitlines():
                if not line.strip():
                    continue
                row = BoxLayout(size_hint_y=None, height=LINE_H, spacing=6)
                line_lbl = Label(
                    text=line,
                    halign='left', valign='middle',
                    size_hint_x=1, size_hint_y=None, height=LINE_H,
                    font_size=FONT_BODY, font_name=CJK_FONT, color=TEXT,
                )
                line_lbl.bind(
                    width=lambda inst, w: setattr(inst, 'text_size', (max(0, w), None))
                )
                def _on_tex(inst, ts, r=row):
                    new_h = max(int(ts[1]) + 12, LINE_H)
                    inst.height = new_h
                    r.height = new_h
                line_lbl.bind(texture_size=_on_tex)

                spk = Button(
                    text='Spk', size_hint=(None, None),
                    width=SPK_W, height=LINE_H,
                    font_size=FONT_SMALL, background_normal='',
                    background_color=SECONDARY, color=TEXT,
                )
                row.bind(height=lambda _, h, b=spk: setattr(b, 'height', h))
                spk.bind(on_press=lambda _, t=line, l=lang: _speak(t, l))
                row.add_widget(line_lbl)
                row.add_widget(spk)
                card_content.add_widget(row)

        # ── Flip logic ────────────────────────────────────────────────────────
        def _flip(_):
            showing_front[0] = not showing_front[0]
            if showing_front[0]:
                side_lbl.text = 'FRONT'
                _build_lines(card.front, 'es')
            else:
                side_lbl.text = 'BACK'
                _build_lines(card.back, 'en')

        flip_btn.bind(on_press=_flip)
        close_btn.bind(on_press=lambda _: mv.dismiss())

        _build_lines(card.front, 'es')
        mv.open()

    def _on_search(self, instance, value):
        self._load(filter_text=value)

    def _delete_card(self, card_id):
        self.app.db.delete_card(card_id)
        self._load(filter_text=self._search.text)

    def _edit_dialog(self, card):
        content = BoxLayout(orientation='vertical', padding=12, spacing=8)
        front_input = TextInput(text=card.front, multiline=True,
                                size_hint_y=None, height=90,
                                font_size=FONT_BODY)
        back_input = TextInput(text=card.back, multiline=True,
                               size_hint_y=None, height=90,
                               font_size=FONT_BODY)
        content.add_widget(lbl('Front:', height=30))
        content.add_widget(front_input)
        content.add_widget(lbl('Back:', height=30))
        content.add_widget(back_input)

        popup = Popup(title='Edit Card', content=content, size_hint=(0.95, 0.75))

        def _save(_):
            card.front = front_input.text.strip()
            card.back = back_input.text.strip()
            if card.front and card.back:
                self.app.db.update_card(card)
                popup.dismiss()
                self._load(filter_text=self._search.text)

        btn_row = BoxLayout(size_hint_y=None, height=BTN_H, spacing=8)
        save = btn('Save')
        save.bind(on_press=_save)
        cancel = btn('Cancel', color=SECONDARY)
        cancel.bind(on_press=popup.dismiss)
        btn_row.add_widget(save)
        btn_row.add_widget(cancel)
        content.add_widget(btn_row)
        popup.open()
