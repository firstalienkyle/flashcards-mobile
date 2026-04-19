from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.widget import Widget
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.graphics import Color, Rectangle
import data.database as db
from ui.theme import (
    apply_bg, btn, lbl,
    SURFACE, SECONDARY, MUTED, TEXT, BG,
    FONT_TITLE, FONT_BODY, FONT_SMALL,
    BTN_H, ROW_H, PAD, GAP,
)


class HomeScreen(Screen):
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self._viewer = None   # full-screen image overlay
        self._build()

    def _build(self):
        apply_bg(self)
        root = BoxLayout(orientation='vertical', padding=PAD, spacing=GAP)

        # ── Header ──────────────────────────────────────────────────────────
        header = BoxLayout(size_hint_y=None, height=ROW_H, spacing=8)
        header.add_widget(lbl('Pictures', font_size=FONT_TITLE, bold=True,
                               height=ROW_H))
        settings_btn = btn('Settings', color=SECONDARY, height=ROW_H)
        settings_btn.size_hint_x = 0.38
        settings_btn.bind(on_press=lambda _: self.app.show_settings())
        header.add_widget(settings_btn)
        root.add_widget(header)

        # ── Picture grid ─────────────────────────────────────────────────────
        scroll = ScrollView(do_scroll_x=False)
        self._grid = GridLayout(cols=2, spacing=GAP, size_hint_y=None,
                                padding=[0, 4])
        self._grid.bind(minimum_height=self._grid.setter('height'))
        scroll.add_widget(self._grid)
        root.add_widget(scroll)

        self.add_widget(root)

    def on_enter(self):
        self._load()

    def _load(self):
        self._grid.clear_widgets()
        buttons = db.get_all_buttons()
        if not buttons:
            self._grid.cols = 1
            self._grid.add_widget(
                lbl('No pictures yet.\nGo to Settings to import some.',
                    color=MUTED, height=120, halign='center')
            )
            return

        self._grid.cols = 2
        TILE_H = 220
        for pb in buttons:
            tile = self._make_tile(pb, TILE_H)
            self._grid.add_widget(tile)

    def _make_tile(self, pb, tile_h):
        """A tappable image tile with a label below."""
        tile = BoxLayout(orientation='vertical', size_hint_y=None,
                         height=tile_h, spacing=4)
        with tile.canvas.before:
            Color(*SURFACE)
            rect = Rectangle(pos=tile.pos, size=tile.size)
        tile.bind(pos=lambda w, _: setattr(rect, 'pos', w.pos))
        tile.bind(size=lambda w, _: setattr(rect, 'size', w.size))

        from pathlib import Path
        if Path(pb.path).exists():
            img = Image(source=pb.path, allow_stretch=True,
                        keep_ratio=True, size_hint_y=1)
        else:
            img = lbl('[image missing]', color=MUTED,
                      halign='center', size_hint_y=1)

        name_lbl = lbl(pb.label, font_size=FONT_SMALL, color=TEXT,
                        halign='center', height=40)
        tile.add_widget(img)
        tile.add_widget(name_lbl)

        # Tap anywhere on the tile → full-screen viewer
        tap = Button(background_normal='', background_color=(0, 0, 0, 0),
                     size_hint=(1, 1))
        tap.bind(on_press=lambda _, p=pb.path, lbl_t=pb.label:
                 self._open_viewer(p, lbl_t))

        fl = FloatLayout(size_hint_y=None, height=tile_h)
        tile.size_hint_y = None
        tile.size = (fl.width, tile_h)
        fl.add_widget(tile)
        fl.add_widget(tap)
        return fl

    def _open_viewer(self, path, label_text):
        """Show a full-screen overlay with the image and a close button."""
        from pathlib import Path
        overlay = FloatLayout()
        with overlay.canvas.before:
            Color(*BG)
            bg_rect = Rectangle(pos=overlay.pos, size=overlay.size)
        overlay.bind(pos=lambda w, _: setattr(bg_rect, 'pos', w.pos))
        overlay.bind(size=lambda w, _: setattr(bg_rect, 'size', w.size))

        if Path(path).exists():
            img = Image(source=path, allow_stretch=True, keep_ratio=True,
                        size_hint=(1, 0.88), pos_hint={'x': 0, 'top': 1})
        else:
            img = lbl('[image not found]', color=MUTED, halign='center',
                      size_hint=(1, 0.88), pos_hint={'x': 0, 'top': 1})

        caption = Label(text=label_text, font_size=FONT_BODY, color=TEXT,
                        size_hint=(1, None), height=50,
                        pos_hint={'x': 0, 'y': 0.08},
                        halign='center')
        caption.bind(size=lambda inst, _: setattr(inst, 'text_size', (inst.width, None)))

        close = Button(text='Close', font_size=FONT_BODY, bold=True,
                       background_normal='', background_color=SECONDARY,
                       color=TEXT,
                       size_hint=(0.4, None), height=BTN_H,
                       pos_hint={'center_x': 0.5, 'y': 0})
        close.bind(on_press=lambda _: self._close_viewer(overlay))

        overlay.add_widget(img)
        overlay.add_widget(caption)
        overlay.add_widget(close)

        self._viewer = overlay
        self.add_widget(overlay)

    def _close_viewer(self, overlay):
        self.remove_widget(overlay)
        self._viewer = None

    def on_touch_down(self, touch):
        # Allow back swipe when viewer is open
        if self._viewer and not self._viewer.collide_point(*touch.pos):
            self._close_viewer(self._viewer)
            return True
        return super().on_touch_down(touch)
