import threading
from datetime import datetime
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget
from kivy.clock import Clock
from services.review_scheduler import (
    build_review_queue, answers_match, apply_memory_delta,
)
import data.database as db


def _extract_word(text: str) -> str:
    for line in text.splitlines():
        line = line.strip()
        if line:
            return line
    return text.strip()


def _speak(text: str, lang: str = 'en'):
    def _run():
        try:
            from plyer import tts
            tts.speak(_extract_word(text))
        except Exception:
            pass
    threading.Thread(target=_run, daemon=True).start()


class ReviewScreen(Screen):
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self._queue = []
        self._index = 0
        self._seen = set()
        self._session_id = None
        self._showing_front = True
        self._play_counts = {}
        self._build()

    def _build(self):
        root = BoxLayout(orientation='vertical', padding=16, spacing=10)

        top = BoxLayout(size_hint_y=None, height=48, spacing=8)
        home_btn = Button(text='← Home', size_hint_x=None, width=100)
        home_btn.bind(on_press=lambda _: self._end_session())
        top.add_widget(home_btn)
        top.add_widget(Widget())
        self._progress_label = Label(text='')
        top.add_widget(self._progress_label)
        root.add_widget(top)

        # Card area
        self._side_label = Label(text='FRONT', size_hint_y=None, height=24,
                                  color=(0.5, 0.5, 0.5, 1), font_size='11sp')
        root.add_widget(self._side_label)

        self._card_label = Label(text='', font_size='20sp', bold=True,
                                  size_hint_y=1, halign='left', valign='top',
                                  text_size=(None, None))
        self._card_label.bind(size=lambda inst, val: setattr(inst, 'text_size', (val[0], None)))
        root.add_widget(self._card_label)

        self._speak_btn = Button(text='🔊 Speak', size_hint_y=None, height=44,
                                  size_hint_x=None, width=120)
        self._speak_btn.bind(on_press=lambda _: self._play_audio())
        root.add_widget(self._speak_btn)

        self._quiz_input = TextInput(hint_text='Type your answer…', size_hint_y=None,
                                      height=44, multiline=False)
        self._quiz_input.opacity = 0
        self._quiz_input.disabled = True
        root.add_widget(self._quiz_input)

        self._feedback_label = Label(text='', size_hint_y=None, height=36,
                                      font_size='16sp')
        root.add_widget(self._feedback_label)

        self._explanation_label = Label(text='', size_hint_y=None, height=60,
                                         color=(0.5, 0.5, 0.5, 1), font_size='12sp',
                                         halign='left', valign='top')
        self._explanation_label.bind(size=lambda inst, val: setattr(inst, 'text_size', (val[0], None)))
        root.add_widget(self._explanation_label)

        # Nav buttons
        nav = BoxLayout(size_hint_y=None, height=52, spacing=8)
        self._prev_btn = Button(text='← Prev', size_hint_x=None, width=100)
        self._prev_btn.bind(on_press=lambda _: self._go_prev())
        nav.add_widget(self._prev_btn)

        self._action_btn = Button(text='Flip', size_hint_x=1)
        self._action_btn.bind(on_press=lambda _: self._on_action())
        nav.add_widget(self._action_btn)

        self._next_btn = Button(text='Next →', size_hint_x=None, width=100)
        self._next_btn.bind(on_press=lambda _: self._go_next())
        nav.add_widget(self._next_btn)
        root.add_widget(nav)

        self.add_widget(root)

    def on_enter(self):
        self._start_session()

    def _start_session(self):
        decay_rate = float(self.app.db.get_setting('decay_rate') or 5)
        all_cards = db.get_all_cards()
        self._queue = build_review_queue(all_cards, decay_rate)
        if not self._queue:
            self._card_label.text = 'No cards to review!'
            return
        self._index = 0
        self._seen = set()
        self._session_id = db.create_session().id
        self._show_card()

    def _show_card(self):
        card = self._queue[self._index]
        self._showing_front = True
        self._side_label.text = 'FRONT'
        self._card_label.text = card.front
        self._feedback_label.text = ''
        self._explanation_label.text = ''
        self._quiz_input.text = ''
        self._quiz_input.opacity = 0
        self._quiz_input.disabled = True
        self._action_btn.text = 'Flip'
        self._progress_label.text = f'{self._index + 1} / {len(self._queue)}'
        self._speak_btn.opacity = 1
        self._speak_btn.disabled = False

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
            self._action_btn.text = 'Next →'

    def _submit_quiz(self):
        card = self._queue[self._index]
        user_ans = self._quiz_input.text.strip()
        correct = card.back
        already_seen = card.id in self._seen
        self._seen.add(card.id)
        if answers_match(user_ans, correct):
            self._feedback_label.text = '✓ Correct!'
            self._feedback_label.color = (0.2, 0.8, 0.2, 1)
            new_level = apply_memory_delta(card, 'correct', already_seen)
            self._record(card, 'correct', new_level)
        else:
            self._feedback_label.text = f'✗ Incorrect — {_extract_word(correct)}'
            self._feedback_label.color = (0.9, 0.2, 0.2, 1)
            new_level = apply_memory_delta(card, 'incorrect', already_seen)
            self._record(card, 'incorrect', new_level)
            self._fetch_explanation(card)
        self._quiz_input.disabled = True
        self._action_btn.text = 'Next →'

    def _record(self, card, result, new_level):
        db.record_session_card_result(
            self._session_id, card.id, result, card.memory_level, new_level
        )
        db.update_card_memory(card.id, new_level, datetime.now())
        card.memory_level = new_level

    def _fetch_explanation(self, card):
        def _run():
            try:
                text = self.app.claude.explain_answer(card.front, card.back)
            except Exception:
                text = ''
            Clock.schedule_once(lambda dt: setattr(self._explanation_label, 'text', text))
        threading.Thread(target=_run, daemon=True).start()

    def _go_next(self):
        if self._index < len(self._queue) - 1:
            self._index += 1
            self._show_card()
        else:
            self._end_session()

    def _go_prev(self):
        if self._index > 0:
            self._index -= 1
            self._show_card()

    def _play_audio(self):
        card = self._queue[self._index]
        lang = 'es' if self._showing_front else 'en'
        text = card.front if self._showing_front else card.back
        _speak(text, lang=lang)

    def _end_session(self):
        if self._session_id:
            db.end_session(self._session_id, len(self._seen))
            self._session_id = None
        self.app.show_home()
