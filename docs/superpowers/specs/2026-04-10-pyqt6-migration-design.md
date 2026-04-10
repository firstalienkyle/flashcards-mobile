# PyQt6 Migration Design

**Date:** 2026-04-10
**Status:** Approved

## Problem

The app crashes on macOS 12 Monterey because Python 3.12's bundled Tk 8.6.13 calls
`-[NSApplication macOSVersion]`, a selector that doesn't exist on macOS 12. All
python.org Python versions up to 3.12.3 have this bug. Rather than ask the user to
upgrade Python, we replace the GUI framework entirely.

## Goal

Port the UI layer from `customtkinter` to `PyQt6`, which installs via pip with
pre-built ARM64 wheels and uses macOS native appearance (follows system light/dark
mode automatically).

## Scope

**Changes:**
- `ui/` — all 6 files rewritten for PyQt6
- `requirements.txt` — remove `customtkinter`, add `PyQt6`

**No changes:**
- `services/` — all service classes untouched
- `data/` — database and models untouched
- `main.py` — entry point needs one addition (see below)
- `config.py` — color constants become unused (can be deleted later)

## Architecture

```
App (QMainWindow)
└── QStackedWidget  (central widget)
    ├── HomeScreen     (QWidget)
    ├── DeckScreen     (QWidget)
    ├── CreateScreen   (QWidget)
    ├── ReviewScreen   (QWidget)
    └── SettingsScreen (QWidget)
```

`App` holds all service references (`db`, `rs`, `claude`, `scan`, `notif`) exactly
as before. Screens access them via `self.app`. Navigation is done by calling
`app.show_home()`, `app.show_deck(id)`, etc., which call
`stacked_widget.setCurrentWidget(screen)`.

## Widget Mapping

| customtkinter | PyQt6 |
|---|---|
| `ctk.CTk` | `QMainWindow` |
| `ctk.CTkFrame` | `QWidget` / `QFrame` |
| `ctk.CTkLabel` | `QLabel` |
| `ctk.CTkButton` | `QPushButton` |
| `ctk.CTkEntry` | `QLineEdit` |
| `ctk.CTkTextbox` | `QTextEdit` |
| `ctk.CTkProgressBar` | `QProgressBar` |
| `ctk.CTkScrollableFrame` | `QScrollArea` wrapping a `QWidget` |
| `.pack()` / `.grid()` | `QVBoxLayout` / `QHBoxLayout` / `QGridLayout` |
| `ctk.CTkFont` | `QFont` |

## Appearance

Native macOS appearance. No custom colors. The app inherits the system palette so
it automatically supports light and dark mode without any extra code.

## Threading

`NotificationService` runs a background thread that fires system notifications via
`plyer`. It does not touch the UI, so it works unchanged.

The Claude API call in `ReviewScreen` remains synchronous (blocking) for now.
This is acceptable for the current scope.

## Screen-by-screen notes

- **HomeScreen** — deck grid uses `QGridLayout` inside a `QScrollArea`; progress
  bar uses `QProgressBar`.
- **DeckScreen** — card list uses `QListWidget`; search uses `QLineEdit`; edit/delete
  modal uses `QDialog`.
- **CreateScreen** — scan and manual entry; file dialog uses `QFileDialog`.
- **ReviewScreen** — card flip and quiz entry; Claude explanation uses `QLabel` with
  word wrap.
- **SettingsScreen** — form layout using `QFormLayout`; API key field uses
  `QLineEdit` with password echo mode.

## Entry point change (main.py)

`main.py` needs a `QApplication` created before the `App` window, and the Qt event
loop started at the end instead of `app.mainloop()`. The services construction is
unchanged.

## Success criteria

- `python main.py` launches without crash on macOS 12
- All 5 screens render and navigate correctly
- Daily goal progress, deck tiles, card review flow, settings save all work
- App follows system light/dark mode
