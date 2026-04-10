from tkinter import messagebox
import customtkinter as ctk
from config import (ACCENT, BG_CARD, BG_DARK, BG_INPUT, TEXT_PRIMARY, TEXT_MUTED,
                    CORNER_R, PADDING, FONT_FAMILY)
import data.database as db

class SettingsScreen(ctk.CTkFrame):
    def __init__(self, app):
        super().__init__(app, fg_color=BG_DARK, corner_radius=0)
        self.app = app
        self._build()
        self._load()

    def _build(self):
        top = ctk.CTkFrame(self, fg_color=BG_DARK)
        top.pack(fill="x", padx=PADDING, pady=(PADDING, 0))
        ctk.CTkButton(top, text="← Back", width=80, fg_color=BG_CARD,
                      hover_color=ACCENT, corner_radius=CORNER_R,
                      command=self.app.show_home).pack(side="left")
        ctk.CTkLabel(top, text="Settings", font=ctk.CTkFont(FONT_FAMILY, 20, "bold"),
                     text_color=TEXT_PRIMARY).pack(side="left", padx=12)

        form = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=CORNER_R)
        form.pack(fill="x", padx=PADDING, pady=PADDING)

        self._fields = {}
        for key, label, kwargs in [
            ("daily_goal",    "Daily goal (cards)",     {"width": 100}),
            ("notify_time",   "Notify at (HH:MM)",      {"width": 100}),
            ("claude_api_key","Claude API key",          {"width": 400, "show": "*"}),
        ]:
            row = ctk.CTkFrame(form, fg_color="transparent")
            row.pack(fill="x", padx=PADDING, pady=(PADDING, 0))
            ctk.CTkLabel(row, text=label, width=180, anchor="w",
                         font=ctk.CTkFont(FONT_FAMILY, 13),
                         text_color=TEXT_MUTED).pack(side="left")
            show = kwargs.pop("show", "")
            entry = ctk.CTkEntry(row, fg_color=BG_INPUT, corner_radius=8,
                                 show=show, **kwargs)
            entry.pack(side="left", padx=8)
            self._fields[key] = entry

            # Show/hide toggle for API key
            if key == "claude_api_key":
                vis_var = ctk.BooleanVar(value=False)
                def toggle_vis(var=vis_var, e=entry):
                    e.configure(show="" if var.get() else "*")
                ctk.CTkCheckBox(row, text="Show", variable=vis_var,
                                command=toggle_vis, fg_color=ACCENT,
                                checkmark_color="white",
                                font=ctk.CTkFont(FONT_FAMILY, 12),
                                text_color=TEXT_MUTED).pack(side="left", padx=8)

        # Decay rate slider
        decay_row = ctk.CTkFrame(form, fg_color="transparent")
        decay_row.pack(fill="x", padx=PADDING, pady=(PADDING, 0))
        ctk.CTkLabel(decay_row, text="Decay rate (pts/day)", width=180, anchor="w",
                     font=ctk.CTkFont(FONT_FAMILY, 13),
                     text_color=TEXT_MUTED).pack(side="left")
        self._decay_var = ctk.DoubleVar(value=5.0)
        self._decay_label = ctk.CTkLabel(decay_row, text="5.0",
                                          font=ctk.CTkFont(FONT_FAMILY, 13),
                                          text_color=TEXT_PRIMARY, width=30)
        self._decay_label.pack(side="right", padx=(0, PADDING))
        ctk.CTkSlider(decay_row, from_=0, to=20, variable=self._decay_var,
                      width=200, progress_color=ACCENT,
                      command=lambda v: self._decay_label.configure(
                          text=f"{v:.1f}")).pack(side="left", padx=8)

        # Save button
        ctk.CTkButton(form, text="Save Settings", fg_color=ACCENT,
                      hover_color="#5a61e8", corner_radius=CORNER_R,
                      command=self._save).pack(anchor="e", padx=PADDING, pady=PADDING)

    def _load(self):
        settings = db.get_all_settings()
        for key, entry in self._fields.items():
            entry.delete(0, "end")
            entry.insert(0, settings.get(key, ""))
        decay = float(settings.get("decay_rate", "5.0"))
        self._decay_var.set(decay)
        self._decay_label.configure(text=f"{decay:.1f}")

    def _save(self):
        for key, entry in self._fields.items():
            db.set_setting(key, entry.get().strip())
        db.set_setting("decay_rate", f"{self._decay_var.get():.1f}")
        messagebox.showinfo("Saved", "Settings saved.")
        self.app.show_home()
