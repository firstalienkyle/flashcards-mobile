from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget
from kivy.uix.progressbar import ProgressBar
from ui.theme import (
    apply_bg, btn, lbl,
    BG, SURFACE, PRIMARY, SECONDARY, MUTED, TEXT,
    FONT_TITLE, FONT_BODY, FONT_SMALL,
    BTN_H, ROW_H, PAD, GAP,
)


class HomeScreen(Screen):
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self._build()

    def _build(self):
        apply_bg(self)
        root = BoxLayout(orientation='vertical', padding=PAD, spacing=GAP)

        # ── Header ──────────────────────────────────────────────────────────
        header = BoxLayout(size_hint_y=None, height=ROW_H, spacing=8)
        header.add_widget(lbl('Flashcards', font_size=FONT_TITLE, bold=True,
                               height=ROW_H))
        header.add_widget(Widget())
        settings_btn = btn('Settings', color=SECONDARY, height=ROW_H)
        settings_btn.size_hint_x = 0.35
        settings_btn.bind(on_press=lambda _: self.app.show_settings())
        header.add_widget(settings_btn)
        root.add_widget(header)

        # ── Daily goal ──────────────────────────────────────────────────────
        goal_box = BoxLayout(size_hint_y=None, height=36, spacing=10)
        self._goal_label = lbl('Loading...', font_size=FONT_SMALL,
                                color=MUTED, height=36)
        goal_box.add_widget(self._goal_label)
        self._progress = ProgressBar(max=20, value=0,
                                      size_hint_x=None, width=140)
        goal_box.add_widget(self._progress)
        root.add_widget(goal_box)

        # ── Action buttons ───────────────────────────────────────────────────
        actions = BoxLayout(size_hint_y=None, height=BTN_H, spacing=8)
        review_btn = btn('Start Review')
        review_btn.bind(on_press=lambda _: self.app.show_review())
        actions.add_widget(review_btn)
        new_btn = btn('+ New Card', color=SECONDARY)
        new_btn.bind(on_press=lambda _: self.app.show_create())
        actions.add_widget(new_btn)
        root.add_widget(actions)

        # ── Deck list ────────────────────────────────────────────────────────
        root.add_widget(lbl('Your Decks', font_size=FONT_SMALL, color=MUTED,
                             height=28))

        scroll = ScrollView()
        self._grid = GridLayout(cols=1, spacing=8, size_hint_y=None, padding=0)
        self._grid.bind(minimum_height=self._grid.setter('height'))
        scroll.add_widget(self._grid)
        root.add_widget(scroll)

        self.add_widget(root)

    def on_enter(self):
        self._load()

    def _load(self):
        goal = int(self.app.db.get_setting('daily_goal') or 20)
        count = self.app.db.get_today_reviewed_count()
        self._goal_label.text = f'{count} / {goal} today'
        self._progress.max = goal
        self._progress.value = min(count, goal)

        self._grid.clear_widgets()
        decks = self.app.db.get_all_decks()
        if not decks:
            self._grid.add_widget(
                lbl('No decks yet — tap "+ New Card" to get started',
                    color=MUTED, height=60, halign='center')
            )
            return

        for deck in decks:
            stats = self.app.db.get_deck_stats(deck.id)
            tile = btn(
                f'{deck.name}   |   {stats["card_count"]} cards   '
                f'|   Memory {stats["avg_memory"]:.0f}%',
                color=SURFACE,
                height=58,
            )
            tile.halign = 'left'
            tile.bind(size=lambda b, _: setattr(b, 'text_size', (b.width - 16, None)))
            tile.bind(on_press=lambda _, did=deck.id: self.app.show_deck(did))
            self._grid.add_widget(tile)
