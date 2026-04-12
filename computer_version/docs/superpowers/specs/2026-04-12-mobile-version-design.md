# Mobile Version Design

**Date:** 2026-04-12
**Status:** Approved

## Problem

The flashcard app runs on the desktop (macOS, PyQt5). The user wants a version that runs on their Samsung Android phone, shares cards with the desktop over local WiFi, and supports full card management (create, edit, delete, review).

## Goal

Build a Python/Kivy Android app in `mobile_version/` that reuses all business logic from `computer_version/` and syncs with the desktop over local WiFi via a Flask server.

## Scope

**New directory:** `mobile_version/`
- `main.py` — Kivy app entry point
- `data/` — copied verbatim from `computer_version/data/`
- `services/` — copied verbatim from `computer_version/services/`
- `sync_client.py` — HTTP client that pulls/pushes changes to the desktop
- `ui/` — 5 Kivy screens
- `requirements.txt` — Kivy + dependencies

**Addition to `computer_version/`:**
- `sync_server.py` — Flask HTTP server; run manually on desktop when syncing

**No changes to:** existing `computer_version/` code.

## Architecture

```
flashcards/
├── computer_version/
│   ├── sync_server.py        (new)
│   └── ... (unchanged)
└── mobile_version/
    ├── main.py
    ├── requirements.txt
    ├── sync_client.py
    ├── data/                 (copied)
    ├── services/             (copied)
    └── ui/
        ├── app.py
        ├── home_screen.py
        ├── deck_screen.py
        ├── create_screen.py
        ├── review_screen.py
        └── settings_screen.py
```

The Kivy app uses `ScreenManager` for navigation. All screens access services via `self.app` (same pattern as the desktop). The local SQLite database lives on the phone. Sync overwrites it from the desktop on pull and pushes local changes on push.

## Sync Protocol

The desktop runs `python sync_server.py` to start a Flask server on port 5000.

### Endpoints

| Method | Path | Description |
|---|---|---|
| `GET /export` | — | Returns full database as JSON (all decks + cards) |
| `POST /import` | body: JSON | Merges incoming decks and cards into desktop DB |

### Sync flow (phone side)

**Pull** — phone calls `GET /export`, replaces its local DB entirely with the received data.

**Push** — phone calls `POST /import` with its local DB as JSON; desktop merges (upserts by id, last-write-wins).

Sync is manual: triggered by a "Sync" button in the phone's Settings screen. The user types the desktop's local IP address (e.g. `192.168.1.5`) into Settings once and it is saved.

## Mobile UI

5 screens, touch-friendly (minimum 48dp tap targets), Kivy `BoxLayout` / `GridLayout`:

- **HomeScreen** — deck grid (2 columns), daily goal progress bar, Start Review and New Card buttons
- **DeckScreen** — scrollable card list, search field, edit/delete per card
- **CreateScreen** — manual front/back entry, TXT import, Excel import (openpyxl), duplicate detection (same as desktop)
- **ReviewScreen** — card flip, quiz mode, Claude explanation, audio (macOS `say` replaced with Android TTS via `plyer.tts`)
- **SettingsScreen** — desktop IP, daily goal, Claude API key, decay rate, Sync button

**Not included:** PDF scan (camera scanning is a future addition).

## Navigation

```python
ScreenManager
├── HomeScreen     (name='home')
├── DeckScreen     (name='deck')
├── CreateScreen   (name='create')
├── ReviewScreen   (name='review')
└── SettingsScreen (name='settings')
```

`App.show_home()`, `App.show_deck(id)`, etc. call `self.screen_manager.current = 'screen_name'`.

## Audio

Desktop uses macOS `say` command. Mobile uses `plyer.tts.speak(text)` which calls Android's built-in TTS engine. Same `_extract_word` logic — reads only the first line of the card.

## Requirements

```
kivy>=2.3.0
anthropic>=0.25.0
openpyxl>=3.1.0
pdfplumber>=0.11.0
plyer>=2.1.0
Pillow>=10.3.0
requests>=2.31.0
```

Desktop sync server additionally needs:
```
flask>=3.0.0
```

## Success Criteria

- `python main.py` launches the Kivy app
- All 5 screens render and navigate correctly
- Cards created on phone appear on desktop after push sync
- Cards created on desktop appear on phone after pull sync
- Review flow, quiz mode, and settings save all work
