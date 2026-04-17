import threading
from datetime import datetime
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.widget import Widget
from kivy.uix.textinput import TextInput
from kivy.graphics import Color, RoundedRectangle
from services.review_scheduler import (
    build_review_queue, answers_match, apply_memory_delta,
)
import data.database as db
from ui.theme import (
    apply_bg, btn, lbl,
    SURFACE, SECONDARY, SUCCESS, DANGER, MUTED, TEXT,
    FONT_TITLE, FONT_BODY, FONT_SMALL,
    BTN_H, ROW_H, PAD, GAP,
)


def _extract_word(text: str) -> str:
    for line in text.splitlines():
        line = line.strip()
        if line:
            return line
    return text.strip()


def _speak(text: str):
    def _run():
        try:
            from plyer import tts
            tts.speak(_extract_word(text))
        except Exception:
            pass
    threading.Thread(target=_run, daemon=True).start()


def _card_panel():
    ref = {}
    panel = BoxLayout(orientation='vertical', padding=28, spacing=12)
    with panel.canvas.before:
        ref['c'] = Color(*SURFACE)
        ref['r'] = RoundedRectangle(pos=panel.pos, size=panel.size, radius=[18])
    panel.bind(pos=lambda w, _: setattr(ref['r'], 'pos', w.pos))
    panel.bind(size=lambda w, _: setattr(ref['r'], 'size', w.size))
    return panel


class ReviewScreen(Screen):
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self._queue = []
        self._index = 0
        self._seen = set()
        self._correct = 0
        self._incorrect = 0
        self._session_id = None
        self._showing_front = True
        self._review_root = None
        self._complete_root = None
        self._build()

    # ── Build ─────────────────────────────────────────────────────────────────

    def _build(self):
        apply_bg(self)
        self._review_root = self._build_review()
        self._complete_root = self._build_complete()
        self._complete_root.opacity = 0
        self._complete_root.disabled = True

        # FloatLayout stacks children on top of each other — both fill full screen
        wrapper = FloatLayout()
        self._review_root.size_hint = (1, 1)
        self._review_root.pos_hint = {'x': 0, 'y': 0}
        self._complete_root.size_hint = (1, 1)
        self._complete_root.pos_hint = {'x': 0, 'y': 0}
        wrapper.add_widget(self._review_root)
        wrapper.add_widget(self._complete_root)
        self.add_widget(wrapper)

    def _build_review(self):
        root = BoxLayout(orientation='vertical', padding=PAD, spacing=GAP)

        # ── Header ───────────────────────────────────────────────────────────
        header = BoxLayout(size_hint_y=None, height=ROW_H, spacing=10)
        home_btn = btn('Home', color=SECONDARY, height=ROW_H)
        home_btn.size_hint_x = 0.28
        home_btn.bind(on_press=lambda _: self._end_session(go_home=True))
        header.add_widget(home_btn)

        self._progress_label = lbl('', font_size=FONT_SMALL, color=MUTED,
                                    height=ROW_H, halign='center')
        header.add_widget(self._progress_label)

        self._speak_btn = btn('Speak', color=SECONDARY, height=ROW_H)
        self._speak_btn.size_hint_x = 0.28
        self._speak_btn.bind(on_press=lambda _: self._play_audio())
        header.add_widget(self._speak_btn)
        root.add_widget(header)

        # ── Side badge ───────────────────────────────────────────────────────
        self._side_label = lbl('FRONT', font_size=FONT_SMALL, color=MUTED,
                                height=32, halign='center')
        root.add_widget(self._side_label)

        # ── Card panel — fills all remaining space ────────────────────────────
        panel = _card_panel()
        self._card_label = lbl('', font_size='26sp', bold=True,
                                halign='center', valign='middle')
        self._card_label.size_hint_y = 1
        self._card_label.bind(
            size=lambda inst, _: setattr(inst, 'text_size', (inst.width, None))
        )
        panel.add_widget(self._card_label)
        root.add_widget(panel)

        # ── Feedback ─────────────────────────────────────────────────────────
        self._feedback_label = lbl('', font_size=FONT_BODY, height=50,
                                    halign='center', bold=True)
        root.add_widget(self._feedback_label)

        # ── Quiz input ────────────────────────────────────────────────────────
        self._quiz_input = TextInput(
            hint_text='Type your answer...',
            size_hint_y=None, height=BTN_H,
            multiline=False,
            background_color=SURFACE,
            foreground_color=TEXT,
            font_size=FONT_BODY,
        )
        self._quiz_input.opacity = 0
        self._quiz_input.disabled = True
        root.add_widget(self._quiz_input)

        # ── Nav — three equal full-width buttons ──────────────────────────────
        nav = BoxLayout(size_hint_y=None, height=BTN_H, spacing=10)
        self._prev_btn = btn('Prev', color=SECONDARY)
        self._prev_btn.bind(on_press=lambda _: self._go_prev())
        nav.add_widget(self._prev_btn)

        self._action_btn = btn('Flip')
        self._action_btn.bind(on_press=lambda _: self._on_action())
        nav.add_widget(self._action_btn)

        self._next_btn = btn('Next', color=SECONDARY)
        self._next_btn.bind(on_press=lambda _: self._go_next())
        nav.add_widget(self._next_btn)
        root.add_widget(nav)

        return root

    def _build_complete(self):
        root = BoxLayout(orientation='vertical', padding=PAD * 2, spacing=GAP * 2)
        root.add_widget(Widget())

        root.add_widget(lbl('Session Complete', font_size='36sp', bold=True,
                             halign='center', height=70))

        self._complete_count = lbl('', font_size=FONT_TITLE, halign='center',
                                    color=MUTED, height=56)
        root.add_widget(self._complete_count)

        self._complete_correct = lbl('', font_size=FONT_BODY, halign='center',
                                      color=SUCCESS, height=48)
        root.add_widget(self._complete_correct)

        self._complete_incorrect = lbl('', font_size=FONT_BODY, halign='center',
                                        color=DANGER, height=48)
        root.add_widget(self._complete_incorrect)

        root.add_widget(Widget(size_hint_y=None, height=30))

        go_home = btn('Go Home')
        go_home.bind(on_press=lambda _: self.app.show_home())
        root.add_widget(go_home)

        review_again = btn('Review Again', color=SECONDARY)
        review_again.bind(on_press=lambda _: self._restart())
        root.add_widget(review_again)

        root.add_widget(Widget())
        return root

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def on_enter(self):
        self._start_session()

    def _start_session(self):
        decay_rate = float(self.app.db.get_setting('decay_rate') or 5)
        all_cards = db.get_all_cards()
        self._queue = build_review_queue(all_cards, decay_rate)
        self._index = 0
        self._seen = set()
        self._correct = 0
        self._incorrect = 0
        self._show_review_view()

        if not self._queue:
            self._card_label.text = 'No cards to review yet.\nAdd some cards first!'
            self._action_btn.disabled = True
            return

        self._session_id = db.create_session().id
        self._show_card()

    def _restart(self):
        if self._session_id:
            db.end_session(self._session_id, len(self._seen))
            self._session_id = None
        self._start_session()

    # ── View switching ────────────────────────────────────────────────────────

    def _show_review_view(self):
        self._review_root.opacity = 1
        self._review_root.disabled = False
        self._complete_root.opacity = 0
        self._complete_root.disabled = True

    def _show_complete_view(self):
        reviewed = len(self._seen)
        self._complete_count.text = f'{reviewed} card{"s" if reviewed != 1 else ""} reviewed'
        self._complete_correct.text = f'Correct: {self._correct}'
        self._complete_incorrect.text = f'Incorrect: {self._incorrect}'
        self._review_root.opacity = 0
        self._review_root.disabled = True
        self._complete_root.opacity = 1
        self._complete_root.disabled = False

    # ── Card display ──────────────────────────────────────────────────────────

    def _show_card(self):
        card = self._queue[self._index]
        self._showing_front = True
        self._side_label.text = 'FRONT'
        self._card_label.text = card.front
        self._feedback_label.text = ''
        self._quiz_input.text = ''
        self._quiz_input.opacity = 0
        self._quiz_input.disabled = True
        self._action_btn.text = 'Flip'
        self._action_btn.disabled = False
        self._progress_label.text = f'{self._index + 1} / {len(self._queue)}'

    def _on_action(self):
        if self._action_btn.text == 'Flip':
            self._flip()
        elif self._action_btn.text == 'Submit':
            self._submit_quiz()

    def _flip(self):
        card = self._queue[self._index]
        self._showing_front = False
        self._side_label.text = 'BACK'
        self._card_label.text = card.back

        if card.is_quiz:
            self._quiz_input.opacity = 1
            self._quiz_input.disabled = False
            self._action_btn.text = 'Submit'
        else:
            already_seen = card.id in self._seen
            self._seen.add(card.id)
            new_level = apply_memory_delta(card, 'seen', already_seen)
            self._record(card, 'seen', new_level)
            self._action_btn.text = 'Next'

    def _submit_quiz(self):
        card = self._queue[self._index]
        user_ans = self._quiz_input.text.strip()
        already_seen = card.id in self._seen
        self._seen.add(card.id)
        if answers_match(user_ans, card.back):
            self._feedback_label.text = 'Correct!'
            self._feedback_label.color = SUCCESS
            self._correct += 1
            new_level = apply_memory_delta(card, 'correct', already_seen)
            self._record(card, 'correct', new_level)
        else:
            self._feedback_label.text = f'Incorrect  -  {_extract_word(card.back)}'
            self._feedback_label.color = DANGER
            self._incorrect += 1
            new_level = apply_memory_delta(card, 'incorrect', already_seen)
            self._record(card, 'incorrect', new_level)
        self._quiz_input.disabled = True
        self._action_btn.text = 'Next'

    def _record(self, card, result, new_level):
        db.record_session_card_result(
            self._session_id, card.id, result, card.memory_level, new_level
        )
        db.update_card_memory(card.id, new_level, datetime.now())
        card.memory_level = new_level

    def _go_next(self):
        if self._index < len(self._queue) - 1:
            self._index += 1
            self._show_card()
        else:
            self._end_session(go_home=False)

    def _go_prev(self):
        if self._index > 0:
            self._index -= 1
            self._show_card()

    def _play_audio(self):
        card = self._queue[self._index]
        text = card.front if self._showing_front else card.back
        _speak(text)

    def _end_session(self, go_home=False):
        if self._session_id:
            db.end_session(self._session_id, len(self._seen))
            self._session_id = None
        if go_home:
            self.app.show_home()
        else:
            self._show_complete_view()
