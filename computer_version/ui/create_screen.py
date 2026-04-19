from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTextEdit, QComboBox,
    QCheckBox, QScrollArea, QFrame, QLineEdit,
    QMessageBox, QFileDialog, QInputDialog,
)
from PyQt5.QtCore import Qt
from data.models import Card


class CreateScreen(QWidget):
    def __init__(self, app, deck_id=None):
        super().__init__()
        self.app       = app
        self._deck_id  = deck_id
        self._deck_map = {}
        self._gen_rows: list = []
        self._build()
        self._load_decks()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        # Header
        top = QHBoxLayout()
        back_btn = QPushButton("← Back")
        back_btn.clicked.connect(self.app.show_home)
        top.addWidget(back_btn)
        title = QLabel("New Card")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        top.addWidget(title)
        top.addStretch()
        root.addLayout(top)

        # Form
        form_frame = QFrame()
        form_frame.setFrameShape(QFrame.StyledPanel)
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
        xlsx_btn = QPushButton("📊 Import Excel")
        xlsx_btn.clicked.connect(self._import_excel)
        btn_row.addWidget(xlsx_btn)
        txt_btn = QPushButton("📄 Import TXT")
        txt_btn.clicked.connect(self._import_txt)
        btn_row.addWidget(txt_btn)
        btn_row.addStretch()
        form_layout.addLayout(btn_row)

        root.addWidget(form_frame)

        # Import hint
        hint = QLabel(
            "Excel: column A = front, column B = back  |  "
            "TXT: front block, blank line, back block, blank line, repeat"
        )
        hint.setStyleSheet("color: gray; font-size: 11px;")
        root.addWidget(hint)

        # Generated cards area
        self._gen_label = QLabel("Imported cards — review before saving")
        self._gen_label.setStyleSheet("font-weight: bold;")
        self._gen_label.hide()
        root.addWidget(self._gen_label)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        self._gen_container = QWidget()
        self._gen_layout = QVBoxLayout(self._gen_container)
        self._gen_layout.setAlignment(Qt.AlignTop)
        scroll.setWidget(self._gen_container)
        self._gen_scroll = scroll
        self._gen_scroll.hide()
        root.addWidget(self._gen_scroll)

    # ── Deck helpers ──────────────────────────────────────────────────────────

    def _load_decks(self):
        decks = self.app.db.get_all_decks()
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
            d = self.app.db.create_deck(name.strip())
            self._deck_map[d.name] = d.id
            self._deck_combo.addItem(d.name)
            self._deck_combo.setCurrentText(d.name)

    # ── Manual card save ──────────────────────────────────────────────────────

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
        self.app.db.create_card(Card(front=front, back=back,
                                     is_quiz=self._quiz_cb.isChecked(),
                                     deck_id=deck_id))
        self._front_box.clear()
        self._back_box.clear()
        QMessageBox.information(self, "Saved", "Card saved successfully!")

    # ── Import: Excel ─────────────────────────────────────────────────────────

    def _import_excel(self):
        deck_id = self._get_selected_deck_id()
        if deck_id is None:
            QMessageBox.warning(self, "No deck", "Please select or create a deck first.")
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Excel", "", "Excel files (*.xlsx *.xls)"
        )
        if not path:
            return
        try:
            import openpyxl
            wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
            ws = wb.active
            cards_data = []
            for row in ws.iter_rows(values_only=True):
                cells = [str(c).strip() if c is not None else "" for c in row]
                front = cells[0] if len(cells) > 0 else ""
                back  = cells[1] if len(cells) > 1 else ""
                if not front or not back:
                    continue
                cards_data.append({"front": front, "back": back, "is_quiz": False})
            wb.close()
            if not cards_data:
                QMessageBox.warning(self, "Nothing found",
                                    "No valid rows found.\n"
                                    "Expected: column A = front, column B = back")
                return
            existing = {
                c.front.strip().lower()
                for c in self.app.db.get_cards_for_deck(deck_id)
            }
            unique = [cd for cd in cards_data
                      if cd["front"].strip().lower() not in existing]
            dupes = len(cards_data) - len(unique)
            if dupes:
                QMessageBox.information(
                    self, "Duplicates removed",
                    f"{dupes} duplicate card(s) skipped (same front as existing cards)."
                )
            if not unique:
                return
            self._show_generated_cards(unique, deck_id)
        except Exception as e:
            QMessageBox.critical(self, "Import failed", str(e))

    # ── Import: TXT ───────────────────────────────────────────────────────────

    def _import_txt(self):
        deck_id = self._get_selected_deck_id()
        if deck_id is None:
            QMessageBox.warning(self, "No deck", "Please select or create a deck first.")
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Text File", "", "Text files (*.txt)"
        )
        if not path:
            return
        try:
            with open(path, encoding="utf-8") as f:
                text = f.read()

            # Split into non-empty blocks separated by blank lines
            blocks = [b.strip() for b in text.split("\n\n") if b.strip()]

            if len(blocks) < 2:
                QMessageBox.warning(self, "Nothing found",
                                    "No card pairs found.\n"
                                    "Expected: front block, blank line, back block, blank line, repeat.")
                return

            cards_data = []
            for i in range(0, len(blocks) - 1, 2):
                front = blocks[i]
                back  = blocks[i + 1]
                cards_data.append({"front": front, "back": back, "is_quiz": False})

            existing = {
                c.front.strip().lower()
                for c in self.app.db.get_cards_for_deck(deck_id)
            }
            unique = [cd for cd in cards_data
                      if cd["front"].strip().lower() not in existing]
            dupes = len(cards_data) - len(unique)
            if dupes:
                QMessageBox.information(
                    self, "Duplicates removed",
                    f"{dupes} duplicate card(s) skipped (same front as existing cards)."
                )
            if not unique:
                return
            self._show_generated_cards(unique, deck_id)
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
            row_frame.setFrameShape(QFrame.StyledPanel)
            row_layout = QHBoxLayout(row_frame)
            front_e = QLineEdit(cd.get("front", ""))
            front_e.setFixedWidth(360)
            row_layout.addWidget(front_e)
            back_e = QLineEdit(cd.get("back", ""))
            back_e.setFixedWidth(360)
            row_layout.addWidget(back_e)
            quiz_cb = QCheckBox("Quiz")
            quiz_cb.setChecked(cd.get("is_quiz", False))
            row_layout.addWidget(quiz_cb)
            del_btn = QPushButton("✕")
            del_btn.setFixedSize(30, 30)
            del_btn.clicked.connect(
                lambda _checked, rf=row_frame: (rf.hide(), rf.deleteLater())
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
                self.app.db.create_card(Card(front=front, back=back,
                                             is_quiz=quiz_cb.isChecked(),
                                             deck_id=deck_id))
                saved += 1
        QMessageBox.information(self, "Saved", f"{saved} cards saved to deck.")
        self._gen_label.hide()
        self._gen_scroll.hide()
