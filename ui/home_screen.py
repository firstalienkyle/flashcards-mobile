from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QProgressBar, QScrollArea, QFrame,
)
from PyQt5.QtCore import Qt
import data.database as db


class HomeScreen(QWidget):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self._build()
        self._load()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        # Top bar
        top = QHBoxLayout()
        title = QLabel("Flashcards")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        top.addWidget(title)
        top.addStretch()
        settings_btn = QPushButton("⚙ Settings")
        settings_btn.clicked.connect(self.app.show_settings)
        top.addWidget(settings_btn)
        root.addLayout(top)

        # Daily goal bar
        goal_frame = QFrame()
        goal_frame.setFrameShape(QFrame.StyledPanel)
        goal_layout = QHBoxLayout(goal_frame)
        self._goal_label = QLabel("Loading...")
        goal_layout.addWidget(self._goal_label)
        goal_layout.addStretch()
        self._progress = QProgressBar()
        self._progress.setFixedWidth(220)
        self._progress.setTextVisible(False)
        goal_layout.addWidget(self._progress)
        root.addWidget(goal_frame)

        # Action buttons
        btn_row = QHBoxLayout()
        for text, slot in [
            ("▶  Start Review", self.app.show_review),
            ("+  New Card",     self.app.show_create),
        ]:
            btn = QPushButton(text)
            btn.clicked.connect(slot)
            btn_row.addWidget(btn)
        btn_row.addStretch()
        root.addLayout(btn_row)

        # Deck grid (scrollable)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        self._grid_container = QWidget()
        self._grid = QGridLayout(self._grid_container)
        self._grid.setSpacing(8)
        self._grid.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        scroll.setWidget(self._grid_container)
        root.addWidget(scroll)

    def _load(self):
        goal  = int(self.app.db.get_setting("daily_goal") or 10)
        count = self.app.db.get_today_reviewed_count()
        self._goal_label.setText(f"{count} / {goal} cards reviewed today")
        self._progress.setMaximum(goal)
        self._progress.setValue(min(count, goal))

        while self._grid.count():
            item = self._grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        decks = self.app.db.get_all_decks()
        if not decks:
            lbl = QLabel("No decks yet — create your first card!")
            lbl.setAlignment(Qt.AlignCenter)
            self._grid.addWidget(lbl, 0, 0, 1, 3)
            return

        for i, deck in enumerate(decks):
            stats = self.app.db.get_deck_stats(deck.id)
            self._deck_tile(deck, stats, row=i // 3, col=i % 3)

    def _deck_tile(self, deck, stats, row, col):
        tile = QFrame()
        tile.setFrameShape(QFrame.StyledPanel)
        tile.setCursor(Qt.PointingHandCursor)
        layout = QVBoxLayout(tile)
        layout.setContentsMargins(12, 12, 12, 12)

        name_lbl = QLabel(deck.name)
        name_lbl.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(name_lbl)
        layout.addWidget(QLabel(f"{stats['card_count']} cards"))
        layout.addWidget(QLabel(f"Memory: {stats['avg_memory']:.0f}%"))

        tile.mousePressEvent = lambda _e, did=deck.id: self.app.show_deck(did)
        self._grid.addWidget(tile, row, col)
