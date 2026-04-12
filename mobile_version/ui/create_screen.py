from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from kivy.uix.scrollview import ScrollView
from kivy.uix.popup import Popup
from kivy.uix.widget import Widget
from data.models import Card


class CreateScreen(Screen):
    def __init__(self, app, deck_id=None, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self._deck_id = deck_id
        self._deck_map = {}
        self._gen_rows = []
        self._build()

    def _build(self):
        root = BoxLayout(orientation='vertical', padding=16, spacing=10)

        top = BoxLayout(size_hint_y=None, height=48, spacing=8)
        back_btn = Button(text='← Back', size_hint_x=None, width=100)
        back_btn.bind(on_press=lambda _: self.app.show_home())
        top.add_widget(back_btn)
        top.add_widget(Label(text='New Card', font_size='18sp', bold=True))
        top.add_widget(Widget())
        root.add_widget(top)

        # Deck selector
        deck_row = BoxLayout(size_hint_y=None, height=44, spacing=8)
        deck_row.add_widget(Label(text='Deck:', size_hint_x=None, width=60))
        self._deck_spinner = Spinner(text='Select deck', values=[], size_hint_x=1)
        deck_row.add_widget(self._deck_spinner)
        new_deck_btn = Button(text='+ New', size_hint_x=None, width=80)
        new_deck_btn.bind(on_press=self._new_deck_dialog)
        deck_row.add_widget(new_deck_btn)
        root.add_widget(deck_row)

        # Front / Back inputs
        root.add_widget(Label(text='Front:', size_hint_y=None, height=28, halign='left'))
        self._front_input = TextInput(multiline=True, size_hint_y=None, height=80)
        root.add_widget(self._front_input)
        root.add_widget(Label(text='Back:', size_hint_y=None, height=28, halign='left'))
        self._back_input = TextInput(multiline=True, size_hint_y=None, height=80)
        root.add_widget(self._back_input)

        # Buttons
        btn_row = BoxLayout(size_hint_y=None, height=48, spacing=8)
        save_btn = Button(text='Save Card', size_hint_x=None, width=130)
        save_btn.bind(on_press=self._save_card)
        btn_row.add_widget(save_btn)
        txt_btn = Button(text='📄 Import TXT', size_hint_x=None, width=150)
        txt_btn.bind(on_press=self._import_txt_dialog)
        btn_row.add_widget(txt_btn)
        btn_row.add_widget(Widget())
        root.add_widget(btn_row)

        # Generated cards area
        self._gen_label = Label(text='Imported cards — review before saving',
                                size_hint_y=None, height=28, bold=True)
        self._gen_label.opacity = 0
        root.add_widget(self._gen_label)

        scroll = ScrollView()
        self._gen_layout = GridLayout(cols=1, spacing=4, size_hint_y=None, padding=4)
        self._gen_layout.bind(minimum_height=self._gen_layout.setter('height'))
        scroll.add_widget(self._gen_layout)
        root.add_widget(scroll)

        self.add_widget(root)

    def on_enter(self):
        self._load_decks()

    def _load_decks(self):
        decks = self.app.db.get_all_decks()
        self._deck_map = {d.name: d.id for d in decks}
        self._deck_spinner.values = list(self._deck_map.keys())
        if self._deck_id is not None:
            for d in decks:
                if d.id == self._deck_id:
                    self._deck_spinner.text = d.name
                    break
        elif decks:
            self._deck_spinner.text = decks[0].name

    def _get_selected_deck_id(self):
        return self._deck_map.get(self._deck_spinner.text)

    def _new_deck_dialog(self, _):
        content = BoxLayout(orientation='vertical', padding=10, spacing=8)
        name_input = TextInput(hint_text='Deck name', multiline=False,
                               size_hint_y=None, height=44)
        content.add_widget(name_input)
        btn_row = BoxLayout(size_hint_y=None, height=44, spacing=8)
        popup = Popup(title='New Deck', content=content, size_hint=(0.8, 0.4))

        def _create(_):
            name = name_input.text.strip()
            if name:
                d = self.app.db.create_deck(name)
                self._deck_map[d.name] = d.id
                self._deck_spinner.values = list(self._deck_map.keys())
                self._deck_spinner.text = d.name
                popup.dismiss()

        create_btn = Button(text='Create')
        create_btn.bind(on_press=_create)
        cancel_btn = Button(text='Cancel')
        cancel_btn.bind(on_press=popup.dismiss)
        btn_row.add_widget(create_btn)
        btn_row.add_widget(cancel_btn)
        content.add_widget(btn_row)
        popup.open()

    def _save_card(self, _):
        front = self._front_input.text.strip()
        back = self._back_input.text.strip()
        deck_id = self._get_selected_deck_id()
        if not front or not back or deck_id is None:
            return
        self.app.db.create_card(Card(front=front, back=back, deck_id=deck_id))
        self._front_input.text = ''
        self._back_input.text = ''

    def _import_txt_dialog(self, _):
        content = BoxLayout(orientation='vertical', padding=10, spacing=8)
        path_input = TextInput(hint_text='/path/to/file.txt', multiline=False,
                               size_hint_y=None, height=44)
        content.add_widget(Label(text='Enter full path to TXT file:', size_hint_y=None, height=28))
        content.add_widget(path_input)
        btn_row = BoxLayout(size_hint_y=None, height=44, spacing=8)
        popup = Popup(title='Import TXT', content=content, size_hint=(0.9, 0.45))

        def _load(_):
            popup.dismiss()
            self._import_txt(path_input.text.strip())

        ok_btn = Button(text='Import')
        ok_btn.bind(on_press=_load)
        cancel_btn = Button(text='Cancel')
        cancel_btn.bind(on_press=popup.dismiss)
        btn_row.add_widget(ok_btn)
        btn_row.add_widget(cancel_btn)
        content.add_widget(btn_row)
        popup.open()

    def _import_txt(self, path):
        deck_id = self._get_selected_deck_id()
        if not deck_id or not path:
            return
        try:
            with open(path, encoding='utf-8') as f:
                text = f.read()
        except Exception:
            return
        blocks = [b.strip() for b in text.split('\n\n') if b.strip()]
        if len(blocks) < 2:
            return
        cards_data = []
        for i in range(0, len(blocks) - 1, 2):
            cards_data.append({'front': blocks[i], 'back': blocks[i + 1]})
        existing = {c.front.strip().lower()
                    for c in self.app.db.get_cards_for_deck(deck_id)}
        unique = [cd for cd in cards_data
                  if cd['front'].strip().lower() not in existing]
        if not unique:
            return
        self._show_generated(unique, deck_id)

    def _show_generated(self, cards_data, deck_id):
        self._gen_rows = []
        self._gen_layout.clear_widgets()
        self._gen_label.opacity = 1

        for cd in cards_data:
            row = BoxLayout(size_hint_y=None, height=52, spacing=6)
            front_e = TextInput(text=cd['front'], multiline=False, size_hint_x=0.45)
            back_e = TextInput(text=cd['back'], multiline=False, size_hint_x=0.45)
            del_btn = Button(text='✕', size_hint_x=None, width=44)
            del_btn.bind(on_press=lambda _, r=row: (
                self._gen_layout.remove_widget(r),
                self._gen_rows.remove(r) if r in self._gen_rows else None,
            ))
            row.add_widget(front_e)
            row.add_widget(back_e)
            row.add_widget(del_btn)
            self._gen_layout.add_widget(row)
            self._gen_rows.append((front_e, back_e, row))

        save_all = Button(text='Save All Cards', size_hint_y=None, height=48)
        save_all.bind(on_press=lambda _: self._save_generated(deck_id))
        self._gen_layout.add_widget(save_all)

    def _save_generated(self, deck_id):
        saved = 0
        for front_e, back_e, row in self._gen_rows:
            if row.parent is None:
                continue
            front = front_e.text.strip()
            back = back_e.text.strip()
            if front and back:
                self.app.db.create_card(Card(front=front, back=back, deck_id=deck_id))
                saved += 1
        self._gen_layout.clear_widgets()
        self._gen_rows = []
        self._gen_label.opacity = 0
