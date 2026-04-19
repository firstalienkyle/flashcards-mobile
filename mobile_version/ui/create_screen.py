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
        self._is_quiz = False
        self._build()

    def _build(self):
        apply_bg(self)
        outer = BoxLayout(orientation='vertical')

        # ── Fixed header ─────────────────────────────────────────────────────
        header = BoxLayout(size_hint_y=None, height=ROW_H,
                           padding=[PAD, 0], spacing=8)
        back = btn('Back', color=SECONDARY, height=ROW_H)
        back.size_hint_x = 0.25
        back.bind(on_press=lambda _: self.app.show_home())
        header.add_widget(back)
        title = lbl('New Card', font_size=FONT_TITLE, bold=True,
                    height=ROW_H, halign='center')
        header.add_widget(title)
        header.add_widget(Widget(size_hint_x=0.25))  # mirror back btn for centering
        outer.add_widget(header)

        # ── Single scrollable body ────────────────────────────────────────────
        scroll = ScrollView(do_scroll_x=False)
        body = BoxLayout(orientation='vertical', padding=PAD, spacing=GAP * 2,
                         size_hint_y=None)
        body.bind(minimum_height=body.setter('height'))

        # Deck row
        deck_row = BoxLayout(size_hint_y=None, height=BTN_H, spacing=8)
        deck_lbl = lbl('Deck:', height=BTN_H, size_hint_x=0.22,
                       font_size=FONT_BODY, halign='left')
        deck_lbl.size_hint_y = None
        deck_lbl.height = BTN_H
        deck_row.add_widget(deck_lbl)
        self._deck_spinner = Spinner(
            text='Select', values=[],
            size_hint_x=0.42, size_hint_y=None, height=BTN_H,
            background_normal='', background_color=SURFACE,
            color=TEXT, font_size=FONT_SMALL,
        )
        deck_row.add_widget(self._deck_spinner)
        new_deck = btn('+ New', color=SECONDARY, height=BTN_H)
        new_deck.size_hint_x = 0.24
        new_deck.bind(on_press=self._new_deck_dialog)
        deck_row.add_widget(new_deck)
        del_deck = btn('Del', color=DANGER, height=BTN_H)
        del_deck.size_hint_x = 0.20
        del_deck.bind(on_press=self._delete_deck_dialog)
        deck_row.add_widget(del_deck)
        body.add_widget(deck_row)

        # Front input — auto-expanding
        body.add_widget(lbl('Front:', height=36, color=MUTED,
                             font_size=FONT_SMALL))
        self._front_input = TextInput(
            multiline=True, size_hint_y=None,
            background_color=SURFACE, foreground_color=TEXT,
            font_size=FONT_BODY,
        )
        self._front_input.height = BTN_H
        self._front_input.bind(
            minimum_height=lambda inst, h: setattr(inst, 'height', max(h, BTN_H))
        )
        body.add_widget(self._front_input)

        # Back input — auto-expanding
        body.add_widget(lbl('Back:', height=36, color=MUTED,
                             font_size=FONT_SMALL))
        self._back_input = TextInput(
            multiline=True, size_hint_y=None,
            background_color=SURFACE, foreground_color=TEXT,
            font_size=FONT_BODY,
        )
        self._back_input.height = BTN_H
        self._back_input.bind(
            minimum_height=lambda inst, h: setattr(inst, 'height', max(h, BTN_H))
        )
        body.add_widget(self._back_input)

        # Quiz toggle — tapping cycles Normal ↔ Quiz
        self._quiz_btn = btn('Mode: Normal Card', color=SECONDARY)
        self._quiz_btn.bind(on_press=self._toggle_quiz)
        body.add_widget(self._quiz_btn)

        save = btn('Save Card')
        save.bind(on_press=self._save_card)
        body.add_widget(save)

        # Extra spacer before import section
        body.add_widget(Widget(size_hint_y=None, height=GAP * 3))

        body.add_widget(lbl('-- or import from file --', font_size=FONT_SMALL,
                             color=MUTED, height=40, halign='center'))

        # Extra spacer before Choose TXT button
        body.add_widget(Widget(size_hint_y=None, height=GAP * 2))

        import_btn = btn('Choose TXT File', color=SECONDARY)
        import_btn.bind(on_press=self._pick_file)
        body.add_widget(import_btn)

        # Extra spacer before format hint
        body.add_widget(Widget(size_hint_y=None, height=GAP * 2))

        body.add_widget(lbl(
            'Format: front, blank line, back, blank line, repeat',
            font_size=FONT_SMALL, color=MUTED, height=40,
        ))

        # Imported cards preview (grows dynamically)
        self._gen_label = lbl('Review imported cards before saving',
                               bold=True, height=44)
        self._gen_label.opacity = 0
        body.add_widget(self._gen_label)

        self._gen_layout = GridLayout(cols=1, spacing=8, size_hint_y=None, padding=0)
        self._gen_layout.bind(minimum_height=self._gen_layout.setter('height'))
        body.add_widget(self._gen_layout)

        scroll.add_widget(body)
        outer.add_widget(scroll)

        # ── Status label pinned to bottom ─────────────────────────────────────
        self._import_status = lbl('', font_size=FONT_SMALL, color=DANGER,
                                   height=50, halign='center',
                                   size_hint_y=None)
        outer.add_widget(self._import_status)

        self.add_widget(outer)

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
        popup = Popup(title='New Deck', content=content, size_hint=(0.85, 0.38))

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

    def _delete_deck_dialog(self, _):
        deck_id = self._get_selected_deck_id()
        if deck_id is None:
            self._import_status.text = 'Select a deck to delete.'
            self._import_status.color = DANGER
            return
        deck_name = self._deck_spinner.text
        content = BoxLayout(orientation='vertical', padding=12, spacing=8)
        content.add_widget(lbl(
            f'Delete "{deck_name}" and all its cards?\nThis cannot be undone.',
            font_size=FONT_SMALL, color=DANGER, height=80, halign='center',
        ))
        popup = Popup(title='Delete Deck', content=content, size_hint=(0.85, 0.40))

        def _confirm(_):
            self.app.db.delete_deck(deck_id)
            popup.dismiss()
            self._load_decks()
            self._import_status.text = f'Deck "{deck_name}" deleted.'
            self._import_status.color = MUTED

        btn_row = BoxLayout(size_hint_y=None, height=BTN_H, spacing=8)
        confirm = btn('Delete', color=DANGER)
        confirm.bind(on_press=_confirm)
        cancel = btn('Cancel', color=SECONDARY)
        cancel.bind(on_press=popup.dismiss)
        btn_row.add_widget(confirm)
        btn_row.add_widget(cancel)
        content.add_widget(btn_row)
        popup.open()

    def _toggle_quiz(self, _):
        self._is_quiz = not self._is_quiz
        if self._is_quiz:
            self._quiz_btn.text = 'Mode: Quiz Card  (user must type answer)'
            self._quiz_btn.background_color = SUCCESS
        else:
            self._quiz_btn.text = 'Mode: Normal Card'
            self._quiz_btn.background_color = SECONDARY

    # ── Manual save ───────────────────────────────────────────────────────────

    def _save_card(self, _):
        front = self._front_input.text.strip()
        back = self._back_input.text.strip()
        deck_id = self._get_selected_deck_id()
        if not front or not back or deck_id is None:
            self._import_status.text = 'Fill in front, back, and select a deck.'
            self._import_status.color = DANGER
            return
        self.app.db.create_card(Card(front=front, back=back,
                                     is_quiz=self._is_quiz, deck_id=deck_id))
        self._front_input.text = ''
        self._back_input.text = ''
        kind = 'Quiz card' if self._is_quiz else 'Card'
        self._import_status.text = f'{kind} saved!'
        self._import_status.color = SUCCESS

    # ── File picker ───────────────────────────────────────────────────────────

    def _pick_file(self, _):
        deck_id = self._get_selected_deck_id()
        if deck_id is None:
            self._import_status.text = 'Select a deck first.'
            self._import_status.color = DANGER
            return

        try:
            from plyer import filechooser
            filechooser.open_file(
                on_selection=self._on_file_selected,
                filters=['*.txt', '*.TXT'],
                title='Choose a TXT file',
            )
        except Exception:
            self._show_path_input_popup()

    def _show_path_input_popup(self):
        content = BoxLayout(orientation='vertical', padding=12, spacing=8)
        content.add_widget(lbl('Enter full path to your .txt file:',
                                height=32, color=MUTED))
        path_input = TextInput(
            hint_text='/path/to/file.txt',
            multiline=False,
            size_hint_y=None, height=BTN_H,
            background_color=SURFACE, foreground_color=TEXT,
        )
        content.add_widget(path_input)
        popup = Popup(title='Import TXT', content=content, size_hint=(0.9, 0.42))

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
            card_box = BoxLayout(orientation='vertical',
                                 size_hint_y=None, height=182, spacing=4)

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

            quiz_b = btn('Normal', color=SECONDARY, height=BTN_H // 2)
            quiz_b._is_quiz = False
            def _toggle_q(_, b=quiz_b):
                b._is_quiz = not b._is_quiz
                b.text = 'Quiz' if b._is_quiz else 'Normal'
                b.background_color = SUCCESS if b._is_quiz else SECONDARY
            quiz_b.bind(on_press=_toggle_q)

            card_box.add_widget(top_row)
            card_box.add_widget(back_e)
            card_box.add_widget(quiz_b)
            self._gen_layout.add_widget(card_box)
            self._gen_rows.append((front_e, back_e, quiz_b, card_box))

        save_all = btn('Save All Cards', color=SUCCESS)
        save_all.bind(on_press=lambda _: self._save_generated(deck_id))
        self._gen_layout.add_widget(save_all)

    def _remove_card(self, card_box):
        self._gen_layout.remove_widget(card_box)
        self._gen_rows = [(f, b, q, box) for f, b, q, box in self._gen_rows
                          if box is not card_box]

    def _save_generated(self, deck_id):
        saved = 0
        for front_e, back_e, quiz_b, _ in self._gen_rows:
            front = front_e.text.strip()
            back = back_e.text.strip()
            if front and back:
                self.app.db.create_card(Card(front=front, back=back,
                                             is_quiz=quiz_b._is_quiz,
                                             deck_id=deck_id))
                saved += 1
        self._gen_layout.clear_widgets()
        self._gen_rows = []
        self._gen_label.opacity = 0
        self._import_status.text = f'{saved} cards saved.'
        self._import_status.color = SUCCESS
