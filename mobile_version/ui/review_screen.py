import os
import random
import threading
from datetime import datetime

from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.graphics import Color, RoundedRectangle

from services.review_scheduler import (
    build_review_queue, answers_match, apply_memory_delta,
)
import data.database as db
from ui.theme import (
    apply_bg, btn, lbl,
    SURFACE, SECONDARY, SUCCESS, DANGER, MUTED, TEXT, PRIMARY,
    FONT_TITLE, FONT_BODY, FONT_SMALL,
    BTN_H, ROW_H, PAD, GAP, SPK_W, CJK_FONT,
)

# ── Speech ────────────────────────────────────────────────────────────────────
_VOICE_MAP = {'en': 'Samantha', 'zh': 'Ting-Ting'}
_CJK_RANGE = range(0x4E00, 0xA000)  # CJK Unified Ideographs block

def _detect_lang(text: str) -> str:
    """Return 'zh' if text contains CJK characters, else 'en'."""
    return 'zh' if any(ord(c) in _CJK_RANGE for c in text) else 'en'

def _first_line(text: str) -> str:
    for line in text.splitlines():
        if line.strip():
            return line.strip()
    return text.strip()


def _speak(text: str, lang: str = 'en'):
    word = _first_line(text)
    if not word:
        return
    def _run():
        if os.environ.get('ANDROID_ARGUMENT'):
            try:
                from plyer import tts
                tts.speak(word)
            except Exception:
                pass
        else:
            import subprocess
            voice = _VOICE_MAP.get(lang, 'Samantha')
            try:
                subprocess.Popen(['say', '-v', voice, word])
            except Exception:
                pass
    threading.Thread(target=_run, daemon=True).start()


# ── Card panel ────────────────────────────────────────────────────────────────
def _card_panel():
    ref = {}
    panel = BoxLayout(orientation='vertical', padding=16, spacing=8)
    with panel.canvas.before:
        ref['c'] = Color(*SURFACE)
        ref['r'] = RoundedRectangle(pos=panel.pos, size=panel.size, radius=[18])
    panel.bind(pos=lambda w, _: setattr(ref['r'], 'pos', w.pos))
    panel.bind(size=lambda w, _: setattr(ref['r'], 'size', w.size))
    return panel


# ── Line height constant (scales with FONT_BODY ≈ 22sp) ──────────────────────
from kivy.metrics import sp
LINE_H = sp(52)   # minimum height per line row, scales with font size


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
        self._quiz_mode = False
        self._wrapper = None
        self._review_root = None
        self._complete_root = None
        self._build()

    # ── Build ─────────────────────────────────────────────────────────────────

    def _build(self):
        apply_bg(self)
        self._wrapper = BoxLayout(orientation='vertical')
        self._review_root = self._build_review()
        self._complete_root = self._build_complete()
        self._wrapper.add_widget(self._review_root)
        self.add_widget(self._wrapper)

    def _build_review(self):
        root = BoxLayout(orientation='vertical', padding=PAD, spacing=GAP)

        # ── Header ──────────────────────────────────────────────────────────
        header = BoxLayout(size_hint_y=None, height=ROW_H, spacing=10)
        home_btn = btn('Home', color=SECONDARY, height=ROW_H)
        home_btn.size_hint_x = 0.28
        home_btn.bind(on_press=lambda _: self._end_session(go_home=True))
        header.add_widget(home_btn)

        self._progress_label = lbl('', font_size=FONT_SMALL, color=MUTED,
                                    height=ROW_H, halign='center')
        header.add_widget(self._progress_label)

        # Placeholder to balance header (was Speak button)
        header.add_widget(Widget(size_hint_x=0.28))
        root.add_widget(header)

        # ── Side badge ───────────────────────────────────────────────────────
        self._side_label = lbl('FRONT', font_size=FONT_SMALL, color=MUTED,
                                height=32, halign='center')
        root.add_widget(self._side_label)

        # ── Card panel with per-line content ─────────────────────────────────
        panel = _card_panel()
        panel.size_hint_y = 1

        card_scroll = ScrollView(do_scroll_x=False)
        self._card_content = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            spacing=6,
            padding=[0, 4],
        )
        self._card_content.bind(minimum_height=self._card_content.setter('height'))
        card_scroll.add_widget(self._card_content)
        panel.add_widget(card_scroll)
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
            font_name=CJK_FONT,
        )
        self._quiz_input.opacity = 0
        self._quiz_input.disabled = True
        self._quiz_input.height = 0   # collapsed; expanded to BTN_H when shown
        root.add_widget(self._quiz_input)

        # ── Nav — Prev | Flip/Submit | Next ──────────────────────────────────
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

        # ── Memory row — [-Mem] [Mem: XX%] [+Mem] ────────────────────────────
        MEM_H = BTN_H // 2
        mem_row = BoxLayout(size_hint_y=None, height=MEM_H, spacing=10)
        mem_down = btn('-Mem', color=SECONDARY, height=MEM_H)
        mem_down.bind(on_press=lambda _: self._adjust_memory(-10))
        mem_row.add_widget(mem_down)

        self._mem_label = lbl('', font_size=FONT_SMALL, color=MUTED,
                               height=MEM_H, halign='center')
        mem_row.add_widget(self._mem_label)

        mem_up = btn('+Mem', color=SECONDARY, height=MEM_H)
        mem_up.bind(on_press=lambda _: self._adjust_memory(10))
        mem_row.add_widget(mem_up)
        root.add_widget(mem_row)

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
        self._show_review_view()
        decay_rate = float(self.app.db.get_setting('decay_rate') or 5)
        all_cards = db.get_all_cards()
        self._queue = build_review_queue(all_cards, decay_rate)
        self._index = 0
        self._seen = set()
        self._correct = 0
        self._incorrect = 0

        if not self._queue:
            self._rebuild_card_lines(
                ['No cards to review yet.', 'Add some cards first!']
            )
            self._action_btn.disabled = True
            self._mem_label.text = ''
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
        if self._complete_root.parent is self._wrapper:
            self._wrapper.remove_widget(self._complete_root)
        if self._review_root.parent is not self._wrapper:
            self._wrapper.add_widget(self._review_root)

    def _show_complete_view(self):
        reviewed = len(self._seen)
        self._complete_count.text = f'{reviewed} card{"s" if reviewed != 1 else ""} reviewed'
        self._complete_correct.text = f'Correct: {self._correct}'
        self._complete_incorrect.text = f'Incorrect: {self._incorrect}'
        if self._review_root.parent is self._wrapper:
            self._wrapper.remove_widget(self._review_root)
        if self._complete_root.parent is not self._wrapper:
            self._wrapper.add_widget(self._complete_root)

    # ── Card content ──────────────────────────────────────────────────────────

    def _rebuild_card_lines(self, lines):
        """Replace card content with left-aligned per-line rows + speak buttons."""
        self._card_content.clear_widgets()
        for line in lines:
            if not line.strip():
                continue
            row = BoxLayout(size_hint_y=None, height=LINE_H, spacing=6)

            line_lbl = Label(
                text=line,
                halign='left',
                valign='middle',
                size_hint_x=1,
                size_hint_y=None,
                height=LINE_H,
                font_size=FONT_BODY,
                font_name=CJK_FONT,
                color=TEXT,
            )
            # Set text_size width when label width is known (enables wrapping)
            line_lbl.bind(
                width=lambda inst, w: setattr(inst, 'text_size', (max(0, w), None))
            )
            # Grow row height to fit wrapped text
            def _on_texture(inst, ts, r=row):
                new_h = max(int(ts[1]) + 12, LINE_H)
                inst.height = new_h
                r.height = new_h
            line_lbl.bind(texture_size=_on_texture)

            spk = Button(
                text='Spk',
                size_hint=(None, None),
                width=SPK_W,
                height=LINE_H,
                font_size=FONT_SMALL,
                bold=False,
                background_normal='',
                background_color=SECONDARY,
                color=TEXT,
            )
            # Keep speak button height in sync with the row
            row.bind(height=lambda _, h, b=spk: setattr(b, 'height', h))

            captured_line = line
            spk.bind(on_press=lambda _, t=captured_line: _speak(t, _detect_lang(t)))

            row.add_widget(line_lbl)
            row.add_widget(spk)
            self._card_content.add_widget(row)

    def _show_card(self):
        card = self._queue[self._index]
        self._showing_front = True
        self._quiz_mode = False

        self._feedback_label.text = ''
        self._quiz_input.text = ''
        self._quiz_input.opacity = 0
        self._quiz_input.disabled = True
        self._quiz_input.height = 0
        self._action_btn.disabled = False
        self._side_label.text = 'FRONT'
        self._progress_label.text = f'{self._index + 1} / {len(self._queue)}'
        self._update_mem_display(card)

        lines = [l for l in card.front.splitlines() if l.strip()]
        self._rebuild_card_lines(lines)

        # Determine mode
        if card.is_quiz and card.id not in self._seen:
            # Quiz card: show answer input immediately
            self._quiz_mode = True
            self._quiz_input.height = BTN_H
            self._quiz_input.opacity = 1
            self._quiz_input.disabled = False
            self._action_btn.text = 'Submit'
        else:
            # Dynamic quiz chance for regular cards (matches web logic)
            quiz_prob = 0.10 + (card.memory_level / 100) * 0.60
            if (not card.is_quiz
                    and card.id not in self._seen
                    and random.random() < quiz_prob):
                self._quiz_mode = True
                self._quiz_input.height = BTN_H
                self._quiz_input.opacity = 1
                self._quiz_input.disabled = False
                self._action_btn.text = 'Submit'
            else:
                self._action_btn.text = 'Flip'

    def _on_action(self):
        if self._action_btn.text == 'Flip':
            self._flip()
        elif self._action_btn.text == 'Submit':
            self._submit_quiz()

    def _flip(self):
        """Toggle between front and back."""
        card = self._queue[self._index]
        if self._showing_front:
            # Front → Back
            self._showing_front = False
            self._side_label.text = 'BACK'
            lines = [l for l in card.back.splitlines() if l.strip()]
            self._rebuild_card_lines(lines)
            # Record 'seen' on first reveal of back
            if card.id not in self._seen:
                already_seen = False
                self._seen.add(card.id)
                new_level = apply_memory_delta(card, 'seen', already_seen)
                self._record(card, 'seen', new_level)
            self._action_btn.text = 'Flip'   # can flip back
        else:
            # Back → Front (toggle back)
            self._showing_front = True
            self._side_label.text = 'FRONT'
            lines = [l for l in card.front.splitlines() if l.strip()]
            self._rebuild_card_lines(lines)
            self._action_btn.text = 'Flip'

    def _submit_quiz(self):
        card = self._queue[self._index]
        user_ans = self._quiz_input.text.strip()
        if not user_ans:
            return
        already_seen = card.id in self._seen
        self._seen.add(card.id)
        self._quiz_input.disabled = True
        self._quiz_input.opacity = 0
        self._quiz_input.height = 0

        if answers_match(user_ans, card.back):
            self._feedback_label.text = 'Correct!'
            self._feedback_label.color = SUCCESS
            self._correct += 1
            new_level = apply_memory_delta(card, 'correct', already_seen)
            self._record(card, 'correct', new_level)
        else:
            first_back = _first_line(card.back)
            self._feedback_label.text = f'Incorrect  —  {first_back}'
            self._feedback_label.color = DANGER
            self._incorrect += 1
            new_level = apply_memory_delta(card, 'incorrect', already_seen)
            self._record(card, 'incorrect', new_level)

        # Show back after quiz answer
        self._showing_front = False
        self._side_label.text = 'BACK'
        lines = [l for l in card.back.splitlines() if l.strip()]
        self._rebuild_card_lines(lines, lang='en')
        self._action_btn.text = 'Flip'
        self._update_mem_display(card)

    def _record(self, card, result, new_level):
        if self._session_id:
            db.record_session_card_result(
                self._session_id, card.id, result, card.memory_level, new_level
            )
        db.update_card_memory(card.id, new_level, datetime.now())
        card.memory_level = new_level

    # ── Navigation ────────────────────────────────────────────────────────────

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

    # ── Memory adjustment ─────────────────────────────────────────────────────

    def _adjust_memory(self, delta):
        if not self._queue:
            return
        card = self._queue[self._index]
        new_level = max(0.0, min(100.0, card.memory_level + delta))
        db.update_card_memory(card.id, new_level, datetime.now())
        card.memory_level = new_level
        self._update_mem_display(card)

    def _update_mem_display(self, card):
        self._mem_label.text = f'Mem: {card.memory_level:.0f}%'

    # ── Session end ───────────────────────────────────────────────────────────

    def _end_session(self, go_home=False):
        if self._session_id:
            db.end_session(self._session_id, len(self._seen))
            self._session_id = None
        if go_home:
            self.app.show_home()
        else:
            self._show_complete_view()
