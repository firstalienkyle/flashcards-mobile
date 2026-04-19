from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.clock import Clock
import data.database as db
from ui.theme import (
    apply_bg, btn, lbl,
    SURFACE, SECONDARY, DANGER, SUCCESS, MUTED, TEXT,
    FONT_TITLE, FONT_BODY, FONT_SMALL,
    BTN_H, ROW_H, PAD, GAP,
)


class SettingsScreen(Screen):
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self._build()

    def _build(self):
        apply_bg(self)
        outer = BoxLayout(orientation='vertical', padding=0, spacing=0)

        # ── Fixed header ──────────────────────────────────────────────────────
        header = BoxLayout(size_hint_y=None, height=ROW_H,
                           padding=[PAD, 0], spacing=8)
        back = btn('Back', color=SECONDARY, height=ROW_H)
        back.size_hint_x = 0.28
        back.bind(on_press=lambda _: self.app.show_home())
        header.add_widget(back)
        header.add_widget(lbl('Settings', font_size=FONT_TITLE, bold=True,
                               height=ROW_H))
        outer.add_widget(header)

        # ── Scrollable body ───────────────────────────────────────────────────
        scroll = ScrollView(do_scroll_x=False)
        self._body = BoxLayout(orientation='vertical', padding=PAD,
                               spacing=GAP * 2, size_hint_y=None)
        self._body.bind(minimum_height=self._body.setter('height'))

        # Import button
        self._body.add_widget(lbl('Picture Buttons', font_size=FONT_BODY,
                                   color=MUTED, bold=True, height=44))

        import_btn = btn('Import Picture')
        import_btn.bind(on_press=self._import_picture)
        self._body.add_widget(import_btn)

        self._status = lbl('', font_size=FONT_SMALL, color=MUTED,
                            height=44, halign='center')
        self._body.add_widget(self._status)

        # List of current buttons (loaded dynamically)
        self._list_box = BoxLayout(orientation='vertical', size_hint_y=None,
                                   spacing=GAP)
        self._list_box.bind(minimum_height=self._list_box.setter('height'))
        self._body.add_widget(self._list_box)

        scroll.add_widget(self._body)
        outer.add_widget(scroll)
        self.add_widget(outer)

    def on_enter(self):
        self._refresh_list()

    def _refresh_list(self):
        self._list_box.clear_widgets()
        buttons = db.get_all_buttons()
        if not buttons:
            self._list_box.add_widget(
                lbl('No picture buttons yet.', color=MUTED, height=50,
                    halign='center')
            )
            return

        for pb in buttons:
            row = BoxLayout(size_hint_y=None, height=BTN_H, spacing=8)

            name_lbl = lbl(pb.label, font_size=FONT_SMALL, color=TEXT,
                           height=BTN_H, halign='left')
            row.add_widget(name_lbl)

            edit = btn('Edit', color=SECONDARY, height=BTN_H)
            edit.size_hint_x = 0.22
            edit.bind(on_press=lambda _, p=pb: self._edit_dialog(p))
            row.add_widget(edit)

            delete = btn('Del', color=DANGER, height=BTN_H)
            delete.size_hint_x = 0.18
            delete.bind(on_press=lambda _, p=pb: self._delete_confirm(p))
            row.add_widget(delete)

            self._list_box.add_widget(row)

    def _import_picture(self, _):
        import os
        if os.environ.get('ANDROID_ARGUMENT'):
            try:
                from plyer import filechooser
                filechooser.open_file(
                    on_selection=self._on_file_selected,
                    filters=['image/*'],
                    title='Choose a picture',
                )
            except Exception:
                self._show_path_popup()
        else:
            import threading
            def _pick():
                try:
                    import tkinter as tk
                    from tkinter import filedialog
                    root = tk.Tk()
                    root.withdraw()
                    root.attributes('-topmost', True)
                    path = filedialog.askopenfilename(
                        title='Choose a picture',
                        filetypes=[
                            ('Images', '*.jpg *.jpeg *.png *.gif *.bmp *.webp'),
                            ('All files', '*.*'),
                        ],
                    )
                    root.destroy()
                    if path:
                        Clock.schedule_once(lambda dt: self._ask_label(path))
                except Exception:
                    Clock.schedule_once(lambda dt: self._show_path_popup())
            threading.Thread(target=_pick, daemon=True).start()

    def _show_path_popup(self):
        content = BoxLayout(orientation='vertical', padding=12, spacing=8)
        content.add_widget(lbl('Enter full path to image:', height=32, color=MUTED))
        path_inp = TextInput(hint_text='/path/to/image.jpg', multiline=False,
                             size_hint_y=None, height=BTN_H,
                             background_color=SURFACE, foreground_color=TEXT,
                             font_size=FONT_BODY)
        content.add_widget(path_inp)
        label_inp = TextInput(hint_text='Button label', multiline=False,
                              size_hint_y=None, height=BTN_H,
                              background_color=SURFACE, foreground_color=TEXT,
                              font_size=FONT_BODY)
        content.add_widget(label_inp)
        popup = Popup(title='Import Picture', content=content, size_hint=(0.9, 0.52))

        def _do(_):
            p = path_inp.text.strip()
            lbl_text = label_inp.text.strip() or 'Picture'
            if p:
                popup.dismiss()
                self._save_picture(p, lbl_text)

        btn_row = BoxLayout(size_hint_y=None, height=BTN_H, spacing=8)
        ok = btn('Import')
        ok.bind(on_press=_do)
        cancel = btn('Cancel', color=SECONDARY)
        cancel.bind(on_press=popup.dismiss)
        btn_row.add_widget(ok)
        btn_row.add_widget(cancel)
        content.add_widget(btn_row)
        popup.open()

    def _on_file_selected(self, selection):
        if not selection:
            return
        path = selection[0]
        # Ask for a label after selection
        Clock.schedule_once(lambda dt: self._ask_label(path))

    def _ask_label(self, path):
        from pathlib import Path
        default_label = Path(path).stem
        content = BoxLayout(orientation='vertical', padding=12, spacing=8)
        content.add_widget(lbl('Button label:', height=32, color=MUTED))
        inp = TextInput(text=default_label, multiline=False,
                        size_hint_y=None, height=BTN_H,
                        background_color=SURFACE, foreground_color=TEXT,
                        font_size=FONT_BODY)
        content.add_widget(inp)
        popup = Popup(title='Label', content=content, size_hint=(0.85, 0.38))

        def _save(_):
            popup.dismiss()
            self._save_picture(path, inp.text.strip() or default_label)

        btn_row = BoxLayout(size_hint_y=None, height=BTN_H, spacing=8)
        ok = btn('Save')
        ok.bind(on_press=_save)
        cancel = btn('Cancel', color=SECONDARY)
        cancel.bind(on_press=popup.dismiss)
        btn_row.add_widget(ok)
        btn_row.add_widget(cancel)
        content.add_widget(btn_row)
        popup.open()

    def _save_picture(self, path, label):
        try:
            db.create_button(label=label, src_path=path)
            self._status.text = f'Added: {label}'
            self._status.color = SUCCESS
            self._refresh_list()
        except Exception as e:
            self._status.text = f'Error: {e}'
            self._status.color = DANGER

    def _edit_dialog(self, pb):
        content = BoxLayout(orientation='vertical', padding=12, spacing=8)
        content.add_widget(lbl('New label:', height=32, color=MUTED))
        inp = TextInput(text=pb.label, multiline=False,
                        size_hint_y=None, height=BTN_H,
                        background_color=SURFACE, foreground_color=TEXT,
                        font_size=FONT_BODY)
        content.add_widget(inp)
        popup = Popup(title='Edit Label', content=content, size_hint=(0.85, 0.38))

        def _save(_):
            new_label = inp.text.strip()
            if new_label:
                db.update_label(pb.id, new_label)
                popup.dismiss()
                self._refresh_list()

        btn_row = BoxLayout(size_hint_y=None, height=BTN_H, spacing=8)
        save = btn('Save')
        save.bind(on_press=_save)
        cancel = btn('Cancel', color=SECONDARY)
        cancel.bind(on_press=popup.dismiss)
        btn_row.add_widget(save)
        btn_row.add_widget(cancel)
        content.add_widget(btn_row)
        popup.open()

    def _delete_confirm(self, pb):
        content = BoxLayout(orientation='vertical', padding=12, spacing=8)
        content.add_widget(lbl(
            f'Delete "{pb.label}"?\nThe image file will also be removed.',
            font_size=FONT_SMALL, color=DANGER, height=80, halign='center',
        ))
        popup = Popup(title='Delete', content=content, size_hint=(0.85, 0.40))

        def _confirm(_):
            db.delete_button(pb.id)
            popup.dismiss()
            self._refresh_list()

        btn_row = BoxLayout(size_hint_y=None, height=BTN_H, spacing=8)
        confirm = btn('Delete', color=DANGER)
        confirm.bind(on_press=_confirm)
        cancel = btn('Cancel', color=SECONDARY)
        cancel.bind(on_press=popup.dismiss)
        btn_row.add_widget(confirm)
        btn_row.add_widget(cancel)
        content.add_widget(btn_row)
        popup.open()
