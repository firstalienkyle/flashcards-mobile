from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.uix.widget import Widget
from data.models import Card


class DeckScreen(Screen):
    def __init__(self, app, deck_id, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self._deck_id = deck_id
        self._build()

    def _build(self):
        root = BoxLayout(orientation='vertical', padding=16, spacing=10)

        top = BoxLayout(size_hint_y=None, height=48, spacing=8)
        back_btn = Button(text='← Back', size_hint_x=None, width=100)
        back_btn.bind(on_press=lambda _: self.app.show_home())
        top.add_widget(back_btn)
        self._title = Label(text='Deck', font_size='18sp', bold=True)
        top.add_widget(self._title)
        top.add_widget(Widget())
        add_btn = Button(text='+ Card', size_hint_x=None, width=90)
        add_btn.bind(on_press=lambda _: self.app.show_create(self._deck_id))
        top.add_widget(add_btn)
        root.add_widget(top)

        self._search = TextInput(hint_text='Search cards...', size_hint_y=None,
                                  height=40, multiline=False)
        self._search.bind(text=self._on_search)
        root.add_widget(self._search)

        scroll = ScrollView()
        self._card_list = GridLayout(cols=1, spacing=4, size_hint_y=None, padding=4)
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
            row = BoxLayout(size_hint_y=None, height=56, spacing=6)
            lbl = Label(
                text=f'{card.front[:40]}  →  {card.back[:40]}',
                halign='left', size_hint_x=1,
            )
            lbl.bind(size=lambda lb, sz: setattr(lb, 'text_size', sz))
            row.add_widget(lbl)
            edit_btn = Button(text='Edit', size_hint_x=None, width=70)
            edit_btn.bind(on_press=lambda _, c=card: self._edit_dialog(c))
            row.add_widget(edit_btn)
            del_btn = Button(text='Del', size_hint_x=None, width=60)
            del_btn.bind(on_press=lambda _, cid=card.id: self._delete_card(cid))
            row.add_widget(del_btn)
            self._card_list.add_widget(row)

    def _on_search(self, instance, value):
        self._load(filter_text=value)

    def _delete_card(self, card_id):
        self.app.db.delete_card(card_id)
        self._load(filter_text=self._search.text)

    def _edit_dialog(self, card):
        content = BoxLayout(orientation='vertical', padding=10, spacing=8)
        front_input = TextInput(text=card.front, multiline=True, size_hint_y=None, height=80)
        back_input = TextInput(text=card.back, multiline=True, size_hint_y=None, height=80)
        content.add_widget(Label(text='Front:', size_hint_y=None, height=28))
        content.add_widget(front_input)
        content.add_widget(Label(text='Back:', size_hint_y=None, height=28))
        content.add_widget(back_input)
        btn_row = BoxLayout(size_hint_y=None, height=44, spacing=8)

        popup = Popup(title='Edit Card', content=content, size_hint=(0.9, 0.7))

        def _save(_):
            card.front = front_input.text.strip()
            card.back = back_input.text.strip()
            if card.front and card.back:
                self.app.db.update_card(card)
                popup.dismiss()
                self._load(filter_text=self._search.text)

        save_btn = Button(text='Save')
        save_btn.bind(on_press=_save)
        cancel_btn = Button(text='Cancel')
        cancel_btn.bind(on_press=popup.dismiss)
        btn_row.add_widget(save_btn)
        btn_row.add_widget(cancel_btn)
        content.add_widget(btn_row)
        popup.open()
