from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.widget import Widget
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from data.models import Card
from ui.theme import (
    apply_bg, btn, lbl,
    SURFACE, SECONDARY, DANGER, MUTED, TEXT,
    FONT_BODY, FONT_TITLE,
    BTN_H, ROW_H, PAD, GAP,
)


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
        back.size_hint_x = 0.25
        back.bind(on_press=lambda _: self.app.show_home())
        header.add_widget(back)
        self._title = lbl('Deck', font_size=FONT_TITLE, bold=True, height=ROW_H)
        header.add_widget(self._title)
        header.add_widget(Widget())
        add = btn('+ Card', height=ROW_H)
        add.size_hint_x = 0.28
        add.bind(on_press=lambda _: self.app.show_create(self._deck_id))
        header.add_widget(add)
        root.add_widget(header)

        # ── Search ───────────────────────────────────────────────────────────
        self._search = TextInput(
            hint_text='Search cards...',
            size_hint_y=None, height=40,
            multiline=False,
            foreground_color=TEXT,
            background_color=SURFACE,
        )
        self._search.bind(text=self._on_search)
        root.add_widget(self._search)

        # ── Card list ─────────────────────────────────────────────────────────
        scroll = ScrollView()
        self._card_list = GridLayout(cols=1, spacing=6, size_hint_y=None, padding=0)
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
        for card in cards:
            row = BoxLayout(size_hint_y=None, height=58, spacing=6)

            card_btn = btn(
                f'{card.front[:50]}  ->  {card.back[:50]}',
                color=SURFACE, height=58,
            )
            card_btn.halign = 'left'
            card_btn.bind(size=lambda b, _: setattr(b, 'text_size', (b.width - 12, None)))
            row.add_widget(card_btn)

            edit = btn('Edit', color=SECONDARY, height=BTN_H)
            edit.size_hint_x = 0.2
            edit.bind(on_press=lambda _, c=card: self._edit_dialog(c))
            row.add_widget(edit)

            delete = btn('Del', color=DANGER, height=BTN_H)
            delete.size_hint_x = 0.18
            delete.bind(on_press=lambda _, cid=card.id: self._delete_card(cid))
            row.add_widget(delete)

            self._card_list.add_widget(row)

    def _on_search(self, instance, value):
        self._load(filter_text=value)

    def _delete_card(self, card_id):
        self.app.db.delete_card(card_id)
        self._load(filter_text=self._search.text)

    def _edit_dialog(self, card):
        content = BoxLayout(orientation='vertical', padding=12, spacing=8)
        front_input = TextInput(text=card.front, multiline=True,
                                size_hint_y=None, height=80)
        back_input = TextInput(text=card.back, multiline=True,
                               size_hint_y=None, height=80)
        content.add_widget(lbl('Front:', height=26))
        content.add_widget(front_input)
        content.add_widget(lbl('Back:', height=26))
        content.add_widget(back_input)

        popup = Popup(title='Edit Card', content=content, size_hint=(0.9, 0.65))

        def _save(_):
            card.front = front_input.text.strip()
            card.back = back_input.text.strip()
            if card.front and card.back:
                self.app.db.update_card(card)
                popup.dismiss()
                self._load(filter_text=self._search.text)

        btn_row = BoxLayout(size_hint_y=None, height=48, spacing=8)
        save = btn('Save')
        save.bind(on_press=_save)
        cancel = btn('Cancel', color=SECONDARY)
        cancel.bind(on_press=popup.dismiss)
        btn_row.add_widget(save)
        btn_row.add_widget(cancel)
        content.add_widget(btn_row)
        popup.open()
