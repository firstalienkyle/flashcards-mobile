import random
import threading
from datetime import datetime
import data.database as db
from services.review_scheduler import build_review_queue, answers_match, apply_memory_delta
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.label import Label
from kivy.graphics import Color, RoundedRectangle
from kivy.animation import Animation
from kivy.clock import Clock
from kivy.metrics import dp
from ui._widgets import btn, lbl, CARD, GREEN, RED, TEXT

try:
    from plyer import tts
except ImportError:
    tts = None


class ReviewScreen(Screen):
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app           = app
        self._queue: list  = []
        self._index: int   = 0
        self._seen: set    = set()
        self._session_id   = None
        self._showing_front = True
        self._dynamic_quiz  = False
        self._worker_thread = None
        self._build()
        self._start_session()

    # ── Layout ────────────────────────────────────────────────────────────────

    def _build(self):
        root = BoxLayout(orientation='vertical', padding=dp(12), spacing=dp(10))

        # Top bar
        top = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(52), spacing=dp(8))
        top.add_widget(btn('← Home', on_press=lambda _: self._end_session(),
                           size_hint_x=None, width=dp(90)))
        top.add_widget(BoxLayout())  # spacer
        self._progress_lbl = lbl('', size=14, halign='right')
        top.add_widget(self._progress_lbl)
        root.add_widget(top)

        # Card widget with rounded corners (drawn via canvas)
        self._card = BoxLayout(
            orientation='vertical',
            size_hint=(1, None),
            height=dp(340),
            padding=dp(20),
            spacing=dp(8),
        )
        with self._card.canvas.before:
            self._card_color = Color(*CARD)
            self._card_rect  = RoundedRectangle(
                pos=self._card.pos,
                size=self._card.size,
                radius=[dp(16)],
            )
        self._card.bind(pos=self._update_card_rect, size=self._update_card_rect)
        self._card.bind(on_touch_down=self._on_card_touch)

        self._side_lbl = lbl('FRONT', size=10, color=(0.5, 0.5, 0.5, 1), halign='center')
        self._card.add_widget(self._side_lbl)

        self._card_text = Label(
            text='',
            font_size=dp(20),
            color=TEXT,
            halign='center',
            valign='middle',
            markup=True,
        )
        self._card_text.bind(size=self._card_text.setter('text_size'))
        self._card.add_widget(self._card_text)

        self._speak_btn = btn('🔊', on_press=lambda _: self._speak_current(),
                              size_hint_x=None, width=dp(52), height=dp(42))
        self._speak_btn.opacity = 0
        self._speak_btn.disabled = True
        self._card.add_widget(self._speak_btn)

        # Quiz input (hidden by default)
        self._quiz_ti = TextInput(
            hint_text='Type your answer…',
            multiline=False,
            input_type='text',
            keyboard_suggestions=True,
            size_hint_y=None,
            height=dp(44),
            opacity=0,
            disabled=True,
        )
        self._quiz_ti.bind(on_text_validate=lambda _: self._submit_quiz())
        self._card.add_widget(self._quiz_ti)

        self._explanation_lbl = lbl('', size=12, color=(0.5, 0.5, 0.5, 1), halign='center')
        self._card.add_widget(self._explanation_lbl)

        root.add_widget(self._card)
        root.add_widget(BoxLayout())  # push nav to bottom

        # Navigation
        nav = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(52), spacing=dp(8))
        self._prev_btn = btn('← Prev', on_press=lambda _: self._go_prev(),
                             size_hint_x=None, width=dp(90))
        nav.add_widget(self._prev_btn)
        self._action_btn = btn('Flip', on_press=self._on_action,
                               size_hint_x=None, width=dp(140))
        nav.add_widget(self._action_btn)
        self._next_btn = btn('Next →', on_press=lambda _: self._go_next(),
                             size_hint_x=None, width=dp(90))
        nav.add_widget(self._next_btn)
        self._mem_up_btn = btn('✓', on_press=lambda _: self._set_memory(100),
                               size_hint_x=None, width=dp(52))
        nav.add_widget(self._mem_up_btn)
        self._mem_down_btn = btn('✕', on_press=lambda _: self._set_memory(0),
                                 size_hint_x=None, width=dp(52))
        nav.add_widget(self._mem_down_btn)
        nav.add_widget(BoxLayout())
        self._level_lbl = lbl('', size=12, halign='right')
        nav.add_widget(self._level_lbl)
        root.add_widget(nav)

        self.add_widget(root)

    def _update_card_rect(self, *_):
        self._card_rect.pos  = self._card.pos
        self._card_rect.size = self._card.size

    # ── Session ───────────────────────────────────────────────────────────────

    def _start_session(self):
        self._queue = build_review_queue(db.get_all_cards(), decay_rate=3.0)
        if not self._queue:
            self._card_text.text = 'No cards yet!\nCreate some cards first.'
            self._action_btn.disabled = True
            return
        session = db.create_session()
        self._session_id = session.id
        self._show_card()

    def _show_card(self):
        self._showing_front    = True
        self._explanation_lbl.text = ''
        self._card_text.color  = TEXT
        self._hide_quiz()

        card = self._queue[self._index]
        self._card_text.text = self._format_side_text(card.front)
        self._side_lbl.text  = 'FRONT'
        self._progress_lbl.text = f'{self._index + 1} / {len(self._queue)}'
        self._level_lbl.text = f'Mem {card.memory_level:.0f}%'
        self._prev_btn.disabled = (self._index == 0)
        self._next_btn.disabled = (self._index >= len(self._queue) - 1)

        if card.is_quiz and card.id not in self._seen:
            # Manual quiz cards are shown as questions until first success.
            self._dynamic_quiz = True
            self._quiz_direction = random.choice(('front_to_back', 'back_to_front'))
            self._set_quiz_prompt(card)
            self._action_btn.text     = 'Submit'
            self._action_btn.disabled = True
            self._quiz_ti.bind(text=self._on_quiz_text_change)
        elif card.is_quiz and card.id in self._seen:
            self._dynamic_quiz = False
            self._action_btn.text     = 'Next →'
            self._action_btn.disabled = False
        else:
            quiz_prob = card.memory_level / 100.0
            if card.id not in self._seen and random.random() < quiz_prob:
                self._dynamic_quiz = True
                self._quiz_direction = random.choice(('front_to_back', 'back_to_front'))
                self._set_quiz_prompt(card)
                self._action_btn.text     = 'Submit'
                self._action_btn.disabled = True
                self._quiz_ti.bind(text=self._on_quiz_text_change)
            else:
                self._dynamic_quiz = False
                self._action_btn.text     = 'Flip'
                self._action_btn.disabled = False

        self._update_speak_visibility(card)

    def _show_quiz(self):
        self._quiz_ti.text     = ''
        self._quiz_ti.opacity  = 1
        self._quiz_ti.disabled = False

    def _hide_quiz(self):
        self._quiz_ti.opacity  = 0
        self._quiz_ti.disabled = True
        try:
            self._quiz_ti.unbind(text=self._on_quiz_text_change)
        except Exception:
            pass

    def _set_quiz_prompt(self, card):
        self._show_quiz()
        if self._quiz_direction == 'front_to_back':
            self._card_text.text = self._format_side_text(card.front)
            self._quiz_answer = card.back
        else:
            self._card_text.text = self._format_side_text(card.back)
            self._quiz_answer = card.front
        self._side_lbl.text = 'QUIZ'

    def _format_side_text(self, text: str) -> str:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if len(lines) <= 1:
            if '|' in text:
                parts = [p.strip() for p in text.split('|') if p.strip()]
                if parts:
                    lines = parts
            elif ';' in text:
                parts = [p.strip() for p in text.split(';') if p.strip()]
                if parts:
                    lines = parts
        return '\n'.join(lines) if lines else text.strip()

    def _update_speak_visibility(self, card):
        can_speak = self._showing_front and not self._dynamic_quiz
        self._speak_btn.opacity = 1 if can_speak else 0
        self._speak_btn.disabled = not can_speak

    def _detect_text_language(self, text: str) -> str:
        if any('\u4e00' <= ch <= '\u9fff' for ch in text):
            return 'zh'
        return 'en'

    def _speak_current(self):
        if not hasattr(self, '_queue') or not self._queue:
            return
        card = self._queue[self._index]
        if not self._showing_front or self._dynamic_quiz:
            return
        text = card.front
        language = 'es'
        try:
            if tts is not None:
                try:
                    tts.speak(text, lang=language)
                except TypeError:
                    tts.speak(text)
            else:
                self._explanation_lbl.text = 'TTS unavailable on this device.'
        except Exception as e:
            self._explanation_lbl.text = f'Could not speak: {e}'

    def _set_memory(self, value: float):
        card = self._queue[self._index]
        mem_before = card.memory_level
        card.memory_level = float(value)
        db.set_card_memory_level(card.id, card.memory_level, datetime.now())
        if self._session_id:
            db.record_session_card_result(
                self._session_id, card.id, 'manual_adjust',
                memory_before=mem_before, memory_after=card.memory_level,
            )
        self._level_lbl.text = f'Mem {card.memory_level:.0f}%'
        self._explanation_lbl.text = f'Memory saved to {card.memory_level:.0f}%.'
        self._show_card()

    def _on_quiz_text_change(self, _, text):
        has_text = bool(text.strip())
        self._action_btn.disabled = not has_text

    # ── Card interaction ──────────────────────────────────────────────────────

    def _on_card_touch(self, widget, touch):
        if widget.collide_point(*touch.pos) and not self._dynamic_quiz:
            card = self._queue[self._index]
            if not card.is_quiz or card.id in self._seen:
                self._flip()
            return True

    def _on_action(self, _):
        if self._action_btn.text in ('Flip',):
            self._flip()
        elif self._action_btn.text == 'Submit':
            self._submit_quiz()
        elif self._action_btn.text == 'Next →':
            card = self._queue[self._index]
            self._record_and_advance(card, 'seen')

    def _flip(self):
        card = self._queue[self._index]
        if self._showing_front:
            self._animate_flip(lambda: self._reveal_back(card))
        else:
            self._record_and_advance(card, 'seen')

    def _reveal_back(self, card):
        self._showing_front    = False
        self._card_text.text   = self._format_side_text(card.back)
        self._side_lbl.text    = 'BACK'
        self._action_btn.text  = 'Next →'
        self._update_speak_visibility(card)

    def _submit_quiz(self):
        card     = self._queue[self._index]
        user_ans = self._quiz_ti.text.strip()
        if not user_ans:
            return
        self._hide_quiz()

        if answers_match(user_ans, self._quiz_answer):
            self._card_text.color = GREEN
            self._card_text.text  = f'✓ Correct!\n\nAnswer: {self._quiz_answer}'
            self._record_and_advance(card, 'correct', delay_s=1.5)
        else:
            self._card_text.color = RED
            self._card_text.text  = f'✗ Incorrect\n\nCorrect: {self._quiz_answer}'
            if self._dynamic_quiz:
                self._record_and_advance(card, 'incorrect', delay_s=2.5)
            else:
                self._explanation_lbl.text = 'Fetching explanation…'
                self._worker_thread = threading.Thread(
                    target=self._fetch_explanation,
                    args=(card,),
                    daemon=True,
                )
                self._worker_thread.start()

    def _fetch_explanation(self, card):
        try:
            text = self.app.claude.explain_answer(card.front, card.back)
        except Exception as e:
            text = f'(Could not fetch explanation: {e})'
        Clock.schedule_once(
            lambda _dt: self._on_explanation_ready(card, text)
        )

    def _on_explanation_ready(self, card, explanation: str):
        self._explanation_lbl.text = explanation
        self._record_and_advance(card, 'incorrect', delay_s=4.0)

    # ── Progress tracking ─────────────────────────────────────────────────────

    def _record_and_advance(self, card, result: str, delay_s: float = 0.0):
        mem_before   = card.memory_level
        already_seen = card.id in self._seen
        new_level    = apply_memory_delta(card, result=result, already_seen=already_seen)
        self._seen.add(card.id)
        card.memory_level = new_level
        db.update_card_memory(card.id, new_level, datetime.now())
        if self._session_id:
            db.record_session_card_result(
                self._session_id, card.id, result,
                memory_before=mem_before, memory_after=new_level,
            )
        if delay_s > 0:
            Clock.schedule_once(lambda _dt: self._advance(), delay_s)
        else:
            self._advance()

    def _advance(self):
        self._card_text.color = TEXT
        if self._index < len(self._queue) - 1:
            self._index += 1
            self._show_card()
        else:
            self._card_text.text      = 'Session complete! 🎉'
            self._action_btn.disabled = True
            Clock.schedule_once(lambda _dt: self._end_session(), 2.0)

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
        fade_out = Animation(opacity=0, duration=0.12)
        fade_in  = Animation(opacity=1, duration=0.12)

        def _midpoint(*_):
            on_midpoint()
            fade_in.start(self._card)

        fade_out.bind(on_complete=_midpoint)
        fade_out.start(self._card)
