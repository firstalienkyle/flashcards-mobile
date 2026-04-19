import random
import threading
from datetime import datetime
import re
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QProgressBar, QLineEdit, QFrame,
    QGraphicsOpacityEffect, QDialog, QScrollArea,
)
from PyQt5.QtCore import (
    Qt, QThread, pyqtSignal, QTimer,
    QPropertyAnimation, QEasingCurve,
)
import data.database as db
from services.review_scheduler import (
    build_review_queue, answers_match, apply_memory_delta,
)


_VOICE_MAP = {
    'en':    'Samantha',
    'es':    'Monica',
    'zh-cn': 'Ting-Ting',
    'zh-tw': 'Mei-Jia',
    'zh':    'Ting-Ting',
}

def _detect_lang(text: str) -> str:
    """Return language code, with CJK character check before langdetect."""
    if any('\u4e00' <= ch <= '\u9fff' for ch in text):
        return 'zh'
    try:
        from langdetect import detect
        return detect(text)
    except Exception:
        return 'en'

_OMW_LANG = {'en': 'eng', 'es': 'spa', 'zh': 'cmn', 'zh-cn': 'cmn', 'zh-tw': 'cmn'}


def _omw_terms(word: str) -> set:
    """Return semantically related terms via Open Multilingual Wordnet."""
    try:
        from nltk.corpus import wordnet as wn
        lang     = _detect_lang(word)
        omw_lang = _OMW_LANG.get(lang, 'eng')
        terms    = set()
        for syn in wn.synsets(word, lang=omw_lang)[:3]:
            for lg in ('eng', 'spa', 'cmn'):
                for lemma in syn.lemmas(lang=lg):
                    terms.add(lemma.name().lower().replace('_', ' '))
            for hyper in syn.hypernyms():
                for lg in ('eng', 'spa', 'cmn'):
                    for lemma in hyper.lemmas(lang=lg):
                        terms.add(lemma.name().lower().replace('_', ' '))
        terms.discard(word.lower())
        return terms
    except Exception:
        return set()


def _tokenise(word: str) -> list:
    """Split a word into searchable tokens.
    Handles space-separated words and individual CJK characters."""
    tokens = []
    for part in word.split():
        part_lower = part.lower()
        tokens.append(part_lower)
        # Also add individual Chinese characters as tokens
        for ch in part:
            if '\u4e00' <= ch <= '\u9fff':
                tokens.append(ch)
    return list(dict.fromkeys(tokens))  # deduplicate, preserve order


def _searchable(card) -> str:
    """Word (front line 1) + meanings (back after first 2 lines, no examples)."""
    front_word = card.front.splitlines()[0].strip() if card.front else ''
    meanings   = []
    for i, raw in enumerate(card.back.splitlines()):
        line = raw.strip()
        if not line or i < 2:
            continue
        if line[0] in '-•·–*"\'「':
            continue
        meanings.append(re.sub(r'^\d+[.)]\s*', '', line))
    return ' '.join([front_word] + meanings).lower()


def _extract_word(text: str) -> str:
    """Return only the first non-empty line (the word itself)."""
    for line in text.splitlines():
        line = line.strip()
        if line:
            return line
    return text.strip()


def _speak(text: str, slow: bool = False, lang: str = 'en') -> None:
    def _run():
        import subprocess
        word  = _extract_word(text)
        voice = _VOICE_MAP.get(lang, 'Samantha')
        rate  = ['-r', '250'] if not slow else ['-r', '160']
        try:
            subprocess.run(['say', '-v', voice] + rate + [word], check=False)
        except Exception:
            pass
    threading.Thread(target=_run, daemon=True).start()


class _ExplanationWorker(QThread):
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
        self._dynamic_quiz   = False   # flip card shown as quiz this turn
        self._quiz_ask_front = False   # True = showing back, asking for front
        self._play_counts: dict = {}   # card_id → number of times played
        self._build()
        self._start_session()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 8, 16, 16)
        root.setSpacing(8)

        # Top bar
        top = QHBoxLayout()
        home_btn = QPushButton("← Home")
        home_btn.clicked.connect(self._end_session)
        top.addWidget(home_btn)
        top.addStretch()
        self._progress_label = QLabel("")
        top.addWidget(self._progress_label)
        root.addLayout(top)

        # Card
        card_area = QHBoxLayout()
        card_area.addStretch()

        self._card_frame = QFrame()
        self._card_frame.setFrameShape(QFrame.StyledPanel)
        self._card_frame.setFixedWidth(600)
        self._card_frame.setMinimumHeight(320)
        self._card_frame.setStyleSheet("""
            QFrame {
                border-radius: 16px;
                border: 1px solid #d0d0d0;
                background: white;
            }
        """)
        self._card_frame.setCursor(Qt.PointingHandCursor)
        self._card_frame.mousePressEvent = lambda _e: self._on_card_click()
        card_inner = QVBoxLayout(self._card_frame)
        card_inner.setAlignment(Qt.AlignLeft | Qt.AlignTop)

        side_row = QHBoxLayout()
        self._side_label = QLabel("FRONT")
        self._side_label.setAlignment(Qt.AlignCenter)
        self._side_label.setStyleSheet("color: gray; font-size: 10px;")
        side_row.addWidget(self._side_label)
        side_row.addStretch()
        # Back-side global speak button (hidden on front — front has inline buttons)
        self._speak_btn = QPushButton("🔊")
        self._speak_btn.setFixedSize(28, 28)
        self._speak_btn.setStyleSheet("border: none; font-size: 16px;")
        self._speak_btn.clicked.connect(self._play_back_audio)
        side_row.addWidget(self._speak_btn)
        card_inner.addLayout(side_row)

        # Structured content area (word + quality + conjugations with inline buttons)
        self._content_widget = QWidget()
        self._content_layout = QVBoxLayout(self._content_widget)
        self._content_layout.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self._content_layout.setSpacing(4)
        card_inner.addWidget(self._content_widget, stretch=1)

        # Feedback label used only during quiz result display
        self._feedback_lbl = QLabel("")
        self._feedback_lbl.setAlignment(Qt.AlignCenter)
        self._feedback_lbl.setWordWrap(True)
        self._feedback_lbl.setStyleSheet("font-size: 18px;")
        self._feedback_lbl.hide()
        card_inner.addWidget(self._feedback_lbl, stretch=1)

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
        self._explanation.setAlignment(Qt.AlignCenter)
        self._explanation.setWordWrap(True)
        self._explanation.setStyleSheet("color: gray; font-size: 12px;")
        card_inner.addWidget(self._explanation)

        card_area.addWidget(self._card_frame)
        card_area.addStretch()
        root.addLayout(card_area)

        # Opacity effect for flip animation
        self._opacity = QGraphicsOpacityEffect(self._card_frame)
        self._card_frame.setGraphicsEffect(self._opacity)

        # Navigation
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

        related_btn = QPushButton("🔗 Related")
        related_btn.clicked.connect(self._show_related)
        nav.addWidget(related_btn)
        nav.addStretch()
        root.addStretch()
        root.addLayout(nav)

    def _start_session(self):
        self._queue = build_review_queue(db.get_all_cards(), decay_rate=3.0)
        if not self._queue:
            self._feedback_lbl.setText("No cards yet!\nCreate some cards first.")
            self._feedback_lbl.show()
            self._content_widget.hide()
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
        self._populate_content(card, 'front')
        self._side_label.setText("FRONT")
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
            self._dynamic_quiz = False
            self._action_btn.setText("Submit")
            self._action_btn.setEnabled(False)
            self._quiz_entry.clear()
            self._quiz_row.show()
        elif card.is_quiz and card.id in self._seen:
            self._dynamic_quiz = False
            self._action_btn.setText("Next →")
            self._action_btn.setEnabled(True)
            self._action_btn.clicked.connect(self._go_next)
        else:
            # Flip card: quiz probability scales with memory level
            # 0% memory → 5% quiz chance · 100% memory → 30% quiz chance
            quiz_prob = 0.05 + (card.memory_level / 100) * 0.25
            if card.id not in self._seen and random.random() < quiz_prob:
                self._dynamic_quiz   = True
                self._quiz_ask_front = random.random() < 0.5
                if self._quiz_ask_front:
                    # Show back, ask for front
                    self._showing_front = False
                    self._populate_content(card, 'back')
                    self._side_label.setText("BACK")
                else:
                    # Show front, ask for back (default)
                    self._populate_content(card, 'front')
                    self._side_label.setText("FRONT")
                self._action_btn.setText("Submit")
                self._action_btn.setEnabled(False)
                self._quiz_entry.clear()
                self._quiz_row.show()
            else:
                self._dynamic_quiz = False
                self._action_btn.setText("Flip")
                self._action_btn.setEnabled(True)
                self._action_btn.clicked.connect(self._flip)

    def _speak_line(self, text: str, card_id: int, lang: str = 'es'):
        count = self._play_counts.get(card_id, 0)
        slow  = (count % 2 == 1)
        self._play_counts[card_id] = count + 1
        _speak(text, slow=slow, lang=lang)

    def _play_back_audio(self):
        card = self._queue[self._index]
        self._speak_line(card.back, card.id, lang='en')

    def _populate_content(self, card, side: str):
        """Rebuild the card content area for the given side."""
        while self._content_layout.count():
            item = self._content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._feedback_lbl.hide()
        self._content_widget.show()

        if side == 'back':
            self._speak_btn.show()
            lbl = QLabel(card.back)
            lbl.setAlignment(Qt.AlignLeft | Qt.AlignTop)
            lbl.setWordWrap(True)
            lbl.setFixedWidth(560)
            lbl.setStyleSheet("font-size: 16px;")
            self._content_layout.addWidget(lbl)
            self._resize_card()
            return

        # Front: word (line 0) + quality (line 1) + conjugations (lines 2+)
        self._speak_btn.hide()
        lines = [l.strip() for l in card.front.splitlines() if l.strip()]
        for i, line in enumerate(lines):
            row_widget = QWidget()
            row        = QHBoxLayout(row_widget)
            row.setContentsMargins(0, 2, 0, 2)

            if i == 0:
                lbl = QLabel(line)
                lbl.setStyleSheet("font-size: 20px; font-weight: bold;")
            elif i == 1:
                lbl = QLabel(line)
                lbl.setStyleSheet("font-size: 13px; color: gray;")
            else:
                lbl = QLabel(line)
                lbl.setStyleSheet("font-size: 15px;")

            lbl.setWordWrap(True)
            row.addWidget(lbl)

            if i == 0:   # word only — inline 🔊
                spk = QPushButton("🔊")
                spk.setFixedSize(24, 24)
                spk.setStyleSheet("border: none; font-size: 13px;")
                spk.clicked.connect(
                    lambda _, t=line, cid=card.id: self._speak_line(t, cid, lang='es')
                )
                row.addWidget(spk)

            row.addStretch()
            self._content_layout.addWidget(row_widget)

        self._content_layout.addStretch()
        self._resize_card()

    def _resize_card(self):
        from PyQt5.QtWidgets import QApplication
        QApplication.processEvents()
        content_h = self._content_widget.sizeHint().height()
        new_h = max(320, content_h + 100)
        self._card_frame.setFixedHeight(new_h)

    def _on_quiz_entry_change(self, text: str):
        enabled = bool(text.strip())
        self._action_btn.setEnabled(enabled)
        if enabled:
            try:
                self._action_btn.clicked.disconnect()
            except TypeError:
                pass
            self._action_btn.clicked.connect(self._submit_quiz)

    def _on_card_click(self):
        """Clicking the card flips it — disabled when quiz input is active."""
        if not self._dynamic_quiz:
            card = self._queue[self._index]
            if not card.is_quiz or card.id in self._seen:
                self._flip()

    def _flip(self):
        card = self._queue[self._index]
        if self._showing_front:
            self._animate_flip(lambda: self._reveal_back(card))
        else:
            self._record_and_advance(card, "seen")

    def _reveal_back(self, card):
        self._showing_front = False
        self._populate_content(card, 'back')
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
        correct = card.front if self._quiz_ask_front else card.back
        self._content_widget.hide()
        self._feedback_lbl.show()
        if answers_match(user_ans, correct):
            self._feedback_lbl.setStyleSheet("font-size: 18px; color: green;")
            self._feedback_lbl.setText(f"✓ Correct!\n\nAnswer: {correct}")
            self._record_and_advance(card, "correct", delay_ms=1500)
        else:
            self._feedback_lbl.setStyleSheet("font-size: 18px; color: red;")
            self._feedback_lbl.setText(f"✗ Incorrect\n\nCorrect answer: {correct}")
            if self._dynamic_quiz:
                self._record_and_advance(card, "incorrect", delay_ms=2500)
            else:
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
        self._feedback_lbl.hide()
        self._content_widget.show()
        if self._index < len(self._queue) - 1:
            self._index += 1
            self._show_card()
        else:
            self._feedback_lbl.setStyleSheet("font-size: 18px;")
            self._feedback_lbl.setText("Session complete! 🎉")
            self._feedback_lbl.show()
            self._content_widget.hide()
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

    def _show_related(self):
        card      = self._queue[self._index]
        word      = card.front.splitlines()[0].strip()
        tokens    = _tokenise(word)
        omw       = _omw_terms(word)
        if not tokens and not omw:
            return

        all_cards = db.get_all_cards()
        related   = [
            c for c in all_cards
            if c.id != card.id and (
                any(t in _searchable(c) for t in tokens) or
                any(t in _searchable(c) for t in omw)
            )
        ]

        dlg = QDialog(self)
        dlg.setWindowTitle(f"Related to: {word}")
        dlg.resize(560, 420)
        dlg.setModal(True)
        outer = QVBoxLayout(dlg)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        layout    = QVBoxLayout(container)
        layout.setSpacing(6)
        scroll.setWidget(container)
        outer.addWidget(scroll)

        if not related:
            layout.addWidget(QLabel("No related cards found."))
        else:
            for c in related:
                row   = QFrame()
                row.setFrameShape(QFrame.StyledPanel)
                vbox  = QVBoxLayout(row)
                vbox.setContentsMargins(10, 8, 10, 8)
                front_lbl = QLabel(c.front.splitlines()[0])
                front_lbl.setStyleSheet("font-weight: bold; font-size: 14px;")
                vbox.addWidget(front_lbl)
                # Show meanings only (back lines after first two, skip examples)
                meanings = [
                    re.sub(r'^\d+[.)]\s*', '', ln.strip())
                    for i, ln in enumerate(c.back.splitlines())
                    if i >= 2 and ln.strip() and ln.strip()[0] not in '-•·–*"\'「'
                ]
                if meanings:
                    vbox.addWidget(QLabel('  ·  '.join(meanings[:3])))
                layout.addWidget(row)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dlg.accept)
        outer.addWidget(close_btn)
        dlg.exec_()

    def _end_session(self):
        if self._worker is not None and self._worker.isRunning():
            self._worker.quit()
            self._worker.wait()
        if self._session_id:
            db.end_session(self._session_id, len(self._seen))
        self.app.show_home()

    def _animate_flip(self, on_midpoint):
        fade_out = QPropertyAnimation(self._opacity, b"opacity")
        fade_out.setDuration(120)
        fade_out.setStartValue(1.0)
        fade_out.setEndValue(0.0)
        fade_out.setEasingCurve(QEasingCurve.InQuad)

        def _swap_and_fade_in():
            on_midpoint()
            fade_in = QPropertyAnimation(self._opacity, b"opacity")
            fade_in.setDuration(120)
            fade_in.setStartValue(0.0)
            fade_in.setEndValue(1.0)
            fade_in.setEasingCurve(QEasingCurve.OutQuad)
            fade_in.start()
            self._anim_in = fade_in

        fade_out.finished.connect(_swap_and_fade_in)
        fade_out.start()
        self._anim_out = fade_out
