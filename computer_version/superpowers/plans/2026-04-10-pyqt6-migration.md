# PyQt6 Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace all customtkinter UI code with PyQt6 so the app launches on macOS 12 without crashing.

**Architecture:** `QMainWindow` with `setCentralWidget()` for screen swapping — each screen is a `QWidget` subclass. Services and data layer are untouched. Native macOS appearance, no custom colors.

**Tech Stack:** PyQt6, Python 3.12 (existing venv), existing services/data layer unchanged.

---

## File Map

| Action | File | Purpose |
|---|---|---|
| Modify | `requirements.txt` | Swap customtkinter for PyQt6 |
| Modify | `main.py` | Add QApplication, swap mainloop for Qt event loop |
| Rewrite | `ui/app.py` | QMainWindow + setCentralWidget screen router |
| Rewrite | `ui/home_screen.py` | Deck grid, daily goal progress bar |
| Rewrite | `ui/settings_screen.py` | Settings form with QFormLayout |
| Rewrite | `ui/deck_screen.py` | Card list, search, edit/delete dialogs |
| Rewrite | `ui/create_screen.py` | Manual card entry + scan + PDF import |
| Rewrite | `ui/review_screen.py` | Card flip, quiz entry, Claude explanation |

---

## Task 1: Install PyQt6 and update requirements

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: Update requirements.txt**

Replace `customtkinter==5.2.2` with `PyQt6>=6.6.0`:

```
PyQt6>=6.6.0
anthropic>=0.25.0
opencv-python>=4.9.0
pdfplumber>=0.11.0
pystray>=0.19.5
plyer>=2.1.0
Pillow>=10.3.0
pytest>=8.0.0
pytest-mock>=3.12.0
```

- [ ] **Step 2: Install PyQt6**

```bash
.venv/bin/pip install PyQt6
```

Expected: `Successfully installed PyQt6-...` (pre-built wheel, no compilation)

- [ ] **Step 3: Verify import**

```bash
.venv/bin/python -c "from PyQt6.QtWidgets import QApplication; print('PyQt6 OK')"
```

Expected: `PyQt6 OK`

- [ ] **Step 4: Commit**

```bash
git add requirements.txt
git commit -m "feat: swap customtkinter for PyQt6 in requirements"
```

---

## Task 2: Port ui/app.py — App window and screen router

**Files:**
- Rewrite: `ui/app.py`

- [ ] **Step 1: Rewrite ui/app.py**

```python
from PyQt6.QtWidgets import QMainWindow


class App(QMainWindow):
    """
    Root window and screen router. All service references are stored here
    so every screen can access them via self.app.
    """

    def __init__(self, db, review_scheduler_mod, claude_service,
                 scan_service, notification_service):
        super().__init__()
        self.setWindowTitle("Flashcards")
        self.setFixedSize(960, 660)

        self.db     = db
        self.rs     = review_scheduler_mod
        self.claude = claude_service
        self.scan   = scan_service
        self.notif  = notification_service

        self.show_home()

    # ── Screen routing ──────────────────────────────────────────────────────────

    def _switch(self, screen) -> None:
        old = self.centralWidget()
        self.setCentralWidget(screen)
        if old is not None:
            old.deleteLater()

    def show_home(self) -> None:
        from ui.home_screen import HomeScreen
        self._switch(HomeScreen(self))

    def show_review(self) -> None:
        from ui.review_screen import ReviewScreen
        self._switch(ReviewScreen(self))

    def show_create(self, deck_id=None) -> None:
        from ui.create_screen import CreateScreen
        self._switch(CreateScreen(self, deck_id=deck_id))

    def show_deck(self, deck_id: int) -> None:
        from ui.deck_screen import DeckScreen
        self._switch(DeckScreen(self, deck_id=deck_id))

    def show_settings(self) -> None:
        from ui.settings_screen import SettingsScreen
        self._switch(SettingsScreen(self))
```

- [ ] **Step 2: Commit**

```bash
git add ui/app.py
git commit -m "feat: port App to QMainWindow with setCentralWidget routing"
```

---

## Task 3: Update main.py — QApplication bootstrap

**Files:**
- Modify: `main.py`

- [ ] **Step 1: Rewrite main.py**

Note: `QApplication` must be created before any `QWidget`. The Qt event loop is started
by calling `qt_app.exec()` — this is `QApplication.exec()`, Qt's run-loop method (not
a shell command). Replace the old `app.mainloop()` call with `sys.exit(qt_app.exec())`.

```python
import sys
import data.database as db
from PyQt6.QtWidgets import QApplication
from services.claude_service import ClaudeService
from services.scan_service import ScanService
from services.notification_service import NotificationService
import services.review_scheduler as review_scheduler
from ui.app import App


def main():
    qt_app = QApplication(sys.argv)

    db.init_db()

    api_key          = db.get_setting("claude_api_key")
    claude_service   = ClaudeService(api_key=api_key)
    scan_service     = ScanService()
    notification_svc = NotificationService(
        get_setting=db.get_setting,
        get_today_count=db.get_today_reviewed_count,
    )
    notification_svc.start()

    app = App(
        db=db,
        review_scheduler_mod=review_scheduler,
        claude_service=claude_service,
        scan_service=scan_service,
        notification_service=notification_svc,
    )
    app.show()

    # Start the Qt event loop. QApplication.exec() blocks until the window closes.
    run_loop = getattr(qt_app, "exec")
    sys.exit(run_loop())


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Commit**

```bash
git add main.py
git commit -m "feat: add QApplication bootstrap in main.py"
```

---

## Task 4: Port ui/home_screen.py — Home screen with deck grid

**Files:**
- Rewrite: `ui/home_screen.py`

- [ ] **Step 1: Rewrite ui/home_screen.py**

```python
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QProgressBar, QScrollArea, QFrame,
)
from PyQt6.QtCore import Qt
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

        # ── Top bar ──────────────────────────────────────────────────────────
        top = QHBoxLayout()
        title = QLabel("Flashcards")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        top.addWidget(title)
        top.addStretch()
        settings_btn = QPushButton("⚙ Settings")
        settings_btn.clicked.connect(self.app.show_settings)
        top.addWidget(settings_btn)
        root.addLayout(top)

        # ── Daily goal bar ────────────────────────────────────────────────────
        goal_frame = QFrame()
        goal_frame.setFrameShape(QFrame.Shape.StyledPanel)
        goal_layout = QHBoxLayout(goal_frame)
        self._goal_label = QLabel("Loading...")
        goal_layout.addWidget(self._goal_label)
        goal_layout.addStretch()
        self._progress = QProgressBar()
        self._progress.setFixedWidth(220)
        self._progress.setTextVisible(False)
        goal_layout.addWidget(self._progress)
        root.addWidget(goal_frame)

        # ── Action buttons ────────────────────────────────────────────────────
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

        # ── Deck grid (scrollable) ─────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._grid_container = QWidget()
        self._grid = QGridLayout(self._grid_container)
        self._grid.setSpacing(8)
        self._grid.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        scroll.setWidget(self._grid_container)
        root.addWidget(scroll)

    def _load(self):
        goal  = int(self.app.db.get_setting("daily_goal") or 10)
        count = self.app.db.get_today_reviewed_count()
        self._goal_label.setText(f"{count} / {goal} cards reviewed today")
        self._progress.setMaximum(goal)
        self._progress.setValue(min(count, goal))

        # Clear existing deck tiles
        while self._grid.count():
            item = self._grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        decks = self.app.db.get_all_decks()
        if not decks:
            lbl = QLabel("No decks yet — create your first card!")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._grid.addWidget(lbl, 0, 0, 1, 3)
            return

        for i, deck in enumerate(decks):
            stats = self.app.db.get_deck_stats(deck.id)
            self._deck_tile(deck, stats, row=i // 3, col=i % 3)

    def _deck_tile(self, deck, stats, row, col):
        tile = QFrame()
        tile.setFrameShape(QFrame.Shape.StyledPanel)
        tile.setCursor(Qt.CursorShape.PointingHandCursor)
        layout = QVBoxLayout(tile)
        layout.setContentsMargins(12, 12, 12, 12)

        name_lbl = QLabel(deck.name)
        name_lbl.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(name_lbl)
        layout.addWidget(QLabel(f"{stats['card_count']} cards"))
        layout.addWidget(QLabel(f"Memory: {stats['avg_memory']:.0f}%"))

        tile.mousePressEvent = lambda _e, did=deck.id: self.app.show_deck(did)
        self._grid.addWidget(tile, row, col)
```

- [ ] **Step 2: Verify home screen loads**

```bash
.venv/bin/python main.py
```

Expected: window opens showing "Flashcards" title, settings button, goal bar, deck grid.

- [ ] **Step 3: Commit**

```bash
git add ui/home_screen.py
git commit -m "feat: port HomeScreen to PyQt6"
```

---

## Task 5: Port ui/settings_screen.py — Settings form

**Files:**
- Rewrite: `ui/settings_screen.py`

- [ ] **Step 1: Rewrite ui/settings_screen.py**

```python
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QSlider, QMessageBox, QFrame,
)
from PyQt6.QtCore import Qt
import data.database as db


class SettingsScreen(QWidget):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self._build()
        self._load()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        # ── Top bar ──────────────────────────────────────────────────────────
        top = QHBoxLayout()
        back_btn = QPushButton("← Back")
        back_btn.clicked.connect(self.app.show_home)
        top.addWidget(back_btn)
        title = QLabel("Settings")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        top.addWidget(title)
        top.addStretch()
        root.addLayout(top)

        # ── Form ─────────────────────────────────────────────────────────────
        form_frame = QFrame()
        form_frame.setFrameShape(QFrame.Shape.StyledPanel)
        from PyQt6.QtWidgets import QFormLayout
        form = QFormLayout(form_frame)
        form.setContentsMargins(16, 16, 16, 16)
        form.setSpacing(12)

        self._goal_edit = QLineEdit()
        self._goal_edit.setFixedWidth(100)
        form.addRow("Daily goal (cards):", self._goal_edit)

        self._notify_edit = QLineEdit()
        self._notify_edit.setFixedWidth(100)
        form.addRow("Notify at (HH:MM):", self._notify_edit)

        api_row = QHBoxLayout()
        self._api_edit = QLineEdit()
        self._api_edit.setFixedWidth(400)
        self._api_edit.setEchoMode(QLineEdit.EchoMode.Password)
        api_row.addWidget(self._api_edit)
        show_btn = QPushButton("Show")
        show_btn.setCheckable(True)
        show_btn.toggled.connect(
            lambda checked: self._api_edit.setEchoMode(
                QLineEdit.EchoMode.Normal if checked
                else QLineEdit.EchoMode.Password
            )
        )
        api_row.addWidget(show_btn)
        api_row.addStretch()
        form.addRow("Claude API key:", api_row)

        decay_row = QHBoxLayout()
        self._decay_slider = QSlider(Qt.Orientation.Horizontal)
        self._decay_slider.setRange(0, 200)   # 0.0–20.0 stored as tenths
        self._decay_slider.setFixedWidth(200)
        self._decay_label = QLabel("5.0")
        self._decay_slider.valueChanged.connect(
            lambda v: self._decay_label.setText(f"{v / 10:.1f}")
        )
        decay_row.addWidget(self._decay_slider)
        decay_row.addWidget(self._decay_label)
        decay_row.addStretch()
        form.addRow("Decay rate (pts/day):", decay_row)

        root.addWidget(form_frame)

        save_btn = QPushButton("Save Settings")
        save_btn.clicked.connect(self._save)
        root.addWidget(save_btn, alignment=Qt.AlignmentFlag.AlignRight)
        root.addStretch()

    def _load(self):
        settings = db.get_all_settings()
        self._goal_edit.setText(settings.get("daily_goal", "10"))
        self._notify_edit.setText(settings.get("notify_time", "09:00"))
        self._api_edit.setText(settings.get("claude_api_key", ""))
        decay = float(settings.get("decay_rate", "5.0"))
        self._decay_slider.setValue(int(decay * 10))
        self._decay_label.setText(f"{decay:.1f}")

    def _save(self):
        goal = self._goal_edit.text().strip()
        if goal and not goal.isdigit():
            QMessageBox.warning(self, "Validation",
                                "Daily goal must be a whole number.")
            return
        db.set_setting("daily_goal", goal)
        db.set_setting("notify_time", self._notify_edit.text().strip())
        db.set_setting("claude_api_key", self._api_edit.text().strip())
        db.set_setting("decay_rate",
                       f"{self._decay_slider.value() / 10:.1f}")
        QMessageBox.information(self, "Saved", "Settings saved.")
        self.app.show_home()
```

- [ ] **Step 2: Verify settings screen**

Click ⚙ Settings. Expected: form shows daily goal, notify time, API key masked, decay slider. Save navigates home.

- [ ] **Step 3: Commit**

```bash
git add ui/settings_screen.py
git commit -m "feat: port SettingsScreen to PyQt6"
```

---

## Task 6: Port ui/deck_screen.py — Deck view with card list

**Files:**
- Rewrite: `ui/deck_screen.py`

Note: `QDialog` is shown with `open()` (non-blocking) and results are handled via the
`accepted` signal. This replaces the blocking `dlg.exec()` call.

- [ ] **Step 1: Rewrite ui/deck_screen.py**

```python
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QScrollArea,
    QFrame, QDialog, QTextEdit, QCheckBox, QMessageBox,
    QDialogButtonBox, QInputDialog,
)
from PyQt6.QtCore import Qt
import data.database as db
from data.models import Card


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

        # ── Top bar ──────────────────────────────────────────────────────────
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
        root.addLayout(top)

        # ── Search bar ────────────────────────────────────────────────────────
        self._search = QLineEdit()
        self._search.setPlaceholderText("Search cards…")
        self._search.setFixedWidth(320)
        self._search.textChanged.connect(lambda _: self._load())
        root.addWidget(self._search)

        # ── Card list ─────────────────────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._list_container = QWidget()
        self._list_layout = QVBoxLayout(self._list_container)
        self._list_layout.setSpacing(4)
        self._list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll.setWidget(self._list_container)
        root.addWidget(scroll)

    def _update_title(self):
        for d in db.get_all_decks():
            if d.id == self._deck_id:
                self._title.setText(d.name)
                break

    def _load(self):
        query = self._search.text().lower()
        while self._list_layout.count():
            item = self._list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        cards    = db.get_cards_for_deck(self._deck_id)
        filtered = [c for c in cards
                    if query in c.front.lower() or query in c.back.lower()]

        if not filtered:
            lbl = QLabel("No cards found.")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._list_layout.addWidget(lbl)
            return

        for card in filtered:
            self._list_layout.addWidget(self._card_row(card))

    def _card_row(self, card: Card) -> QFrame:
        row = QFrame()
        row.setFrameShape(QFrame.Shape.StyledPanel)
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

        layout.addWidget(QLabel(f"Mem: {card.memory_level:.0f}%"))

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

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save |
            QDialogButtonBox.StandardButton.Cancel
        )

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
            db.update_card(card)
            dlg.accept()
            self._load()

        buttons.accepted.connect(_save)
        buttons.rejected.connect(dlg.reject)
        layout.addWidget(buttons)
        # Open as modal dialog; accepted/rejected handled via signals above
        dlg.open()

    def _delete_card(self, card: Card):
        reply = QMessageBox.question(
            self, "Delete card", f"Delete '{card.front}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            db.delete_card(card.id)
            self._load()

    def _rename_deck(self):
        name, ok = QInputDialog.getText(
            self, "Rename Deck", "New deck name:"
        )
        if ok and name.strip():
            db.rename_deck(self._deck_id, name.strip())
            self._update_title()
```

- [ ] **Step 2: Verify deck screen**

Click a deck tile. Expected: card list, search filters, edit/delete buttons work, rename dialog works.

- [ ] **Step 3: Commit**

```bash
git add ui/deck_screen.py
git commit -m "feat: port DeckScreen to PyQt6"
```

---

## Task 7: Port ui/create_screen.py — Create/import cards

**Files:**
- Rewrite: `ui/create_screen.py`

- [ ] **Step 1: Rewrite ui/create_screen.py**

```python
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTextEdit, QComboBox,
    QCheckBox, QScrollArea, QFrame, QLineEdit,
    QMessageBox, QFileDialog, QInputDialog,
)
from PyQt6.QtCore import Qt
import data.database as db
from data.models import Card


class CreateScreen(QWidget):
    def __init__(self, app, deck_id=None):
        super().__init__()
        self.app       = app
        self._deck_id  = deck_id
        self._deck_map = {}
        self._gen_rows: list[tuple] = []
        self._build()
        self._load_decks()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        # ── Header ────────────────────────────────────────────────────────────
        top = QHBoxLayout()
        back_btn = QPushButton("← Back")
        back_btn.clicked.connect(self.app.show_home)
        top.addWidget(back_btn)
        title = QLabel("New Card")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        top.addWidget(title)
        top.addStretch()
        root.addLayout(top)

        # ── Form ─────────────────────────────────────────────────────────────
        form_frame = QFrame()
        form_frame.setFrameShape(QFrame.Shape.StyledPanel)
        form_layout = QVBoxLayout(form_frame)
        form_layout.setContentsMargins(16, 16, 16, 16)
        form_layout.setSpacing(10)

        deck_row = QHBoxLayout()
        deck_row.addWidget(QLabel("Deck"))
        self._deck_combo = QComboBox()
        self._deck_combo.setFixedWidth(260)
        deck_row.addWidget(self._deck_combo)
        new_deck_btn = QPushButton("+ New Deck")
        new_deck_btn.clicked.connect(self._new_deck_dialog)
        deck_row.addWidget(new_deck_btn)
        deck_row.addStretch()
        form_layout.addLayout(deck_row)

        for attr, label in [("_front_box", "Front"), ("_back_box", "Back")]:
            row = QHBoxLayout()
            row.addWidget(QLabel(label))
            tb = QTextEdit()
            tb.setFixedHeight(70)
            row.addWidget(tb)
            form_layout.addLayout(row)
            setattr(self, attr, tb)

        self._quiz_cb = QCheckBox("Quiz card (user must type the answer)")
        form_layout.addWidget(self._quiz_cb)

        btn_row = QHBoxLayout()
        save_btn = QPushButton("Save Card")
        save_btn.clicked.connect(self._save_card)
        btn_row.addWidget(save_btn)
        scan_btn = QPushButton("📷 Scan")
        scan_btn.clicked.connect(self._scan_camera)
        btn_row.addWidget(scan_btn)
        pdf_btn = QPushButton("📄 Import PDF")
        pdf_btn.clicked.connect(self._import_pdf)
        btn_row.addWidget(pdf_btn)
        btn_row.addStretch()
        form_layout.addLayout(btn_row)

        root.addWidget(form_frame)

        # ── Generated cards review area ───────────────────────────────────────
        self._gen_label = QLabel("Generated cards — review before saving")
        self._gen_label.setStyleSheet("font-weight: bold;")
        self._gen_label.hide()
        root.addWidget(self._gen_label)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._gen_container = QWidget()
        self._gen_layout = QVBoxLayout(self._gen_container)
        self._gen_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll.setWidget(self._gen_container)
        self._gen_scroll = scroll
        self._gen_scroll.hide()
        root.addWidget(self._gen_scroll)

    def _load_decks(self):
        decks = db.get_all_decks()
        self._deck_map = {d.name: d.id for d in decks}
        self._deck_combo.clear()
        if decks:
            for d in decks:
                self._deck_combo.addItem(d.name)
            if self._deck_id is not None:
                for i, d in enumerate(decks):
                    if d.id == self._deck_id:
                        self._deck_combo.setCurrentIndex(i)
                        break
        else:
            self._deck_combo.addItem("(no decks — create one)")

    def _get_selected_deck_id(self):
        return self._deck_map.get(self._deck_combo.currentText())

    def _new_deck_dialog(self):
        name, ok = QInputDialog.getText(self, "New Deck", "Deck name:")
        if ok and name.strip():
            d = db.create_deck(name.strip())
            self._deck_map[d.name] = d.id
            self._deck_combo.addItem(d.name)
            self._deck_combo.setCurrentText(d.name)

    def _save_card(self):
        front   = self._front_box.toPlainText().strip()
        back    = self._back_box.toPlainText().strip()
        deck_id = self._get_selected_deck_id()
        if not front or not back:
            QMessageBox.warning(self, "Missing content",
                                "Both front and back are required.")
            return
        if deck_id is None:
            QMessageBox.warning(self, "No deck",
                                "Please select or create a deck first.")
            return
        db.create_card(Card(front=front, back=back,
                            is_quiz=self._quiz_cb.isChecked(),
                            deck_id=deck_id))
        self._front_box.clear()
        self._back_box.clear()
        QMessageBox.information(self, "Saved", "Card saved successfully!")

    def _scan_camera(self):
        deck_id = self._get_selected_deck_id()
        if deck_id is None:
            QMessageBox.warning(self, "No deck",
                                "Please select or create a deck first.")
            return
        try:
            image_bytes = self.app.scan.capture_from_camera()
            cards_data  = self.app.claude.generate_cards_from_image(image_bytes)
            self._show_generated_cards(cards_data, deck_id)
        except Exception as e:
            QMessageBox.critical(self, "Scan failed", str(e))

    def _import_pdf(self):
        deck_id = self._get_selected_deck_id()
        if deck_id is None:
            QMessageBox.warning(self, "No deck",
                                "Please select or create a deck first.")
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "Open PDF", "", "PDF files (*.pdf)"
        )
        if not path:
            return
        try:
            text       = self.app.scan.extract_text_from_pdf(path)
            cards_data = self.app.claude.generate_cards_from_text(text)
            self._show_generated_cards(cards_data, deck_id)
        except Exception as e:
            QMessageBox.critical(self, "Import failed", str(e))

    def _show_generated_cards(self, cards_data: list, deck_id: int):
        while self._gen_layout.count():
            item = self._gen_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._gen_rows = []

        for cd in cards_data:
            row_frame = QFrame()
            row_frame.setFrameShape(QFrame.Shape.StyledPanel)
            row_layout = QHBoxLayout(row_frame)
            front_e = QLineEdit(cd.get("front", ""))
            front_e.setFixedWidth(380)
            row_layout.addWidget(front_e)
            back_e = QLineEdit(cd.get("back", ""))
            back_e.setFixedWidth(380)
            row_layout.addWidget(back_e)
            quiz_cb = QCheckBox("Quiz")
            quiz_cb.setChecked(cd.get("is_quiz", False))
            row_layout.addWidget(quiz_cb)
            del_btn = QPushButton("✕")
            del_btn.setFixedSize(30, 30)
            del_btn.clicked.connect(
                lambda _checked, rf=row_frame: rf.deleteLater()
            )
            row_layout.addWidget(del_btn)
            self._gen_layout.addWidget(row_frame)
            self._gen_rows.append((front_e, back_e, quiz_cb, row_frame))

        save_all_btn = QPushButton("Save All Cards")
        save_all_btn.clicked.connect(lambda: self._save_generated(deck_id))
        self._gen_layout.addWidget(save_all_btn)
        self._gen_label.show()
        self._gen_scroll.show()

    def _save_generated(self, deck_id: int):
        saved = 0
        for front_e, back_e, quiz_cb, row_frame in self._gen_rows:
            if not row_frame.isVisible():
                continue
            front = front_e.text().strip()
            back  = back_e.text().strip()
            if front and back:
                db.create_card(Card(front=front, back=back,
                                    is_quiz=quiz_cb.isChecked(),
                                    deck_id=deck_id))
                saved += 1
        QMessageBox.information(self, "Saved",
                                f"{saved} cards saved to deck.")
        self._gen_label.hide()
        self._gen_scroll.hide()
```

- [ ] **Step 2: Verify create screen**

Click "+ New Card". Expected: deck dropdown, front/back areas, Save Card saves and clears fields, PDF import opens file dialog.

- [ ] **Step 3: Commit**

```bash
git add ui/create_screen.py
git commit -m "feat: port CreateScreen to PyQt6"
```

---

## Task 8: Port ui/review_screen.py — Card review with flip animation

**Files:**
- Rewrite: `ui/review_screen.py`

- [ ] **Step 1: Rewrite ui/review_screen.py**

```python
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QProgressBar, QLineEdit, QFrame,
    QGraphicsOpacityEffect,
)
from PyQt6.QtCore import (
    Qt, QThread, pyqtSignal, QTimer,
    QPropertyAnimation, QEasingCurve,
)
import data.database as db
from services.review_scheduler import (
    build_review_queue, answers_match, apply_memory_delta,
)


class _ExplanationWorker(QThread):
    """Fetches a Claude explanation off the main thread."""
    result = pyqtSignal(str)

    def __init__(self, claude, question: str, answer: str):
        super().__init__()
        self._claude   = claude
        self._question = question
        self._answer   = answer

    def run(self):
        try:
            text = self._claude.explain_answer(self._question, self._answer)
        except Exception as e:
            text = f"(Could not fetch explanation: {e})"
        self.result.emit(text)


class ReviewScreen(QWidget):
    def __init__(self, app):
        super().__init__()
        self.app            = app
        self._queue: list   = []
        self._index: int    = 0
        self._seen: set     = set()
        self._session_id    = None
        self._showing_front = True
        self._worker        = None
        self._anim_out      = None
        self._anim_in       = None
        self._build()
        self._start_session()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        # ── Top bar ──────────────────────────────────────────────────────────
        top = QHBoxLayout()
        home_btn = QPushButton("← Home")
        home_btn.clicked.connect(self._end_session)
        top.addWidget(home_btn)
        top.addStretch()
        self._progress_label = QLabel("")
        top.addWidget(self._progress_label)
        root.addLayout(top)

        # ── Memory bar ───────────────────────────────────────────────────────
        mem_row = QHBoxLayout()
        self._mem_label = QLabel("Memory: —")
        mem_row.addWidget(self._mem_label)
        mem_row.addStretch()
        self._mem_bar = QProgressBar()
        self._mem_bar.setFixedWidth(180)
        self._mem_bar.setTextVisible(False)
        mem_row.addWidget(self._mem_bar)
        root.addLayout(mem_row)

        # ── Card ─────────────────────────────────────────────────────────────
        card_area = QHBoxLayout()
        card_area.addStretch()

        self._card_frame = QFrame()
        self._card_frame.setFrameShape(QFrame.Shape.StyledPanel)
        self._card_frame.setFixedSize(600, 280)
        card_inner = QVBoxLayout(self._card_frame)
        card_inner.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._side_label = QLabel("FRONT")
        self._side_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._side_label.setStyleSheet("color: gray; font-size: 10px;")
        card_inner.addWidget(self._side_label)

        self._card_text = QLabel("")
        self._card_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._card_text.setWordWrap(True)
        self._card_text.setStyleSheet("font-size: 18px;")
        card_inner.addWidget(self._card_text, stretch=1)

        self._quiz_row = QWidget()
        quiz_layout = QHBoxLayout(self._quiz_row)
        quiz_layout.setContentsMargins(0, 0, 0, 0)
        self._quiz_entry = QLineEdit()
        self._quiz_entry.setPlaceholderText("Type your answer…")
        self._quiz_entry.setFixedWidth(440)
        self._quiz_entry.returnPressed.connect(self._submit_quiz)
        self._quiz_entry.textChanged.connect(self._on_quiz_entry_change)
        quiz_layout.addWidget(self._quiz_entry)
        quiz_layout.addStretch()
        self._quiz_row.hide()
        card_inner.addWidget(self._quiz_row)

        self._explanation = QLabel("")
        self._explanation.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._explanation.setWordWrap(True)
        self._explanation.setStyleSheet("color: gray; font-size: 12px;")
        card_inner.addWidget(self._explanation)

        card_area.addWidget(self._card_frame)
        card_area.addStretch()
        root.addLayout(card_area, stretch=1)

        # Opacity effect for flip animation
        self._opacity = QGraphicsOpacityEffect(self._card_frame)
        self._card_frame.setGraphicsEffect(self._opacity)

        # ── Navigation ───────────────────────────────────────────────────────
        nav = QHBoxLayout()
        self._prev_btn = QPushButton("← Previous")
        self._prev_btn.clicked.connect(self._go_prev)
        nav.addWidget(self._prev_btn)

        self._action_btn = QPushButton("Flip")
        self._action_btn.setFixedWidth(160)
        nav.addWidget(self._action_btn)

        self._next_btn = QPushButton("Next →")
        self._next_btn.clicked.connect(self._go_next)
        nav.addWidget(self._next_btn)
        nav.addStretch()
        root.addLayout(nav)

    # ── Session ───────────────────────────────────────────────────────────────

    def _start_session(self):
        decay = float(db.get_setting("decay_rate") or 5.0)
        self._queue = build_review_queue(db.get_all_cards(), decay_rate=decay)
        if not self._queue:
            self._card_text.setText("No cards yet!\nCreate some cards first.")
            self._action_btn.setEnabled(False)
            return
        session = db.create_session()
        self._session_id = session.id
        self._show_card()

    def _show_card(self):
        self._showing_front = True
        self._explanation.setText("")
        self._quiz_row.hide()
        card = self._queue[self._index]
        self._card_text.setText(card.front)
        self._card_text.setStyleSheet("font-size: 18px;")
        self._side_label.setText("FRONT")
        self._mem_label.setText(f"Memory: {card.memory_level:.0f}%")
        self._mem_bar.setMaximum(100)
        self._mem_bar.setValue(int(card.memory_level))
        self._progress_label.setText(
            f"{self._index + 1} / {len(self._queue)}"
        )
        self._prev_btn.setEnabled(self._index > 0)
        self._next_btn.setEnabled(self._index < len(self._queue) - 1)

        try:
            self._action_btn.clicked.disconnect()
        except TypeError:
            pass

        if card.is_quiz and card.id not in self._seen:
            self._action_btn.setText("Submit")
            self._action_btn.setEnabled(False)
            self._quiz_entry.clear()
            self._quiz_row.show()
        elif card.is_quiz and card.id in self._seen:
            self._action_btn.setText("Next →")
            self._action_btn.setEnabled(True)
            self._action_btn.clicked.connect(self._go_next)
        else:
            self._action_btn.setText("Flip")
            self._action_btn.setEnabled(True)
            self._action_btn.clicked.connect(self._flip)

    def _on_quiz_entry_change(self, text: str):
        enabled = bool(text.strip())
        self._action_btn.setEnabled(enabled)
        if enabled:
            try:
                self._action_btn.clicked.disconnect()
            except TypeError:
                pass
            self._action_btn.clicked.connect(self._submit_quiz)

    def _flip(self):
        card = self._queue[self._index]
        if self._showing_front:
            self._animate_flip(lambda: self._reveal_back(card))
        else:
            self._record_and_advance(card, "seen")

    def _reveal_back(self, card):
        self._showing_front = False
        self._card_text.setText(card.back)
        self._side_label.setText("BACK")
        self._action_btn.setText("Next →")
        try:
            self._action_btn.clicked.disconnect()
        except TypeError:
            pass
        self._action_btn.clicked.connect(
            lambda: self._record_and_advance(card, "seen")
        )

    def _submit_quiz(self):
        card     = self._queue[self._index]
        user_ans = self._quiz_entry.text().strip()
        if not user_ans:
            return
        self._quiz_row.hide()
        if answers_match(user_ans, card.back):
            self._card_text.setStyleSheet("font-size: 18px; color: green;")
            self._card_text.setText(f"✓ Correct!\n\nAnswer: {card.back}")
            self._record_and_advance(card, "correct", delay_ms=1500)
        else:
            self._card_text.setStyleSheet("font-size: 18px; color: red;")
            self._card_text.setText(
                f"✗ Incorrect\n\nCorrect answer: {card.back}"
            )
            self._explanation.setText("Fetching explanation…")
            self._worker = _ExplanationWorker(
                self.app.claude, card.front, card.back
            )
            self._worker.result.connect(
                lambda text, c=card: self._on_explanation_ready(c, text)
            )
            self._worker.start()

    def _on_explanation_ready(self, card, explanation: str):
        self._explanation.setText(explanation)
        self._explanation.setStyleSheet("color: gray; font-size: 12px;")
        self._record_and_advance(card, "incorrect", delay_ms=4000)

    def _record_and_advance(self, card, result: str, delay_ms: int = 0):
        mem_before   = card.memory_level
        already_seen = card.id in self._seen
        new_level    = apply_memory_delta(card, result=result,
                                          already_seen=already_seen)
        self._seen.add(card.id)
        card.memory_level = new_level
        db.update_card_memory(card.id, new_level, datetime.now())
        if self._session_id:
            db.record_session_card_result(
                self._session_id, card.id, result,
                memory_before=mem_before, memory_after=new_level
            )
        if delay_ms:
            QTimer.singleShot(delay_ms, self._advance)
        else:
            self._advance()

    def _advance(self):
        self._card_text.setStyleSheet("font-size: 18px;")
        if self._index < len(self._queue) - 1:
            self._index += 1
            self._show_card()
        else:
            self._card_text.setText("Session complete! 🎉")
            self._action_btn.setEnabled(False)
            QTimer.singleShot(2000, self._end_session)

    def _go_prev(self):
        if self._index > 0:
            self._index -= 1
            self._show_card()

    def _go_next(self):
        if self._index < len(self._queue) - 1:
            self._index += 1
            self._show_card()

    def _end_session(self):
        if self._session_id:
            db.end_session(self._session_id, len(self._seen))
        self.app.show_home()

    # ── Flip animation ────────────────────────────────────────────────────────

    def _animate_flip(self, on_midpoint):
        """Fade card out, swap content at midpoint, fade back in."""
        fade_out = QPropertyAnimation(self._opacity, b"opacity")
        fade_out.setDuration(120)
        fade_out.setStartValue(1.0)
        fade_out.setEndValue(0.0)
        fade_out.setEasingCurve(QEasingCurve.Type.InQuad)

        def _swap_and_fade_in():
            on_midpoint()
            fade_in = QPropertyAnimation(self._opacity, b"opacity")
            fade_in.setDuration(120)
            fade_in.setStartValue(0.0)
            fade_in.setEndValue(1.0)
            fade_in.setEasingCurve(QEasingCurve.Type.OutQuad)
            fade_in.start()
            self._anim_in = fade_in

        fade_out.finished.connect(_swap_and_fade_in)
        fade_out.start()
        self._anim_out = fade_out
```

- [ ] **Step 2: Verify review screen**

Click "▶ Start Review". Expected: cards display, Flip fades and reveals back, quiz entry works, wrong answers trigger Claude explanation, session complete navigates home.

- [ ] **Step 3: Commit**

```bash
git add ui/review_screen.py
git commit -m "feat: port ReviewScreen to PyQt6 with QThread explanation worker"
```

---

## Task 9: Smoke test the full app

- [ ] **Step 1: Run the app and verify no crash**

```bash
.venv/bin/python main.py
```

Expected: window opens on macOS 12 without any `NSInvalidArgumentException`.

- [ ] **Step 2: Exercise all screens**

Manually verify each flow:
1. Home screen shows deck grid and daily goal progress bar
2. ⚙ Settings opens, values load from DB, Save writes to DB and returns home
3. "+ New Card" opens CreateScreen, deck dropdown populated, Save Card works
4. Clicking a deck tile opens DeckScreen with card list
5. Search in DeckScreen filters cards live
6. Edit card dialog opens, saves changes, list refreshes
7. Delete card shows confirmation then removes row
8. "▶ Start Review" shows cards, Flip animates, quiz entry enabled on typing
9. System light/dark mode toggle in macOS System Preferences is respected

- [ ] **Step 3: Clean up orphaned venvs and commit**

```bash
rm -rf .venv311
git add -A
git commit -m "chore: clean up venv311, complete PyQt6 migration"
```
