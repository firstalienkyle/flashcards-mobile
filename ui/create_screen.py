from tkinter import filedialog, messagebox
import customtkinter as ctk
from config import (ACCENT, BG_CARD, BG_DARK, BG_INPUT, TEXT_PRIMARY, TEXT_MUTED,
                    CORNER_R, PADDING, FONT_FAMILY, COLOR_RED)
import data.database as db
from data.models import Card

class CreateScreen(ctk.CTkFrame):
    def __init__(self, app, deck_id: int | None = None):
        super().__init__(app, fg_color=BG_DARK, corner_radius=0)
        self.app        = app
        self._deck_id   = deck_id
        self._deck_map  = {}
        self._gen_entries: list[tuple] = []
        self._build()
        self._load_decks()

    def _build(self):
        # Header
        top = ctk.CTkFrame(self, fg_color=BG_DARK)
        top.pack(fill="x", padx=PADDING, pady=(PADDING, 0))
        ctk.CTkButton(top, text="← Back", width=80, fg_color=BG_CARD,
                      hover_color=ACCENT, corner_radius=CORNER_R,
                      command=self.app.show_home).pack(side="left")
        ctk.CTkLabel(top, text="New Card", font=ctk.CTkFont(FONT_FAMILY, 20, "bold"),
                     text_color=TEXT_PRIMARY).pack(side="left", padx=12)

        form = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=CORNER_R)
        form.pack(fill="x", padx=PADDING, pady=PADDING)

        # Deck selector
        row = ctk.CTkFrame(form, fg_color="transparent")
        row.pack(fill="x", padx=PADDING, pady=(PADDING, 0))
        ctk.CTkLabel(row, text="Deck", font=ctk.CTkFont(FONT_FAMILY, 13),
                     text_color=TEXT_MUTED, width=60, anchor="w").pack(side="left")
        self._deck_var = ctk.StringVar(value="")
        self._deck_menu = ctk.CTkOptionMenu(row, variable=self._deck_var, width=260,
                                            fg_color=BG_INPUT, button_color=ACCENT)
        self._deck_menu.pack(side="left", padx=(8, 0))
        ctk.CTkButton(row, text="+ New Deck", width=90, fg_color="transparent",
                      text_color=ACCENT, hover_color=BG_INPUT,
                      command=self._new_deck_dialog).pack(side="left", padx=8)

        # Front / Back
        for attr, label in [("_front_box", "Front"), ("_back_box", "Back")]:
            r = ctk.CTkFrame(form, fg_color="transparent")
            r.pack(fill="x", padx=PADDING, pady=(10, 0))
            ctk.CTkLabel(r, text=label, font=ctk.CTkFont(FONT_FAMILY, 13),
                         text_color=TEXT_MUTED, width=60, anchor="w").pack(side="left")
            tb = ctk.CTkTextbox(r, height=70, width=500, fg_color=BG_INPUT,
                                corner_radius=8, font=ctk.CTkFont(FONT_FAMILY, 13))
            tb.pack(side="left", padx=8)
            setattr(self, attr, tb)

        # is_quiz toggle
        quiz_row = ctk.CTkFrame(form, fg_color="transparent")
        quiz_row.pack(fill="x", padx=PADDING, pady=(10, 0))
        ctk.CTkLabel(quiz_row, text="", width=60).pack(side="left")
        self._quiz_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(quiz_row, text="Quiz card (user must type the answer)",
                        variable=self._quiz_var,
                        font=ctk.CTkFont(FONT_FAMILY, 13), text_color=TEXT_MUTED,
                        checkmark_color="white", fg_color=ACCENT).pack(side="left")

        # Save button row
        btn_row = ctk.CTkFrame(form, fg_color="transparent")
        btn_row.pack(fill="x", padx=PADDING, pady=PADDING)
        ctk.CTkButton(btn_row, text="Save Card", width=140, fg_color=ACCENT,
                      hover_color="#5a61e8", corner_radius=CORNER_R,
                      command=self._save_card).pack(side="left")
        ctk.CTkButton(btn_row, text="📷 Scan", width=100, fg_color=BG_INPUT,
                      hover_color=ACCENT, corner_radius=CORNER_R,
                      command=self._scan_camera).pack(side="left", padx=8)
        ctk.CTkButton(btn_row, text="📄 Import PDF", width=120, fg_color=BG_INPUT,
                      hover_color=ACCENT, corner_radius=CORNER_R,
                      command=self._import_pdf).pack(side="left")

        # Generated cards review area (hidden until import)
        self._gen_scroll = ctk.CTkScrollableFrame(
            self, fg_color=BG_DARK,
            label_text="Generated cards — review before saving",
            label_font=ctk.CTkFont(FONT_FAMILY, 13),
            label_text_color=TEXT_MUTED
        )

    def _load_decks(self):
        decks = db.get_all_decks()
        names = [d.name for d in decks]
        self._deck_map = {d.name: d.id for d in decks}
        if names:
            self._deck_menu.configure(values=names)
            if self._deck_id is not None:
                for d in decks:
                    if d.id == self._deck_id:
                        self._deck_var.set(d.name)
                        break
            else:
                self._deck_var.set(names[0])
        else:
            self._deck_menu.configure(values=["(no decks — create one)"])

    def _get_selected_deck_id(self) -> int | None:
        return self._deck_map.get(self._deck_var.get())

    def _new_deck_dialog(self):
        dialog = ctk.CTkInputDialog(text="Deck name:", title="New Deck")
        name = dialog.get_input()
        if name and name.strip():
            d = db.create_deck(name.strip())
            self._deck_map[d.name] = d.id
            names = list(self._deck_map.keys())
            self._deck_menu.configure(values=names)
            self._deck_var.set(d.name)

    def _save_card(self):
        front = self._front_box.get("1.0", "end").strip()
        back  = self._back_box.get("1.0", "end").strip()
        deck_id = self._get_selected_deck_id()

        if not front or not back:
            messagebox.showwarning("Missing content", "Both front and back are required.")
            return
        if deck_id is None:
            messagebox.showwarning("No deck", "Please select or create a deck first.")
            return

        card = Card(front=front, back=back, is_quiz=self._quiz_var.get(), deck_id=deck_id)
        db.create_card(card)
        self._front_box.delete("1.0", "end")
        self._back_box.delete("1.0", "end")
        messagebox.showinfo("Saved", "Card saved successfully!")

    def _scan_camera(self):
        deck_id = self._get_selected_deck_id()
        if deck_id is None:
            messagebox.showwarning("No deck", "Please select or create a deck first.")
            return
        try:
            image_bytes = self.app.scan.capture_from_camera()
            cards_data  = self.app.claude.generate_cards_from_image(image_bytes)
            self._show_generated_cards(cards_data, deck_id)
        except Exception as e:
            messagebox.showerror("Scan failed", str(e))

    def _import_pdf(self):
        deck_id = self._get_selected_deck_id()
        if deck_id is None:
            messagebox.showwarning("No deck", "Please select or create a deck first.")
            return
        path = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
        if not path:
            return
        try:
            text       = self.app.scan.extract_text_from_pdf(path)
            cards_data = self.app.claude.generate_cards_from_text(text)
            self._show_generated_cards(cards_data, deck_id)
        except Exception as e:
            messagebox.showerror("Import failed", str(e))

    def _show_generated_cards(self, cards_data: list[dict], deck_id: int):
        for w in self._gen_scroll.winfo_children():
            w.destroy()
        self._gen_scroll.pack(fill="both", expand=True, padx=PADDING, pady=(0, PADDING))

        self._gen_entries: list[tuple] = []
        for cd in cards_data:
            row_frame = ctk.CTkFrame(self._gen_scroll, fg_color=BG_CARD, corner_radius=CORNER_R)
            row_frame.pack(fill="x", pady=4)

            front_e = ctk.CTkEntry(row_frame, width=380, fg_color=BG_INPUT, corner_radius=6)
            front_e.insert(0, cd.get("front", ""))
            front_e.pack(side="left", padx=8, pady=8)

            back_e = ctk.CTkEntry(row_frame, width=380, fg_color=BG_INPUT, corner_radius=6)
            back_e.insert(0, cd.get("back", ""))
            back_e.pack(side="left", padx=8)

            quiz_var = ctk.BooleanVar(value=cd.get("is_quiz", False))
            ctk.CTkCheckBox(row_frame, text="Quiz", variable=quiz_var,
                            fg_color=ACCENT, checkmark_color="white").pack(side="left", padx=8)

            del_btn = ctk.CTkButton(row_frame, text="✕", width=30, fg_color=COLOR_RED,
                                    hover_color="#c0392b", corner_radius=6)
            del_btn.pack(side="right", padx=8)

            entry_tuple = (front_e, back_e, quiz_var, row_frame)
            self._gen_entries.append(entry_tuple)
            del_btn.configure(command=lambda rf=row_frame: rf.destroy())

        ctk.CTkButton(
            self._gen_scroll, text="Save All Cards", fg_color=ACCENT,
            hover_color="#5a61e8", corner_radius=CORNER_R,
            command=lambda: self._save_generated(deck_id)
        ).pack(pady=8)

    def _save_generated(self, deck_id: int):
        saved = 0
        for front_e, back_e, quiz_var, row_frame in self._gen_entries:
            if not row_frame.winfo_exists():
                continue
            front = front_e.get().strip()
            back  = back_e.get().strip()
            if front and back:
                db.create_card(Card(front=front, back=back,
                                    is_quiz=quiz_var.get(), deck_id=deck_id))
                saved += 1
        messagebox.showinfo("Saved", f"{saved} cards saved to deck.")
        self._gen_scroll.pack_forget()
