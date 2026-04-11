import data.database as db
from data.models import Card
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.uix.checkbox import CheckBox
from kivy.metrics import dp
from ui._widgets import btn, lbl, top_bar, confirm_popup


class DeckScreen(Screen):
    def __init__(self, app, deck_id: int, **kwargs):
        super().__init__(**kwargs)
        self.app      = app
        self._deck_id = deck_id
        self._build()
        self._load()

    def _build(self):
        self._root = BoxLayout(orientation='vertical', padding=dp(12), spacing=dp(10))

        # Top bar with deck title
        self._title_lbl = lbl('', size=18, bold=True)
        bar = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(52), spacing=dp(8))
        bar.add_widget(btn('← Back', on_press=lambda _: self.app.show_home(),
                           size_hint_x=None, width=dp(90)))
        bar.add_widget(self._title_lbl)
        self._root.add_widget(bar)

        # Action row
        actions = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(48), spacing=dp(8))
        actions.add_widget(btn('+ Add', on_press=lambda _: self.app.show_create(deck_id=self._deck_id),
                               size_hint_x=None, width=dp(80)))
        actions.add_widget(btn('✎ Rename', on_press=self._rename_deck,
                               size_hint_x=None, width=dp(100)))
        actions.add_widget(btn('🗑 Delete Deck', on_press=self._confirm_delete_deck,
                               size_hint_x=None, width=dp(140)))
        actions.add_widget(BoxLayout())  # spacer
        self._root.add_widget(actions)

        # Search
        self._search = TextInput(
            hint_text='Search cards…',
            multiline=False,
            size_hint_y=None,
            height=dp(40),
        )
        self._search.bind(text=lambda _, __: self._load())
        self._root.add_widget(self._search)

        # Card list
        scroll = ScrollView()
        self._list = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(6))
        self._list.bind(minimum_height=self._list.setter('height'))
        scroll.add_widget(self._list)
        self._root.add_widget(scroll)

        self.add_widget(self._root)

    def _load(self):
        for d in db.get_all_decks():
            if d.id == self._deck_id:
                self._title_lbl.text = d.name
                break

        query   = self._search.text.lower()
        cards   = db.get_cards_for_deck(self._deck_id)
        filtered = [c for c in cards if query in c.front.lower() or query in c.back.lower()]

        self._list.clear_widgets()
        if not filtered:
            self._list.add_widget(lbl('No cards found.', halign='center'))
            return
        for card in filtered:
            self._list.add_widget(self._card_row(card))

    def _card_row(self, card: Card):
        row = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(64),
                        padding=(dp(8), dp(4)), spacing=dp(6))
        tag  = ' [Quiz]' if card.is_quiz else ''
        info = BoxLayout(orientation='vertical')
        info.add_widget(lbl(card.front + tag, bold=True, size=14))
        info.add_widget(lbl(card.back, size=12))
        row.add_widget(info)
        row.add_widget(btn('✎', on_press=lambda _, c=card: self._edit_card(c),
                           size_hint_x=None, width=dp(40)))
        row.add_widget(btn('✕', on_press=lambda _, c=card: self._confirm_delete_card(c),
                           size_hint_x=None, width=dp(40)))
        return row

    def _edit_card(self, card: Card):
        content = BoxLayout(orientation='vertical', spacing=dp(10), padding=dp(12))
        front_ti = TextInput(text=card.front, multiline=True,
                             size_hint_y=None, height=dp(70))
        back_ti  = TextInput(text=card.back, multiline=True,
                             size_hint_y=None, height=dp(70))

        quiz_row = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(36))
        quiz_row.add_widget(lbl('Quiz card:', size=14, size_hint_x=None, width=dp(90)))
        quiz_cb = CheckBox(active=card.is_quiz, size_hint_x=None, width=dp(40))
        quiz_row.add_widget(quiz_cb)
        quiz_row.add_widget(BoxLayout())

        content.add_widget(lbl('Front:', bold=True, size=14))
        content.add_widget(front_ti)
        content.add_widget(lbl('Back:', bold=True, size=14))
        content.add_widget(back_ti)
        content.add_widget(quiz_row)

        popup = Popup(title='Edit Card', content=content,
                      size_hint=(0.95, None), height=dp(400))

        def _save(_):
            front = front_ti.text.strip()
            back  = back_ti.text.strip()
            if not front or not back:
                return
            card.front   = front
            card.back    = back
            card.is_quiz = quiz_cb.active
            db.update_card(card)
            popup.dismiss()
            self._load()

        btn_row = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(48), spacing=dp(8))
        btn_row.add_widget(btn('Cancel', on_press=lambda _: popup.dismiss()))
        btn_row.add_widget(btn('Save', on_press=_save))
        content.add_widget(btn_row)
        popup.open()

    def _confirm_delete_card(self, card: Card):
        confirm_popup(
            'Delete Card',
            f"Delete '{card.front}'?",
            on_yes=lambda: (db.delete_card(card.id), self._load()),
        )

    def _rename_deck(self, _):
        from ui._widgets import input_popup
        input_popup('Rename Deck', 'New deck name',
                    on_ok=lambda name: (db.rename_deck(self._deck_id, name), self._load()))

    def _confirm_delete_deck(self, _):
        confirm_popup(
            'Delete Deck',
            'Delete this deck and all its cards? Cannot be undone.',
            on_yes=lambda: (db.delete_deck(self._deck_id), self.app.show_home()),
        )
