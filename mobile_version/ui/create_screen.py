from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from kivy.uix.popup import Popup
from data.models import Card
from ui.theme import (
    apply_bg, btn, lbl,
    SURFACE, SECONDARY, DANGER, MUTED, TEXT,
    FONT_TITLE, FONT_BODY,
    BTN_H, ROW_H, PAD, GAP,
)


class CreateScreen(Screen):
    def __init__(self, app, deck_id=None, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self._deck_id = deck_id
        self._deck_map = {}
        self._gen_rows = []
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
        header.add_widget(lbl('New Card', font_size=FONT_TITLE, bold=True,
                               height=ROW_H))
        header.add_widget(Widget())
        root.add_widget(header)

        # ── Deck row ─────────────────────────────────────────────────────────
        deck_row = BoxLayout(size_hint_y=None, height=44, spacing=8)
        deck_row.add_widget(lbl('Deck:', height=44, size_hint_x=None, width=55))
        self._deck_spinner = Spinner(
            text='Select deck', values=[],
            size_hint_x=1, size_hint_y=None, height=44,
            background_normal='', background_color=SURFACE,
            color=TEXT,
        )
        deck_row.add_widget(self._deck_spinner)
        new_deck = btn('+ New', color=SECONDARY, height=44)
        new_deck.size_hint_x = 0.25
        new_deck.bind(on_press=self._new_deck_dialog)
        deck_row.add_widget(new_deck)
        root.add_widget(deck_row)

        # ── Front / Back inputs ──────────────────────────────────────────────
        root.add_widget(lbl('Front:', height=26, color=MUTED))
        self._front_input = TextInput(
            multiline=True, size_hint_y=None, height=80,
            background_color=SURFACE, foreground_color=TEXT,
        )
        root.add_widget(self._front_input)

        root.add_widget(lbl('Back:', height=26, color=MUTED))
        self._back_input = TextInput(
            multiline=True, size_hint_y=None, height=80,
            background_color=SURFACE, foreground_color=TEXT,
        )
        root.add_widget(self._back_input)

        # ── Buttons ──────────────────────────────────────────────────────────
        btn_row = BoxLayout(size_hint_y=None, height=BTN_H, spacing=8)
        save = btn('Save Card')
        save.bind(on_press=self._save_card)
        btn_row.add_widget(save)
        import_txt = btn('Import TXT', color=SECONDARY)
        import_txt.bind(on_press=self._import_txt_dialog)
        btn_row.add_widget(import_txt)
        root.add_widget(btn_row)

        # ── Imported cards preview ────────────────────────────────────────────
        self._gen_label = lbl('Imported cards - review before saving',
                               bold=True, height=32)
        self._gen_label.opacity = 0
        root.add_widget(self._gen_label)

        scroll = ScrollView()
        self._gen_layout = GridLayout(cols=1, spacing=6, size_hint_y=None, padding=0)
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
        content = BoxLayout(orientation='vertical', padding=12, spacing=8)
        name_input = TextInput(hint_text='Deck name', multiline=False,
                               size_hint_y=None, height=44)
        content.add_widget(name_input)
        popup = Popup(title='New Deck', content=content, size_hint=(0.8, 0.35))

        def _create(_):
            name = name_input.text.strip()
            if name:
                d = self.app.db.create_deck(name)
                self._deck_map[d.name] = d.id
                self._deck_spinner.values = list(self._deck_map.keys())
                self._deck_spinner.text = d.name
                popup.dismiss()

        btn_row = BoxLayout(size_hint_y=None, height=BTN_H, spacing=8)
        create = btn('Create')
        create.bind(on_press=_create)
        cancel = btn('Cancel', color=SECONDARY)
        cancel.bind(on_press=popup.dismiss)
        btn_row.add_widget(create)
        btn_row.add_widget(cancel)
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
        content = BoxLayout(orientation='vertical', padding=12, spacing=8)
        content.add_widget(lbl('Full path to .txt file:', height=28, color=MUTED))
        path_input = TextInput(hint_text='/path/to/file.txt', multiline=False,
                               size_hint_y=None, height=44)
        content.add_widget(path_input)
        popup = Popup(title='Import TXT', content=content, size_hint=(0.9, 0.38))

        def _load(_):
            popup.dismiss()
            self._import_txt(path_input.text.strip())

        btn_row = BoxLayout(size_hint_y=None, height=BTN_H, spacing=8)
        ok = btn('Import')
        ok.bind(on_press=_load)
        cancel = btn('Cancel', color=SECONDARY)
        cancel.bind(on_press=popup.dismiss)
        btn_row.add_widget(ok)
        btn_row.add_widget(cancel)
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
        if unique:
            self._show_generated(unique, deck_id)

    def _show_generated(self, cards_data, deck_id):
        self._gen_rows = []
        self._gen_layout.clear_widgets()
        self._gen_label.opacity = 1

        for cd in cards_data:
            row = BoxLayout(size_hint_y=None, height=52, spacing=6)
            front_e = TextInput(text=cd['front'], multiline=False, size_hint_x=0.45,
                                background_color=SURFACE, foreground_color=TEXT)
            back_e = TextInput(text=cd['back'], multiline=False, size_hint_x=0.45,
                               background_color=SURFACE, foreground_color=TEXT)
            del_b = btn('X', color=DANGER, width=44, height=52)
            del_b.bind(on_press=lambda _, r=row: (
                self._gen_layout.remove_widget(r),
                self._gen_rows.remove(r) if r in self._gen_rows else None,
            ))
            row.add_widget(front_e)
            row.add_widget(back_e)
            row.add_widget(del_b)
            self._gen_layout.add_widget(row)
            self._gen_rows.append((front_e, back_e, row))

        save_all = btn('Save All Cards')
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
