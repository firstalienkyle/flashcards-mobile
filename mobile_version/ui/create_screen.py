from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from kivy.uix.popup import Popup
from kivy.clock import Clock
from data.models import Card
from ui.theme import (
    apply_bg, btn, lbl,
    SURFACE, SECONDARY, DANGER, SUCCESS, MUTED, TEXT,
    FONT_TITLE, FONT_BODY, FONT_SMALL,
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
        deck_row = BoxLayout(size_hint_y=None, height=BTN_H, spacing=8)
        deck_row.add_widget(lbl('Deck:', height=BTN_H, size_hint_x=None, width=55))
        self._deck_spinner = Spinner(
            text='Select deck', values=[],
            size_hint_x=1, size_hint_y=None, height=BTN_H,
            background_normal='', background_color=SURFACE,
            color=TEXT,
        )
        deck_row.add_widget(self._deck_spinner)
        new_deck = btn('+ New', color=SECONDARY, height=BTN_H)
        new_deck.size_hint_x = 0.25
        new_deck.bind(on_press=self._new_deck_dialog)
        deck_row.add_widget(new_deck)
        root.add_widget(deck_row)

        # ── Manual entry ─────────────────────────────────────────────────────
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

        save = btn('Save Card')
        save.bind(on_press=self._save_card)
        root.add_widget(save)

        # ── Import from file ──────────────────────────────────────────────────
        root.add_widget(lbl('-- or import from file --', font_size=FONT_SMALL,
                             color=MUTED, height=28, halign='center'))

        import_btn = btn('Choose TXT File', color=SECONDARY)
        import_btn.bind(on_press=self._pick_file)
        root.add_widget(import_btn)

        root.add_widget(lbl(
            'Format: front text, blank line, back text, blank line, repeat',
            font_size=FONT_SMALL, color=MUTED, height=26,
        ))

        self._import_status = lbl('', font_size=FONT_SMALL, color=MUTED, height=26)
        root.add_widget(self._import_status)

        # ── Preview of imported cards ─────────────────────────────────────────
        self._gen_label = lbl('Review imported cards before saving',
                               bold=True, height=32)
        self._gen_label.opacity = 0
        root.add_widget(self._gen_label)

        scroll = ScrollView()
        self._gen_layout = GridLayout(cols=1, spacing=8, size_hint_y=None, padding=0)
        self._gen_layout.bind(minimum_height=self._gen_layout.setter('height'))
        scroll.add_widget(self._gen_layout)
        root.add_widget(scroll)

        self.add_widget(root)

    # ── Deck helpers ──────────────────────────────────────────────────────────

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
                               size_hint_y=None, height=BTN_H)
        content.add_widget(name_input)
        popup = Popup(title='New Deck', content=content, size_hint=(0.85, 0.35))

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

    # ── Manual save ───────────────────────────────────────────────────────────

    def _save_card(self, _):
        front = self._front_input.text.strip()
        back = self._back_input.text.strip()
        deck_id = self._get_selected_deck_id()
        if not front or not back or deck_id is None:
            return
        self.app.db.create_card(Card(front=front, back=back, deck_id=deck_id))
        self._front_input.text = ''
        self._back_input.text = ''

    # ── File picker ───────────────────────────────────────────────────────────

    def _pick_file(self, _):
        deck_id = self._get_selected_deck_id()
        if deck_id is None:
            self._import_status.text = 'Select a deck first.'
            self._import_status.color = DANGER
            return

        # Try plyer (works on Android); fall back to path input on desktop
        try:
            from plyer import filechooser
            filechooser.open_file(
                on_selection=self._on_file_selected,
                filters=['*.txt', '*.TXT'],
                title='Choose a TXT file',
            )
        except Exception:
            # Desktop preview: plyer has no native picker, use manual path input
            self._show_path_input_popup()

    def _show_path_input_popup(self):
        content = BoxLayout(orientation='vertical', padding=12, spacing=8)
        content.add_widget(lbl('Enter full path to your .txt file:',
                                height=28, color=MUTED))
        path_input = TextInput(
            hint_text='/path/to/file.txt',
            multiline=False,
            size_hint_y=None, height=BTN_H,
            background_color=SURFACE, foreground_color=TEXT,
        )
        content.add_widget(path_input)
        popup = Popup(title='Import TXT', content=content, size_hint=(0.9, 0.38))

        def _load(_):
            popup.dismiss()
            p = path_input.text.strip()
            if p:
                self._load_file([p])

        btn_row = BoxLayout(size_hint_y=None, height=BTN_H, spacing=8)
        ok = btn('Import')
        ok.bind(on_press=_load)
        cancel = btn('Cancel', color=SECONDARY)
        cancel.bind(on_press=popup.dismiss)
        btn_row.add_widget(ok)
        btn_row.add_widget(cancel)
        content.add_widget(btn_row)
        popup.open()

    def _on_file_selected(self, selection):
        # plyer calls this on a background thread — schedule back on main thread
        Clock.schedule_once(lambda dt: self._load_file(selection))

    def _load_file(self, selection):
        if not selection:
            return
        path = selection[0]
        deck_id = self._get_selected_deck_id()
        if not deck_id:
            return
        try:
            with open(path, encoding='utf-8') as f:
                text = f.read()
        except Exception as e:
            self._import_status.text = f'Could not read file: {e}'
            self._import_status.color = DANGER
            return

        blocks = [b.strip() for b in text.split('\n\n') if b.strip()]
        if len(blocks) < 2:
            self._import_status.text = 'No card pairs found. Check the file format.'
            self._import_status.color = DANGER
            return

        cards_data = []
        for i in range(0, len(blocks) - 1, 2):
            cards_data.append({'front': blocks[i], 'back': blocks[i + 1]})

        existing = {c.front.strip().lower()
                    for c in self.app.db.get_cards_for_deck(deck_id)}
        unique = [cd for cd in cards_data
                  if cd['front'].strip().lower() not in existing]
        dupes = len(cards_data) - len(unique)

        if not unique:
            self._import_status.text = 'All cards already exist in this deck.'
            self._import_status.color = MUTED
            return

        msg = f'{len(unique)} cards ready to import'
        if dupes:
            msg += f'  ({dupes} duplicates skipped)'
        self._import_status.text = msg
        self._import_status.color = SUCCESS
        self._show_generated(unique, deck_id)

    # ── Card preview ──────────────────────────────────────────────────────────

    def _show_generated(self, cards_data, deck_id):
        self._gen_rows = []
        self._gen_layout.clear_widgets()
        self._gen_label.opacity = 1

        for cd in cards_data:
            # Each card is a vertical stacked panel (front on top, back below)
            card_box = BoxLayout(orientation='vertical',
                                 size_hint_y=None, height=120, spacing=4)

            top_row = BoxLayout(size_hint_y=None, height=52, spacing=6)
            front_e = TextInput(
                text=cd['front'], multiline=False,
                size_hint_x=1, size_hint_y=None, height=52,
                background_color=SURFACE, foreground_color=TEXT,
                hint_text='Front',
            )
            del_b = btn('X', color=DANGER, height=52)
            del_b.size_hint_x = 0.15
            del_b.bind(on_press=lambda _, b=card_box: self._remove_card(b))
            top_row.add_widget(front_e)
            top_row.add_widget(del_b)

            back_e = TextInput(
                text=cd['back'], multiline=False,
                size_hint_y=None, height=52,
                background_color=SURFACE, foreground_color=TEXT,
                hint_text='Back',
            )

            card_box.add_widget(top_row)
            card_box.add_widget(back_e)
            self._gen_layout.add_widget(card_box)
            self._gen_rows.append((front_e, back_e, card_box))

        save_all = btn('Save All Cards', color=SUCCESS)
        save_all.bind(on_press=lambda _: self._save_generated(deck_id))
        self._gen_layout.add_widget(save_all)

    def _remove_card(self, card_box):
        self._gen_layout.remove_widget(card_box)
        self._gen_rows = [(f, b, box) for f, b, box in self._gen_rows
                          if box is not card_box]

    def _save_generated(self, deck_id):
        saved = 0
        for front_e, back_e, _ in self._gen_rows:
            front = front_e.text.strip()
            back = back_e.text.strip()
            if front and back:
                self.app.db.create_card(Card(front=front, back=back, deck_id=deck_id))
                saved += 1
        self._gen_layout.clear_widgets()
        self._gen_rows = []
        self._gen_label.opacity = 0
        self._import_status.text = f'{saved} cards saved.'
        self._import_status.color = SUCCESS
