from pathlib import Path
import random
from datetime import datetime

import data.database as db
from data.models import PhotoCard
from services.review_scheduler import build_review_queue, apply_memory_delta
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import AsyncImage
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.metrics import dp
from ui._widgets import btn, lbl, top_bar

SUPPORTED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp'}


def _is_image_file(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS


class PhotoScreen(Screen):
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self._queue: list[PhotoCard] = []
        self._photos: list[PhotoCard] = []
        self._index: int = 0
        self._seen: set[int] = set()
        self._build()
        self._load_photos()

    def _build(self):
        root = BoxLayout(orientation='vertical', padding=dp(12), spacing=dp(10))
        root.add_widget(top_bar('Photo Cards', on_back=lambda _: self.app.show_home()))

        control_row = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(52), spacing=dp(8))
        control_row.add_widget(btn('📁 Import Folder', on_press=self._import_folder, size_hint_x=None, width=dp(140)))
        control_row.add_widget(btn('🎲 Pick One', on_press=self._pick_random, size_hint_x=None, width=dp(120)))
        control_row.add_widget(BoxLayout())
        self._mem_lbl = lbl('Mem 0%', size=14, halign='right')
        control_row.add_widget(self._mem_lbl)
        root.add_widget(control_row)

        self._photo_area = BoxLayout(orientation='vertical', size_hint=(1, None), height=dp(320), padding=dp(8))
        self._photo_widget = AsyncImage(source='', allow_stretch=True, keep_ratio=True)
        self._photo_area.add_widget(self._photo_widget)
        self._photo_path_lbl = lbl('', size=12, halign='center')
        self._photo_area.add_widget(self._photo_path_lbl)
        root.add_widget(self._photo_area)

        nav = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(52), spacing=dp(8))
        self._prev_btn = btn('← Prev', on_press=lambda _: self._goto(self._index - 1), size_hint_x=None, width=dp(90))
        nav.add_widget(self._prev_btn)
        self._next_btn = btn('Next →', on_press=lambda _: self._goto(self._index + 1), size_hint_x=None, width=dp(90))
        nav.add_widget(self._next_btn)
        self._up_btn = btn('✓', on_press=lambda _: self._set_memory(100), size_hint_x=None, width=dp(52))
        nav.add_widget(self._up_btn)
        self._down_btn = btn('✕', on_press=lambda _: self._set_memory(0), size_hint_x=None, width=dp(52))
        nav.add_widget(self._down_btn)
        nav.add_widget(BoxLayout())
        root.add_widget(nav)

        self._notice_lbl = lbl('Import a folder and pick a photo to start.', size=12, halign='center')
        root.add_widget(self._notice_lbl)
        self.add_widget(root)

    def _load_photos(self):
        self._photos = db.get_all_photos()
        self._queue = build_review_queue(self._photos, decay_rate=3.0, queue_size=max(1, len(self._photos)))
        self._index = 0
        if self._queue:
            self._show_photo()
        else:
            self._photo_widget.source = ''
            self._photo_path_lbl.text = ''
            self._mem_lbl.text = 'Mem 0%'
            self._prev_btn.disabled = True
            self._next_btn.disabled = True

    def _import_folder(self, _):
        try:
            from plyer import filechooser
        except ImportError as e:
            self._notice_lbl.text = f'File chooser unavailable: {e}'
            return

        def on_selection(selection):
            if not selection:
                return
            path = Path(selection[0])
            if path.is_dir():
                self._import_photo_directory(path)
            else:
                self._import_photo_files([Path(p) for p in selection])

        if hasattr(filechooser, 'open_dir'):
            filechooser.open_dir(title='Select photo folder', on_selection=on_selection)
        else:
            filechooser.open_file(title='Select photo files', multiple=True, on_selection=on_selection)

    def _import_photo_directory(self, folder: Path):
        added = 0
        for path in folder.rglob('*'):
            if _is_image_file(path):
                photo = db.add_photo_path(str(path))
                if photo is not None:
                    added += 1
        self._notice_lbl.text = f'Imported {added} photo(s).'
        self._load_photos()

    def _import_photo_files(self, files: list[Path]):
        added = 0
        for path in files:
            if _is_image_file(path):
                photo = db.add_photo_path(str(path))
                if photo is not None:
                    added += 1
        self._notice_lbl.text = f'Imported {added} photo(s).'
        self._load_photos()

    def _pick_random(self, _=None):
        if not self._queue:
            return
        self._index = random.randrange(len(self._queue))
        self._show_photo()

    def _goto(self, index: int):
        if 0 <= index < len(self._queue):
            self._index = index
            self._show_photo()

    def _show_photo(self):
        photo = self._queue[self._index]
        self._photo_widget.source = photo.path
        self._photo_path_lbl.text = f'{Path(photo.path).name}  ·  {photo.memory_level:.0f}%'
        self._mem_lbl.text = f'Mem {photo.memory_level:.0f}%'
        self._prev_btn.disabled = self._index == 0
        self._next_btn.disabled = self._index >= len(self._queue) - 1
        self._notice_lbl.text = ''
        if photo.id not in self._seen:
            self._record_memory(photo, 'seen')
            self._seen.add(photo.id)

    def _record_memory(self, photo: PhotoCard, result: str):
        old_level = photo.memory_level
        photo.memory_level = apply_memory_delta(photo, result=result, already_seen=False)
        db.update_photo_memory(photo.id, photo.memory_level, datetime.now())
        self._mem_lbl.text = f'Mem {photo.memory_level:.0f}%'
        self._photo_path_lbl.text = f'{Path(photo.path).name}  ·  {photo.memory_level:.0f}%'

    def _set_memory(self, value: float):
        if not self._queue:
            return
        photo = self._queue[self._index]
        photo.memory_level = float(value)
        db.set_photo_memory_level(photo.id, photo.memory_level, datetime.now())
        self._mem_lbl.text = f'Mem {photo.memory_level:.0f}%'
        self._photo_path_lbl.text = f'{Path(photo.path).name}  ·  {photo.memory_level:.0f}%'
        self._notice_lbl.text = f'Set memory to {photo.memory_level:.0f}%.'
