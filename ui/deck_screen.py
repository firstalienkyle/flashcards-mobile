from tkinter import messagebox
import customtkinter as ctk
from config import (ACCENT, BG_CARD, BG_DARK, BG_INPUT, TEXT_PRIMARY, TEXT_MUTED,
                    CORNER_R, PADDING, FONT_FAMILY, COLOR_RED)
import data.database as db
from data.models import Card

class DeckScreen(ctk.CTkFrame):
    def __init__(self, app, deck_id: int):
        super().__init__(app, fg_color=BG_DARK, corner_radius=0)
        self.app      = app
        self._deck_id = deck_id
        self._build()
        self._update_title()
        self._load()

    def _build(self):
        top = ctk.CTkFrame(self, fg_color=BG_DARK)
        top.pack(fill="x", padx=PADDING, pady=(PADDING, 0))

        ctk.CTkButton(top, text="← Back", width=80, fg_color=BG_CARD,
                      hover_color=ACCENT, corner_radius=CORNER_R,
                      command=self.app.show_home).pack(side="left")

        self._title = ctk.CTkLabel(top, text="",
                                   font=ctk.CTkFont(FONT_FAMILY, 20, "bold"),
                                   text_color=TEXT_PRIMARY)
        self._title.pack(side="left", padx=12)

        ctk.CTkButton(top, text="✎ Rename", width=90, fg_color=BG_CARD,
                      hover_color=ACCENT, corner_radius=CORNER_R,
                      command=self._rename_deck).pack(side="right")

        ctk.CTkButton(top, text="+ Add Card", width=100, fg_color=ACCENT,
                      hover_color="#5a61e8", corner_radius=CORNER_R,
                      command=lambda: self.app.show_create(deck_id=self._deck_id)).pack(side="right", padx=(0, 8))

        # Search bar
        search_row = ctk.CTkFrame(self, fg_color=BG_DARK)
        search_row.pack(fill="x", padx=PADDING, pady=(10, 0))
        self._search_var = ctk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._load())
        ctk.CTkEntry(search_row, textvariable=self._search_var, width=320,
                     placeholder_text="Search cards…", fg_color=BG_INPUT,
                     corner_radius=8).pack(side="left")

        # Card list
        self._scroll = ctk.CTkScrollableFrame(self, fg_color=BG_DARK, corner_radius=0)
        self._scroll.pack(fill="both", expand=True, padx=PADDING, pady=PADDING)

    def _update_title(self):
        for d in db.get_all_decks():
            if d.id == self._deck_id:
                self._title.configure(text=d.name)
                break

    def _load(self):
        query = self._search_var.get().lower()
        for w in self._scroll.winfo_children():
            w.destroy()

        cards = db.get_cards_for_deck(self._deck_id)
        filtered = [c for c in cards if query in c.front.lower() or query in c.back.lower()]

        if not filtered:
            ctk.CTkLabel(self._scroll, text="No cards found.", text_color=TEXT_MUTED,
                         font=ctk.CTkFont(FONT_FAMILY, 14)).pack(pady=30)
            return

        for card in filtered:
            self._card_row(card)

    def _card_row(self, card: Card):
        row = ctk.CTkFrame(self._scroll, fg_color=BG_CARD, corner_radius=CORNER_R)
        row.pack(fill="x", pady=4)

        info = ctk.CTkFrame(row, fg_color="transparent")
        info.pack(side="left", fill="x", expand=True, padx=12, pady=8)

        tag = " [Quiz]" if card.is_quiz else ""
        ctk.CTkLabel(info, text=card.front + tag,
                     font=ctk.CTkFont(FONT_FAMILY, 13, "bold"),
                     text_color=TEXT_PRIMARY, anchor="w").pack(fill="x")
        ctk.CTkLabel(info, text=card.back,
                     font=ctk.CTkFont(FONT_FAMILY, 12),
                     text_color=TEXT_MUTED, anchor="w").pack(fill="x")

        mem_label = ctk.CTkLabel(row, text=f"Mem: {card.memory_level:.0f}%",
                                  font=ctk.CTkFont(FONT_FAMILY, 11), text_color=TEXT_MUTED)
        mem_label.pack(side="right", padx=12)

        ctk.CTkButton(row, text="✕", width=28, height=28, fg_color=COLOR_RED,
                      hover_color="#c0392b", corner_radius=6,
                      command=lambda c=card: self._delete_card(c)).pack(side="right", padx=(0, 8))

        ctk.CTkButton(row, text="✎", width=28, height=28, fg_color=BG_INPUT,
                      hover_color=ACCENT, corner_radius=6,
                      command=lambda c=card: self._edit_card(c)).pack(side="right")

    def _edit_card(self, card: Card):
        modal = ctk.CTkToplevel(self)
        modal.title("Edit Card")
        modal.geometry("560x320")
        modal.configure(fg_color=BG_DARK)
        modal.grab_set()

        boxes = {}
        for key, label, value in [
            ("front", "Front", card.front),
            ("back",  "Back",  card.back),
        ]:
            r = ctk.CTkFrame(modal, fg_color="transparent")
            r.pack(fill="x", padx=20, pady=(16 if key == "front" else 8, 0))
            ctk.CTkLabel(r, text=label, width=50, anchor="w",
                         font=ctk.CTkFont(FONT_FAMILY, 13), text_color=TEXT_MUTED).pack(side="left")
            tb = ctk.CTkTextbox(r, height=70, width=440, fg_color=BG_INPUT,
                                corner_radius=8, font=ctk.CTkFont(FONT_FAMILY, 13))
            tb.insert("1.0", value)
            tb.pack(side="left", padx=8)
            boxes[key] = tb

        quiz_var = ctk.BooleanVar(value=card.is_quiz)
        ctk.CTkCheckBox(modal, text="Quiz card", variable=quiz_var,
                        fg_color=ACCENT, checkmark_color="white",
                        font=ctk.CTkFont(FONT_FAMILY, 13),
                        text_color=TEXT_MUTED).pack(anchor="w", padx=72, pady=8)

        def save():
            front = boxes["front"].get("1.0", "end").strip()
            back  = boxes["back"].get("1.0", "end").strip()
            if not front or not back:
                messagebox.showwarning("Missing content", "Both front and back are required.")
                return
            card.front   = front
            card.back    = back
            card.is_quiz = quiz_var.get()
            db.update_card(card)
            modal.destroy()
            self._load()

        ctk.CTkButton(modal, text="Save", fg_color=ACCENT, hover_color="#5a61e8",
                      corner_radius=CORNER_R, command=save).pack(pady=12)

    def _delete_card(self, card: Card):
        if messagebox.askyesno("Delete card", f"Delete '{card.front}'?"):
            db.delete_card(card.id)
            self._load()

    def _rename_deck(self):
        dialog = ctk.CTkInputDialog(text="New deck name:", title="Rename Deck")
        name = dialog.get_input()
        if name and name.strip():
            db.rename_deck(self._deck_id, name.strip())
            self._update_title()
            self._load()
