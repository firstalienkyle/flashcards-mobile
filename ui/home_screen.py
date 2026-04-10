import customtkinter as ctk
from config import (ACCENT, BG_CARD, BG_DARK, TEXT_PRIMARY, TEXT_MUTED,
                    CORNER_R, PADDING, FONT_FAMILY, COLOR_GREEN)

class HomeScreen(ctk.CTkFrame):
    def __init__(self, app):
        super().__init__(app, fg_color=BG_DARK, corner_radius=0)
        self.app = app
        self._build()
        self._load()

    def _build(self):
        # ── Top bar ──────────────────────────────────────────────────────────
        top = ctk.CTkFrame(self, fg_color=BG_DARK, corner_radius=0)
        top.pack(fill="x", padx=PADDING, pady=(PADDING, 0))

        ctk.CTkLabel(top, text="Flashcards", font=ctk.CTkFont(FONT_FAMILY, 24, "bold"),
                     text_color=TEXT_PRIMARY).pack(side="left")

        ctk.CTkButton(top, text="⚙ Settings", width=100, fg_color=BG_CARD,
                      hover_color=ACCENT, corner_radius=CORNER_R,
                      command=self.app.show_settings).pack(side="right")

        # ── Daily goal bar ────────────────────────────────────────────────────
        goal_frame = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=CORNER_R)
        goal_frame.pack(fill="x", padx=PADDING, pady=(12, 0))

        inner = ctk.CTkFrame(goal_frame, fg_color="transparent")
        inner.pack(fill="x", padx=PADDING, pady=10)

        self._goal_label = ctk.CTkLabel(inner, text="Loading...",
                                        font=ctk.CTkFont(FONT_FAMILY, 13),
                                        text_color=TEXT_MUTED)
        self._goal_label.pack(side="left")

        self._progress = ctk.CTkProgressBar(inner, width=220, height=10,
                                            progress_color=ACCENT, corner_radius=5)
        self._progress.set(0)
        self._progress.pack(side="right")

        # ── Action buttons ────────────────────────────────────────────────────
        btn_row = ctk.CTkFrame(self, fg_color=BG_DARK)
        btn_row.pack(fill="x", padx=PADDING, pady=(12, 0))

        for text, cmd in [
            ("▶  Start Review", self.app.show_review),
            ("+  New Card",     self.app.show_create),
            ("↑  Import",       self._open_import),
        ]:
            ctk.CTkButton(btn_row, text=text, height=40, fg_color=ACCENT,
                          hover_color="#5a61e8", corner_radius=CORNER_R,
                          font=ctk.CTkFont(FONT_FAMILY, 13, "bold"),
                          command=cmd).pack(side="left", padx=(0, 8))

        # ── Deck grid (scrollable) ────────────────────────────────────────────
        self._scroll = ctk.CTkScrollableFrame(self, fg_color=BG_DARK, corner_radius=0)
        self._scroll.pack(fill="both", expand=True, padx=PADDING, pady=PADDING)
        self._scroll.columnconfigure((0, 1, 2), weight=1)

    def _load(self):
        # Goal progress
        goal   = int(self.app.db.get_setting("daily_goal"))
        count  = self.app.db.get_today_reviewed_count()
        ratio  = min(1.0, count / max(goal, 1))
        self._goal_label.configure(text=f"{count} / {goal} cards reviewed today")
        self._progress.set(ratio)

        # Deck tiles
        for widget in self._scroll.winfo_children():
            widget.destroy()

        decks = self.app.db.get_all_decks()
        if not decks:
            ctk.CTkLabel(self._scroll, text="No decks yet — create your first card!",
                         text_color=TEXT_MUTED,
                         font=ctk.CTkFont(FONT_FAMILY, 14)).grid(row=0, column=0,
                                                                   columnspan=3, pady=40)
            return

        for i, deck in enumerate(decks):
            stats = self.app.db.get_deck_stats(deck.id)
            self._deck_tile(deck, stats, row=i // 3, col=i % 3)

    def _deck_tile(self, deck, stats, row, col):
        tile = ctk.CTkFrame(self._scroll, fg_color=BG_CARD, corner_radius=CORNER_R,
                            cursor="hand2")
        tile.grid(row=row, column=col, padx=6, pady=6, sticky="nsew")

        ctk.CTkLabel(tile, text=deck.name, font=ctk.CTkFont(FONT_FAMILY, 15, "bold"),
                     text_color=TEXT_PRIMARY).pack(anchor="w", padx=12, pady=(12, 4))

        ctk.CTkLabel(tile, text=f"{stats['card_count']} cards",
                     font=ctk.CTkFont(FONT_FAMILY, 12), text_color=TEXT_MUTED).pack(anchor="w", padx=12)

        mem_color = COLOR_GREEN if stats["avg_memory"] >= 60 else ACCENT
        ctk.CTkLabel(tile, text=f"Memory: {stats['avg_memory']:.0f}%",
                     font=ctk.CTkFont(FONT_FAMILY, 12),
                     text_color=mem_color).pack(anchor="w", padx=12, pady=(0, 12))

        tile.bind("<Button-1>", lambda e, did=deck.id: self.app.show_deck(did))
        for child in tile.winfo_children():
            child.bind("<Button-1>", lambda e, did=deck.id: self.app.show_deck(did))

    def _open_import(self):
        from ui.create_screen import CreateScreen
        self.app.show_create()
