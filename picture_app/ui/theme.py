"""Theme for picture app — reuses same palette/sizing as flashcards."""
from kivy.graphics import Color, Rectangle
from kivy.uix.button import Button
from kivy.uix.label import Label

BG        = (0.08, 0.09, 0.12, 1)
SURFACE   = (0.13, 0.14, 0.19, 1)
PRIMARY   = (0.22, 0.53, 0.96, 1)
SECONDARY = (0.18, 0.20, 0.28, 1)
DANGER    = (0.88, 0.28, 0.28, 1)
SUCCESS   = (0.18, 0.72, 0.44, 1)
TEXT      = (0.93, 0.93, 0.97, 1)
MUTED     = (0.52, 0.53, 0.63, 1)

FONT_TITLE = '28sp'
FONT_BODY  = '20sp'
FONT_SMALL = '16sp'
BTN_H      = 110
ROW_H      = 80
PAD        = 16
GAP        = 14


def apply_bg(widget, color=BG):
    with widget.canvas.before:
        Color(*color)
        rect = Rectangle(pos=widget.pos, size=widget.size)
    widget.bind(pos=lambda w, _: setattr(rect, 'pos', w.pos))
    widget.bind(size=lambda w, _: setattr(rect, 'size', w.size))


def btn(text, color=PRIMARY, height=None, **kw):
    if height is None:
        height = BTN_H
    return Button(
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


def lbl(text, font_size=FONT_BODY, color=TEXT, bold=False,
        halign='left', height=None, **kw):
    kwargs = dict(text=text, font_size=font_size, color=color,
                  bold=bold, halign=halign, **kw)
    if height is not None:
        kwargs['size_hint_y'] = None
        kwargs['height'] = height
    l = Label(**kwargs)
    l.bind(size=lambda inst, _: setattr(inst, 'text_size', (inst.width, None)))
    return l
