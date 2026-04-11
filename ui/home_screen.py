import data.database as db
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.progressbar import ProgressBar
from kivy.metrics import dp
from ui._widgets import btn, lbl, CARD


class HomeScreen(Screen):
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self._build()
        self._load()

    def _build(self):
        root = BoxLayout(orientation='vertical', padding=dp(16), spacing=dp(12))

        # Top bar: title + settings button
        top = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(52), spacing=dp(8))
        top.add_widget(lbl('Flashcards', size=22, bold=True))
        top.add_widget(btn('⚙ Settings', on_press=lambda _: self.app.show_settings(),
                           size_hint_x=None, width=dp(110)))
        root.add_widget(top)

        # Daily goal row
        goal_row = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(40), spacing=dp(8))
        self._goal_lbl = lbl('Loading...', size=14)
        goal_row.add_widget(self._goal_lbl)
        self._progress = ProgressBar(max=100, value=0, size_hint_x=None, width=dp(160))
        goal_row.add_widget(self._progress)
        root.add_widget(goal_row)

        # Action buttons
        btn_row = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(52), spacing=dp(8))
        btn_row.add_widget(btn('▶  Start Review', on_press=lambda _: self.app.show_review()))
        btn_row.add_widget(btn('+  New Card', on_press=lambda _: self.app.show_create()))
        root.add_widget(btn_row)

        # Scrollable deck grid (2-column)
        scroll = ScrollView()
        self._grid = GridLayout(cols=2, spacing=dp(8), size_hint_y=None, padding=dp(4))
        self._grid.bind(minimum_height=self._grid.setter('height'))
        scroll.add_widget(self._grid)
        root.add_widget(scroll)

        self.add_widget(root)

    def _load(self):
        goal  = int(db.get_setting('daily_goal') or 10)
        count = db.get_today_reviewed_count()
        self._goal_lbl.text = f'{count} / {goal} cards today'
        self._progress.max   = goal
        self._progress.value = min(count, goal)

        self._grid.clear_widgets()
        decks = db.get_all_decks()
        if not decks:
            self._grid.add_widget(lbl('No decks yet — create your first card!',
                                      halign='center'))
            return

        for deck in decks:
            stats = db.get_deck_stats(deck.id)
            self._grid.add_widget(self._deck_tile(deck, stats))

    def _deck_tile(self, deck, stats):
        tile = Button(
            text=f'[b]{deck.name}[/b]\n{stats["card_count"]} cards  ·  Mem: {stats["avg_memory"]:.0f}%',
            markup=True,
            background_color=CARD,
            size_hint_y=None,
            height=dp(90),
            halign='left',
            valign='middle',
        )
        tile.bind(size=tile.setter('text_size'))
        tile.bind(on_press=lambda _, did=deck.id: self.app.show_deck(did))
        return tile
