from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.progressbar import ProgressBar
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget


class HomeScreen(Screen):
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self._build()

    def _build(self):
        root = BoxLayout(orientation='vertical', padding=16, spacing=12)

        # Top bar
        top = BoxLayout(size_hint_y=None, height=48, spacing=8)
        top.add_widget(Label(text='Flashcards', font_size='20sp', bold=True,
                             size_hint_x=None, width=200, halign='left'))
        top.add_widget(Widget())
        settings_btn = Button(text='⚙ Settings', size_hint_x=None, width=120)
        settings_btn.bind(on_press=lambda _: self.app.show_settings())
        top.add_widget(settings_btn)
        root.add_widget(top)

        # Daily goal
        goal_row = BoxLayout(size_hint_y=None, height=40, spacing=8)
        self._goal_label = Label(text='Loading...', halign='left')
        goal_row.add_widget(self._goal_label)
        self._progress = ProgressBar(max=10, value=0, size_hint_x=None, width=200)
        goal_row.add_widget(self._progress)
        root.add_widget(goal_row)

        # Action buttons
        btn_row = BoxLayout(size_hint_y=None, height=48, spacing=8)
        review_btn = Button(text='▶  Start Review', size_hint_x=None, width=160)
        review_btn.bind(on_press=lambda _: self.app.show_review())
        btn_row.add_widget(review_btn)
        new_btn = Button(text='+  New Card', size_hint_x=None, width=140)
        new_btn.bind(on_press=lambda _: self.app.show_create())
        btn_row.add_widget(new_btn)
        btn_row.add_widget(Widget())
        root.add_widget(btn_row)

        # Deck grid
        scroll = ScrollView()
        self._grid = GridLayout(cols=2, spacing=8, size_hint_y=None, padding=4)
        self._grid.bind(minimum_height=self._grid.setter('height'))
        scroll.add_widget(self._grid)
        root.add_widget(scroll)

        self.add_widget(root)

    def on_enter(self):
        self._load()

    def _load(self):
        goal = int(self.app.db.get_setting('daily_goal') or 10)
        count = self.app.db.get_today_reviewed_count()
        self._goal_label.text = f'{count} / {goal} cards reviewed today'
        self._progress.max = goal
        self._progress.value = min(count, goal)

        self._grid.clear_widgets()
        decks = self.app.db.get_all_decks()
        if not decks:
            self._grid.add_widget(Label(text='No decks yet — create your first card!'))
            return
        for deck in decks:
            stats = self.app.db.get_deck_stats(deck.id)
            tile = Button(
                text=f'{deck.name}\n{stats["card_count"]} cards\nMemory: {stats["avg_memory"]:.0f}%',
                size_hint_y=None, height=100,
                halign='left', valign='top',
            )
            tile.bind(on_press=lambda _, did=deck.id: self.app.show_deck(did))
            self._grid.add_widget(tile)
