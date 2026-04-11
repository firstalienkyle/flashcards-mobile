import threading
import data.database as db
from data.models import Card
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput
from kivy.uix.checkbox import CheckBox
from kivy.uix.popup import Popup
from kivy.clock import Clock
from kivy.metrics import dp
from ui._widgets import btn, lbl, top_bar, input_popup


class CreateScreen(Screen):
    def __init__(self, app, deck_id=None, **kwargs):
        super().__init__(**kwargs)
        self.app      = app
        self._deck_id = deck_id
        self._deck_map: dict = {}
        self._gen_rows: list = []
        self._build()
        self._load_decks()

    def _build(self):
        root = BoxLayout(orientation='vertical', padding=dp(12), spacing=dp(10))
        root.add_widget(top_bar('New Card', on_back=lambda _: self.app.show_home()))

        # Deck picker row
        deck_row = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(48), spacing=dp(8))
        deck_row.add_widget(lbl('Deck:', size=14, size_hint_x=None, width=dp(50)))
        self._deck_spinner = Spinner(
            text='Select deck',
            values=[],
            size_hint_x=1,
            height=dp(44),
        )
        deck_row.add_widget(self._deck_spinner)
        deck_row.add_widget(btn('+ New', on_press=self._new_deck_dialog,
                                size_hint_x=None, width=dp(72)))
        root.add_widget(deck_row)

        # Front / Back inputs
        root.add_widget(lbl('Front:', size=14))
        self._front_ti = TextInput(multiline=True, size_hint_y=None, height=dp(70))
        root.add_widget(self._front_ti)

        root.add_widget(lbl('Back:', size=14))
        self._back_ti = TextInput(multiline=True, size_hint_y=None, height=dp(70))
        root.add_widget(self._back_ti)

        # Quiz checkbox
        quiz_row = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(36))
        quiz_row.add_widget(lbl('Quiz card (type the answer):', size=13,
                                size_hint_x=None, width=dp(220)))
        self._quiz_cb = CheckBox(size_hint_x=None, width=dp(40))
        quiz_row.add_widget(self._quiz_cb)
        quiz_row.add_widget(BoxLayout())
        root.add_widget(quiz_row)

        # Save + Excel import buttons
        btn_row = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(52), spacing=dp(8))
        btn_row.add_widget(btn('Save Card', on_press=self._save_card))
        btn_row.add_widget(btn('📊 Import Excel', on_press=self._import_excel))
        root.add_widget(btn_row)

        root.add_widget(lbl('Excel: col A = front, col B = back, col C = part of speech (optional)',
                             size=11, color=(0.5, 0.5, 0.5, 1)))

        # Generated preview (hidden until import)
        self._gen_header = lbl('Imported cards — tap Save All to confirm', bold=True)
        self._gen_header.opacity = 0
        root.add_widget(self._gen_header)

        self._gen_scroll = ScrollView(size_hint_y=1)
        self._gen_list   = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(6))
        self._gen_list.bind(minimum_height=self._gen_list.setter('height'))
        self._gen_scroll.add_widget(self._gen_list)
        root.add_widget(self._gen_scroll)

        self.add_widget(root)

    # ── Deck helpers ──────────────────────────────────────────────────────────

    def _load_decks(self):
        decks = db.get_all_decks()
        self._deck_map = {d.name: d.id for d in decks}
        names = [d.name for d in decks]
        self._deck_spinner.values = names
        if names:
            if self._deck_id is not None:
                for d in decks:
                    if d.id == self._deck_id:
                        self._deck_spinner.text = d.name
                        break
            else:
                self._deck_spinner.text = names[0]
        else:
            self._deck_spinner.text = '(no decks)'

    def _get_selected_deck_id(self):
        return self._deck_map.get(self._deck_spinner.text)

    def _new_deck_dialog(self, _):
        input_popup('New Deck', 'Deck name', on_ok=self._create_deck)

    def _create_deck(self, name: str):
        d = db.create_deck(name)
        self._deck_map[d.name] = d.id
        self._deck_spinner.values = list(self._deck_map.keys())
        self._deck_spinner.text   = d.name

    # ── Manual save ───────────────────────────────────────────────────────────

    def _save_card(self, _):
        front   = self._front_ti.text.strip()
        back    = self._back_ti.text.strip()
        deck_id = self._get_selected_deck_id()
        if not front or not back:
            _alert('Missing content', 'Both front and back are required.')
            return
        if deck_id is None:
            _alert('No deck', 'Please select or create a deck first.')
            return
        db.create_card(Card(front=front, back=back,
                            is_quiz=self._quiz_cb.active, deck_id=deck_id))
        self._front_ti.text = ''
        self._back_ti.text  = ''
        _alert('Saved', 'Card saved successfully!')

    # ── Import: Excel ─────────────────────────────────────────────────────────

    def _import_excel(self, _):
        deck_id = self._get_selected_deck_id()
        if deck_id is None:
            _alert('No deck', 'Please select or create a deck first.')
            return
        try:
            from plyer import filechooser
            filechooser.open_file(
                title='Select Excel',
                filters=['*.xlsx', '*.xls'],
                on_selection=lambda sel: self._on_excel_selected(sel, deck_id),
            )
        except Exception as e:
            _alert('Error', f'File chooser unavailable:\n{e}')

    def _on_excel_selected(self, selection, deck_id):
        if not selection:
            return
        path = selection[0]
        def _run():
            try:
                import openpyxl
                wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
                ws = wb.active
                cards_data = []
                for row in ws.iter_rows(values_only=True):
                    cells = [str(c).strip() if c is not None else '' for c in row]
                    front = cells[0] if len(cells) > 0 else ''
                    back  = cells[1] if len(cells) > 1 else ''
                    pos   = cells[2] if len(cells) > 2 else ''
                    if not front or not back:
                        continue
                    if pos:
                        back = f'{back} ({pos})'
                    cards_data.append({'front': front, 'back': back, 'is_quiz': False})
                wb.close()
                Clock.schedule_once(lambda _dt, cd=cards_data: self._show_generated(cd, deck_id))
            except Exception as e:
                Clock.schedule_once(lambda _dt: _alert('Import failed', str(e)))
        threading.Thread(target=_run, daemon=True).start()

    # ── Generated preview ─────────────────────────────────────────────────────

    def _show_generated(self, cards_data: list, deck_id: int):
        if not cards_data:
            _alert('Nothing found',
                   'No valid cards found.\nExpected: col A = front, col B = back')
            return
        self._gen_list.clear_widgets()
        self._gen_rows = []

        for cd in cards_data:
            row = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(52),
                            spacing=dp(6), padding=(dp(4), dp(2)))
            front_ti = TextInput(text=cd.get('front', ''), multiline=False)
            back_ti  = TextInput(text=cd.get('back',  ''), multiline=False)
            quiz_cb  = CheckBox(active=cd.get('is_quiz', False),
                                size_hint_x=None, width=dp(36))
            del_btn  = btn('✕', size_hint_x=None, width=dp(40))

            def _remove(_, r=row):
                r.opacity = 0
                r.disabled = True

            del_btn.bind(on_press=_remove)
            row.add_widget(front_ti)
            row.add_widget(back_ti)
            row.add_widget(quiz_cb)
            row.add_widget(del_btn)
            self._gen_list.add_widget(row)
            self._gen_rows.append((front_ti, back_ti, quiz_cb, row))

        save_all = btn('Save All Cards', on_press=lambda _: self._save_generated(deck_id))
        self._gen_list.add_widget(save_all)
        self._gen_header.opacity = 1

    def _save_generated(self, deck_id: int):
        saved = 0
        for front_ti, back_ti, quiz_cb, row in self._gen_rows:
            if row.disabled:
                continue
            front = front_ti.text.strip()
            back  = back_ti.text.strip()
            if front and back:
                db.create_card(Card(front=front, back=back,
                                    is_quiz=quiz_cb.active, deck_id=deck_id))
                saved += 1
        _alert('Saved', f'{saved} cards saved to deck.',
               on_dismiss=lambda _: (self._gen_list.clear_widgets(),
                                     setattr(self._gen_header, 'opacity', 0)))


# ── Module-level helpers ───────────────────────────────────────────────────────

def _alert(title, message, on_dismiss=None):
    from kivy.uix.label import Label
    content = BoxLayout(orientation='vertical', padding=dp(12), spacing=dp(8))
    content.add_widget(Label(text=message, halign='center'))
    popup = Popup(title=title, content=content,
                  size_hint=(0.85, None), height=dp(180))
    from ui._widgets import btn as _btn
    content.add_widget(_btn('OK', on_press=lambda _: popup.dismiss()))
    if on_dismiss:
        popup.bind(on_dismiss=on_dismiss)
    popup.open()
