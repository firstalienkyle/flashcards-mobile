"""Shared visual theme for all screens."""
from kivy.graphics import Color, Rectangle
from kivy.uix.button import Button
from kivy.uix.label import Label

# ── Palette ──────────────────────────────────────────────────────────────────
BG         = (0.08, 0.09, 0.12, 1)      # page background
SURFACE    = (0.13, 0.14, 0.19, 1)      # card / panel background
PRIMARY    = (0.22, 0.53, 0.96, 1)      # primary action buttons
SECONDARY  = (0.18, 0.20, 0.28, 1)      # secondary / back buttons
DANGER     = (0.88, 0.28, 0.28, 1)      # delete / error
SUCCESS    = (0.18, 0.72, 0.44, 1)      # correct answer
TEXT       = (0.93, 0.93, 0.97, 1)      # main text
MUTED      = (0.52, 0.53, 0.63, 1)      # secondary text
BORDER     = (0.22, 0.23, 0.31, 1)      # subtle borders

# ── Sizing ───────────────────────────────────────────────────────────────────
FONT_TITLE  = '26sp'
FONT_BODY   = '18sp'
FONT_SMALL  = '15sp'
BTN_H       = 68
ROW_H       = 60
PAD         = 20
GAP         = 12


def apply_bg(widget, color=BG):
    """Paint a solid background colour on any widget."""
    with widget.canvas.before:
        Color(*color)
        rect = Rectangle(pos=widget.pos, size=widget.size)
    widget.bind(pos=lambda w, _: setattr(rect, 'pos', w.pos))
    widget.bind(size=lambda w, _: setattr(rect, 'size', w.size))


def btn(text, color=PRIMARY, width=None, height=None, **kw):
    if height is None:
        height = BTN_H
    """Return a styled Button."""
    b = Button(
        text=text,
        font_size=FONT_BODY,
        bold=True,
        background_normal='',
        background_color=color,
        color=TEXT,
        size_hint_y=None,
        height=height,
        **kw,
    )
    if width is not None:
        b.size_hint_x = None
        b.width = width
    return b


def lbl(text, font_size=FONT_BODY, color=TEXT, bold=False,
        halign='left', height=None, **kw):
    """Return a styled Label."""
    kwargs = dict(
        text=text,
        font_size=font_size,
        color=color,
        bold=bold,
        halign=halign,
        **kw,
    )
    if height is not None:
        kwargs['size_hint_y'] = None
        kwargs['height'] = height
    l = Label(**kwargs)
    if halign != 'center':
        l.bind(size=lambda inst, _: setattr(inst, 'text_size', (inst.width, None)))
    return l
