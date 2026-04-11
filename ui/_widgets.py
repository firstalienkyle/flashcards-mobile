"""Shared Kivy widget helpers used across screens."""
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.textinput import TextInput
from kivy.metrics import dp
from kivy.utils import get_color_from_hex
import config

ACCENT = get_color_from_hex(config.ACCENT + 'ff')
BG     = get_color_from_hex(config.BG    + 'ff')
CARD   = get_color_from_hex(config.CARD_BG + 'ff')
TEXT   = get_color_from_hex(config.TEXT  + 'ff')
MUTED  = get_color_from_hex(config.MUTED + 'ff')
GREEN  = get_color_from_hex(config.GREEN + 'ff')
RED    = get_color_from_hex(config.RED   + 'ff')


def btn(text, on_press=None, color=None, **kw):
    b = Button(
        text=text,
        background_color=color or ACCENT,
        size_hint_y=None,
        height=dp(48),
        **kw,
    )
    if on_press:
        b.bind(on_press=on_press)
    return b


def lbl(text, size=16, color=None, bold=False, halign='left', **kw):
    l = Label(
        text=('[b]' + text + '[/b]') if bold else text,
        markup=bold,
        font_size=dp(size),
        color=color or TEXT,
        halign=halign,
        valign='middle',
        **kw,
    )
    l.bind(size=l.setter('text_size'))
    return l


def top_bar(title_text, on_back):
    bar = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(52), spacing=dp(8))
    bar.add_widget(btn('← Back', on_press=on_back, size_hint_x=None, width=dp(90)))
    bar.add_widget(lbl(title_text, size=20, bold=True))
    return bar


def confirm_popup(title, message, on_yes):
    content = BoxLayout(orientation='vertical', spacing=dp(12), padding=dp(12))
    content.add_widget(lbl(message, halign='center'))
    btns = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(48), spacing=dp(8))
    popup = Popup(title=title, content=content,
                  size_hint=(0.85, None), height=dp(200))

    def yes(_):
        popup.dismiss()
        on_yes()

    btns.add_widget(btn('Cancel', on_press=lambda _: popup.dismiss(),
                        color=get_color_from_hex('#444444ff')))
    btns.add_widget(btn('Yes', on_press=yes, color=RED))
    content.add_widget(btns)
    popup.open()


def input_popup(title, hint, on_ok):
    content = BoxLayout(orientation='vertical', spacing=dp(12), padding=dp(12))
    ti = TextInput(hint_text=hint, multiline=False, size_hint_y=None, height=dp(44))
    content.add_widget(ti)
    btns = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(48), spacing=dp(8))
    popup = Popup(title=title, content=content,
                  size_hint=(0.9, None), height=dp(180))

    def ok(_):
        val = ti.text.strip()
        if val:
            popup.dismiss()
            on_ok(val)

    btns.add_widget(btn('Cancel', on_press=lambda _: popup.dismiss(),
                        color=get_color_from_hex('#444444ff')))
    btns.add_widget(btn('OK', on_press=ok))
    content.add_widget(btns)
    ti.bind(on_text_validate=ok)
    popup.open()
