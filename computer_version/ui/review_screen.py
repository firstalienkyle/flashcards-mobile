import random
from datetime import datetime
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QProgressBar, QLineEdit, QFrame,
    QGraphicsOpacityEffect,
)
from PyQt5.QtCore import (
    Qt, QThread, pyqtSignal, QTimer,
    QPropertyAnimation, QEasingCurve,
)
import data.database as db
from computer_version.services.review_scheduler import (
    build_review_queue, answers_match, apply_memory_delta,
)


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
        self._dynamic_quiz  = False   # flip card shown as quiz this turn
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
        self._card_frame.setFixedSize(600, 320)
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
        card_inner.setAlignment(Qt.AlignCenter)

        self._side_label = QLabel("FRONT")
        self._side_label.setAlignment(Qt.AlignCenter)
        self._side_label.setStyleSheet("color: gray; font-size: 10px;")
        card_inner.addWidget(self._side_label)

        self._card_text = QLabel("")
        self._card_text.setAlignment(Qt.AlignCenter)
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
        nav.addStretch()
        root.addStretch()
        root.addLayout(nav)

    def _start_session(self):
        self._queue = build_review_queue(db.get_all_cards(), decay_rate=3.0)
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
                self._dynamic_quiz = True
                self._action_btn.setText("Submit")
                self._action_btn.setEnabled(False)
                self._quiz_entry.clear()
                self._quiz_row.show()
            else:
                self._dynamic_quiz = False
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
