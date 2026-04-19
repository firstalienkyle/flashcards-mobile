import re
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QScrollArea,
    QFrame, QDialog, QTextEdit, QCheckBox, QMessageBox,
    QDialogButtonBox, QInputDialog,
)
from PyQt5.QtCore import Qt
from data.models import Card


def _searchable(card: Card) -> str:
    """Return only the word and meanings — skip quality, conjugations, example sentences.

    Front structure: line 0 = word, line 1 = quality, rest = conjugations
    Back structure:  line 0 = word, line 1 = quality, rest = meanings + example sentences
    """
    # From front: only the word (first line)
    front_word = card.front.splitlines()[0].strip() if card.front else ''

    # From back: skip first 2 lines (word + quality), then collect meanings only
    meanings = []
    for i, raw in enumerate(card.back.splitlines()):
        line = raw.strip()
        if not line or i < 2:
            continue
        # Skip example sentences: lines starting with - • · – * or quote chars
        if line[0] in '-•·–*"\'「':
            continue
        # Strip leading numbering (1. 2. etc.)
        meanings.append(re.sub(r'^\d+[.)]\s*', '', line))

    return ' '.join([front_word] + meanings).lower()


class DeckScreen(QWidget):
    def __init__(self, app, deck_id: int):
        super().__init__()
        self.app      = app
        self._deck_id = deck_id
        self._build()
        self._update_title()
        self._load()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        top = QHBoxLayout()
        back_btn = QPushButton("← Back")
        back_btn.clicked.connect(self.app.show_home)
        top.addWidget(back_btn)
        self._title = QLabel("")
        self._title.setStyleSheet("font-size: 18px; font-weight: bold;")
        top.addWidget(self._title)
        top.addStretch()
        add_btn = QPushButton("+ Add Card")
        add_btn.clicked.connect(
            lambda: self.app.show_create(deck_id=self._deck_id)
        )
        top.addWidget(add_btn)
        rename_btn = QPushButton("✎ Rename")
        rename_btn.clicked.connect(self._rename_deck)
        top.addWidget(rename_btn)
        del_deck_btn = QPushButton("🗑 Delete Deck")
        del_deck_btn.clicked.connect(self._delete_deck)
        top.addWidget(del_deck_btn)
        root.addLayout(top)

        self._search = QLineEdit()
        self._search.setPlaceholderText("Search cards…")
        self._search.setFixedWidth(320)
        self._search.textChanged.connect(lambda _: self._load())
        root.addWidget(self._search)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        self._list_container = QWidget()
        self._list_layout = QVBoxLayout(self._list_container)
        self._list_layout.setSpacing(4)
        self._list_layout.setAlignment(Qt.AlignTop)
        scroll.setWidget(self._list_container)
        root.addWidget(scroll)

    def _update_title(self):
        for d in self.app.db.get_all_decks():
            if d.id == self._deck_id:
                self._title.setText(d.name)
                break

    def _load(self):
        query = self._search.text().lower()
        while self._list_layout.count():
            item = self._list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        cards    = self.app.db.get_cards_for_deck(self._deck_id)
        filtered = [c for c in cards
                    if not query or query in _searchable(c)]

        if not filtered:
            lbl = QLabel("No cards found.")
            lbl.setAlignment(Qt.AlignCenter)
            self._list_layout.addWidget(lbl)
            return

        for card in filtered:
            self._list_layout.addWidget(self._card_row(card))

    def _card_row(self, card: Card) -> QFrame:
        row = QFrame()
        row.setFrameShape(QFrame.StyledPanel)
        layout = QHBoxLayout(row)
        layout.setContentsMargins(12, 8, 12, 8)

        info = QVBoxLayout()
        tag  = " [Quiz]" if card.is_quiz else ""
        front_lbl = QLabel(card.front + tag)
        front_lbl.setStyleSheet("font-weight: bold;")
        info.addWidget(front_lbl)
        back_lbl = QLabel(card.back)
        back_lbl.setStyleSheet("color: gray;")
        info.addWidget(back_lbl)
        layout.addLayout(info, stretch=1)

        edit_btn = QPushButton("✎")
        edit_btn.setFixedSize(28, 28)
        edit_btn.clicked.connect(lambda _c, c=card: self._edit_card(c))
        layout.addWidget(edit_btn)

        del_btn = QPushButton("✕")
        del_btn.setFixedSize(28, 28)
        del_btn.clicked.connect(lambda _c, c=card: self._delete_card(c))
        layout.addWidget(del_btn)

        return row

    def _edit_card(self, card: Card):
        dlg = QDialog(self)
        dlg.setWindowTitle("Edit Card")
        dlg.resize(560, 320)
        dlg.setModal(True)
        layout = QVBoxLayout(dlg)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)

        boxes = {}
        for key, label, value in [("front", "Front", card.front),
                                   ("back",  "Back",  card.back)]:
            row = QHBoxLayout()
            row.addWidget(QLabel(label))
            tb = QTextEdit()
            tb.setFixedHeight(70)
            tb.setPlainText(value)
            row.addWidget(tb)
            layout.addLayout(row)
            boxes[key] = tb

        quiz_cb = QCheckBox("Quiz card")
        quiz_cb.setChecked(card.is_quiz)
        layout.addWidget(quiz_cb)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)

        def _save():
            front = boxes["front"].toPlainText().strip()
            back  = boxes["back"].toPlainText().strip()
            if not front or not back:
                QMessageBox.warning(dlg, "Missing content",
                                    "Both front and back are required.")
                return
            card.front   = front
            card.back    = back
            card.is_quiz = quiz_cb.isChecked()
            self.app.db.update_card(card)
            dlg.accept()
            self._load()

        buttons.accepted.connect(_save)
        buttons.rejected.connect(dlg.reject)
        layout.addWidget(buttons)
        dlg.open()

    def _delete_card(self, card: Card):
        reply = QMessageBox.question(
            self, "Delete card", f"Delete '{card.front}'?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.app.db.delete_card(card.id)
            self._load()

    def _rename_deck(self):
        name, ok = QInputDialog.getText(
            self, "Rename Deck", "New deck name:"
        )
        if ok and name.strip():
            self.app.db.rename_deck(self._deck_id, name.strip())
            self._update_title()

    def _delete_deck(self):
        reply = QMessageBox.question(
            self, "Delete deck",
            "Delete this deck and all its cards? This cannot be undone.",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.app.db.delete_deck(self._deck_id)
            self.app.show_home()
