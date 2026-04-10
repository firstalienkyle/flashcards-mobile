import customtkinter as ctk
from datetime import datetime
from config import (ACCENT, BG_CARD, BG_DARK, BG_INPUT, TEXT_PRIMARY, TEXT_MUTED,
                    CORNER_R, PADDING, FONT_FAMILY, COLOR_GREEN, COLOR_RED)
import data.database as db
from services.review_scheduler import build_review_queue, answers_match, apply_memory_delta

class ReviewScreen(ctk.CTkFrame):
    def __init__(self, app):
        super().__init__(app, fg_color=BG_DARK, corner_radius=0)
        self.app  = app
        self._queue: list    = []
        self._index: int     = 0
        self._seen: set      = set()    # card IDs seen this session
        self._session_id: int | None = None
        self._showing_front  = True
        self._animating      = False
        self._card_orig_w: int | None = None
        self._build()
        self._start_session()

    # ── Build UI ──────────────────────────────────────────────────────────────

    def _build(self):
        # Top bar
        top = ctk.CTkFrame(self, fg_color=BG_DARK)
        top.pack(fill="x", padx=PADDING, pady=(PADDING, 0))

        ctk.CTkButton(top, text="← Home", width=80, fg_color=BG_CARD,
                      hover_color=ACCENT, corner_radius=CORNER_R,
                      command=self._end_session).pack(side="left")

        self._progress_label = ctk.CTkLabel(top, text="",
                                            font=ctk.CTkFont(FONT_FAMILY, 13),
                                            text_color=TEXT_MUTED)
        self._progress_label.pack(side="right")

        # Memory bar
        mem_row = ctk.CTkFrame(self, fg_color=BG_DARK)
        mem_row.pack(fill="x", padx=PADDING, pady=(8, 0))
        self._mem_label = ctk.CTkLabel(mem_row, text="Memory: —",
                                       font=ctk.CTkFont(FONT_FAMILY, 12), text_color=TEXT_MUTED)
        self._mem_label.pack(side="left")
        self._mem_bar = ctk.CTkProgressBar(mem_row, width=180, height=8,
                                           progress_color=ACCENT, corner_radius=4)
        self._mem_bar.set(0.5)
        self._mem_bar.pack(side="right")

        # Card area
        card_container = ctk.CTkFrame(self, fg_color=BG_DARK)
        card_container.pack(fill="both", expand=True, padx=PADDING, pady=PADDING)

        self._card_frame = ctk.CTkFrame(card_container, fg_color=BG_CARD,
                                        corner_radius=20, width=600, height=280)
        self._card_frame.pack(expand=True)
        self._card_frame.pack_propagate(False)

        self._side_label = ctk.CTkLabel(self._card_frame, text="FRONT",
                                        font=ctk.CTkFont(FONT_FAMILY, 10),
                                        text_color=TEXT_MUTED)
        self._side_label.pack(pady=(16, 0))

        self._card_text = ctk.CTkLabel(self._card_frame, text="",
                                       font=ctk.CTkFont(FONT_FAMILY, 20),
                                       wraplength=520, text_color=TEXT_PRIMARY)
        self._card_text.pack(expand=True, padx=20)

        # Quiz input (hidden until needed)
        self._quiz_frame = ctk.CTkFrame(self._card_frame, fg_color="transparent")
        self._quiz_entry = ctk.CTkEntry(self._quiz_frame, width=440, height=36,
                                        fg_color=BG_INPUT, corner_radius=8,
                                        placeholder_text="Type your answer…")
        self._quiz_entry.pack(side="left", padx=(0, 8))
        ctk.CTkButton(self._quiz_frame, text="Submit", width=80, fg_color=ACCENT,
                      corner_radius=8, command=self._submit_quiz).pack(side="left")

        # Trace on quiz entry to enable action button when text is non-empty
        self._quiz_entry_var = ctk.StringVar()
        self._quiz_entry.configure(textvariable=self._quiz_entry_var)
        self._quiz_entry_var.trace_add("write", self._on_quiz_entry_change)

        # Explanation label (quiz wrong feedback)
        self._explanation = ctk.CTkLabel(self._card_frame, text="",
                                         font=ctk.CTkFont(FONT_FAMILY, 12),
                                         text_color=TEXT_MUTED, wraplength=520)
        self._explanation.pack(pady=(0, 8))

        # Bottom navigation
        nav = ctk.CTkFrame(self, fg_color=BG_DARK)
        nav.pack(fill="x", padx=PADDING, pady=(0, PADDING))

        self._prev_btn = ctk.CTkButton(nav, text="← Previous", width=120,
                                       fg_color=BG_CARD, hover_color=ACCENT,
                                       corner_radius=CORNER_R, command=self._go_prev)
        self._prev_btn.pack(side="left")

        self._action_btn = ctk.CTkButton(nav, text="Flip", width=160,
                                         fg_color=ACCENT, hover_color="#5a61e8",
                                         corner_radius=CORNER_R, command=self._flip)
        self._action_btn.pack(side="left", padx=8)

        self._next_btn = ctk.CTkButton(nav, text="Next →", width=120,
                                       fg_color=BG_CARD, hover_color=ACCENT,
                                       corner_radius=CORNER_R, command=self._go_next)
        self._next_btn.pack(side="left")

    # ── Session logic ─────────────────────────────────────────────────────────

    def _start_session(self):
        decay = float(db.get_setting("decay_rate"))
        cards = db.get_all_cards()
        self._queue = build_review_queue(cards, decay_rate=decay)

        if not self._queue:
            self._card_text.configure(text="No cards yet!\nCreate some cards first.")
            self._action_btn.configure(state="disabled")
            return

        session = db.create_session()
        self._session_id = session.id
        self._show_card()

    def _show_card(self):
        self._showing_front = True
        self._explanation.configure(text="")
        self._quiz_frame.pack_forget()
        card = self._queue[self._index]

        self._card_text.configure(text=card.front)
        self._side_label.configure(text="FRONT")
        self._mem_label.configure(text=f"Memory: {card.memory_level:.0f}%")
        self._mem_bar.set(card.memory_level / 100)
        self._progress_label.configure(
            text=f"{self._index + 1} / {len(self._queue)}"
        )
        self._prev_btn.configure(state="normal" if self._index > 0 else "disabled")

        if card.is_quiz:
            self._action_btn.configure(text="Submit", state="disabled")
            self._quiz_entry.delete(0, "end")
            self._quiz_frame.pack(pady=(0, 12))
            self._quiz_entry.bind("<Return>", lambda e: self._submit_quiz())
        else:
            self._action_btn.configure(text="Flip", state="normal",
                                       command=self._flip)

    def _on_quiz_entry_change(self, *_args):
        """Enable the Submit action button when the quiz entry has text."""
        if self._quiz_entry_var.get().strip():
            self._action_btn.configure(state="normal", command=self._submit_quiz)
        else:
            self._action_btn.configure(state="disabled")

    def _flip(self):
        """Animate card flip and reveal the back."""
        if self._animating:
            return
        card = self._queue[self._index]

        if self._showing_front:
            self._animate_flip(lambda: self._reveal_back(card))
        else:
            # Already flipped — advance
            self._record_and_advance(card, "seen")

    def _reveal_back(self, card):
        self._showing_front = False
        self._card_text.configure(text=card.back)
        self._side_label.configure(text="BACK")
        self._action_btn.configure(text="Next →", command=lambda: self._record_and_advance(card, "seen"))

    def _submit_quiz(self):
        card = self._queue[self._index]
        user_ans = self._quiz_entry.get().strip()
        if not user_ans:
            return

        self._quiz_frame.pack_forget()

        if answers_match(user_ans, card.back):
            self._card_text.configure(text=f"✓ Correct!\n\nAnswer: {card.back}",
                                      text_color=COLOR_GREEN)
            self._record_and_advance(card, "correct", delay_ms=1500)
        else:
            self._card_text.configure(text=f"✗ Incorrect\n\nCorrect answer: {card.back}",
                                      text_color=COLOR_RED)
            self._explanation.configure(text="Fetching explanation…")
            self.after(100, lambda: self._fetch_explanation(card, user_ans))

    def _fetch_explanation(self, card, _user_ans):
        try:
            explanation = self.app.claude.explain_answer(card.front, card.back)
        except Exception as e:
            explanation = f"(Could not fetch explanation: {e})"
        self._explanation.configure(text=explanation, text_color=TEXT_MUTED)
        self._record_and_advance(card, "incorrect", delay_ms=4000)

    def _record_and_advance(self, card, result: str, delay_ms: int = 0):
        mem_before       = card.memory_level   # captured BEFORE apply_memory_delta
        already_seen     = card.id in self._seen
        new_level        = apply_memory_delta(card, result=result, already_seen=already_seen)
        self._seen.add(card.id)
        card.memory_level = new_level

        db.update_card_memory(card.id, new_level, datetime.now())
        if self._session_id:
            db.record_session_card_result(
                self._session_id, card.id, result,
                memory_before=mem_before, memory_after=new_level
            )

        if delay_ms:
            self.after(delay_ms, self._advance)
        else:
            self._advance()

    def _advance(self):
        self._card_text.configure(text_color=TEXT_PRIMARY)
        if self._index < len(self._queue) - 1:
            self._index += 1
            self._show_card()
        else:
            self._card_text.configure(text="Session complete! 🎉")
            self._action_btn.configure(state="disabled")
            self.after(2000, self._end_session)

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
        """Fade card to black, call on_midpoint, fade back."""
        fade_out = ["#16213e", "#131827", "#100f15", "#080808", "#000000"]
        fade_in  = ["#080808", "#100f15", "#131827", "#16213e"]
        self._animating = True

        def step_out(i=0):
            if i < len(fade_out):
                self._card_frame.configure(fg_color=fade_out[i])
                self.after(25, lambda: step_out(i + 1))
            else:
                on_midpoint()
                step_in(0)

        def step_in(i=0):
            if i < len(fade_in):
                self._card_frame.configure(fg_color=fade_in[i])
                self.after(25, lambda: step_in(i + 1))
            else:
                self._card_frame.configure(fg_color=BG_CARD)
                self._animating = False

        step_out()
