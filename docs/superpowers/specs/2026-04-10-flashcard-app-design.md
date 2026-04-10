# Flashcard App — Design Spec
*Date: 2026-04-10*

---

## Overview

A Python desktop flashcard app (macOS) with spaced-repetition memory tracking, Claude API integration for card generation and answer explanations, camera/PDF import, push notifications, and a dark-themed CustomTkinter UI.

---

## Project Structure

```
flashcard-app/
├── main.py                      # Entry point, wires everything together
├── config.py                    # Constants, default settings
├── data/
│   ├── database.py              # SQLite setup, schema creation, migrations
│   └── models.py                # Card, Deck, ReviewSession dataclasses
├── services/
│   ├── claude_service.py        # Claude API: card generation + answer explanation
│   ├── review_scheduler.py      # Review queue algorithm + memory decay
│   ├── scan_service.py          # Webcam capture + PDF extraction → Claude
│   └── notification_service.py  # System tray (pystray) + plyer notifications
└── ui/
    ├── app.py                   # Root CTk window, screen router
    ├── home_screen.py           # Deck list, daily goal progress bar
    ├── review_screen.py         # Card flip, quiz mode, back/forward navigation
    ├── create_screen.py         # Manual creation + scan/PDF import flow
    ├── deck_screen.py           # View/edit/delete cards in a deck
    └── settings_screen.py       # Daily goal, notify time, API key, decay rate
```

---

## Data Model (SQLite)

### `cards`
| field | type | notes |
|---|---|---|
| id | INTEGER PK | |
| deck_id | INTEGER FK | references decks.id |
| front | TEXT | always shown to user |
| back | TEXT | revealed on flip; correct answer for quiz cards |
| is_quiz | BOOLEAN | if true, user must type answer instead of flipping |
| memory_level | REAL | 0–100, starts at 50 on creation |
| last_reviewed | DATETIME | used to compute daily decay |
| created_at | DATETIME | |

### `decks`
| field | type | notes |
|---|---|---|
| id | INTEGER PK | |
| name | TEXT | user-defined |
| created_at | DATETIME | |

### `session_cards`
Tracks every card interaction within a review session. Enables backwards navigation and memory snapshots.
| field | type | notes |
|---|---|---|
| session_id | INTEGER FK | references review_sessions.id |
| card_id | INTEGER FK | references cards.id |
| reviewed_at | DATETIME | |
| result | TEXT | `'seen'`, `'correct'`, `'incorrect'` |
| memory_before | REAL | snapshot before this review event |
| memory_after | REAL | snapshot after this review event |

### `review_sessions`
| field | type | notes |
|---|---|---|
| id | INTEGER PK | |
| started_at | DATETIME | |
| ended_at | DATETIME | nullable until session ends |
| cards_reviewed | INTEGER | count of unique cards seen this session |

### `settings` (single-row key-value store)
| key | default value |
|---|---|
| daily_goal | 20 |
| notify_time | "18:00" |
| claude_api_key | "" |
| decay_rate | 5.0 |

---

## Memory Level System

### Rules
- **Regular flip card — first view in session:** `memory_level += 10`
- **Regular flip card — subsequent views same session:** no change
- **Quiz card — correct (answer matches back):** `memory_level += 20`
- **Quiz card — incorrect (answer doesn't match back):** `memory_level -= 10`
- **Floor/ceiling:** memory_level is always clamped to `[0, 100]`

### Decay
Applied when computing *effective* memory level for scheduling:
```
effective_level = max(0, stored_level - decay_rate × days_since_last_reviewed)
```
Default `decay_rate` is 5.0 points/day. Adjustable in Settings. The stored `memory_level` in the database is updated only when a card is reviewed — decay is computed on-the-fly for scheduling purposes, then written back on review.

---

## Services

### `ReviewScheduler`
- Computes effective memory level for every card in the user's decks
- Sorts by effective memory level ascending
- Builds session queue: **75% lowest-memory cards**, **25% random** from the rest
- Maintains an ordered in-memory list during a session for back/forward navigation
- On card review, writes the new `memory_level` and `last_reviewed` to the database and records a `session_cards` row

### `ClaudeService`
Uses `claude-sonnet-4-6` via the Anthropic Python SDK.

**`generate_cards(text: str) → list[dict]`**
- Sends raw text (from camera image or PDF) to Claude with a prompt instructing it to produce concise front/back flashcard pairs
- Returns a list of `{front, back, is_quiz}` dicts for user review before saving
- `is_quiz` defaults to False; Claude may suggest True for definition-style cards

**`explain_answer(front: str, back: str) → str`**
- Called automatically when a quiz card answer doesn't match `card.back`
- Returns a short, plain-language explanation of why the back is the correct answer
- Shown inline below the correct answer on the review screen

### `ScanService`
Two input paths, both funnel into `ClaudeService.generate_cards()`:

- **Camera**: opens webcam via OpenCV (`cv2`), shows live preview in a CTk window, captures on button press, sends the raw image to Claude Vision API (no OCR library needed)
- **PDF**: extracts text page-by-page with `pdfplumber`, concatenates, passes to `ClaudeService.generate_cards()`

Both paths end with a "review generated cards" screen where the user can edit, delete, or approve before saving to the database.

### `NotificationService`
- Runs a background daemon thread (started at app launch) that checks the time every 60 seconds
- If current time matches `notify_time` setting and today's reviewed count < `daily_goal` → fires a system notification via `plyer.notification.notify()`
- App minimises to a system tray icon via `pystray` so notifications fire even when the main window is hidden
- On app open, if goal is not yet met, shows an in-app banner as a fallback

---

## UI Screens

### Dark Theme
CustomTkinter with `appearance_mode = "dark"`. Accent colour: `#7c83fd` (purple-blue). All screens use rounded corners (`corner_radius=12`), consistent padding (16px), and the `Inter` font where available.

### Animations
Card flip simulated by animating the card frame's width from full → 0, swapping content, then expanding back to full. Implemented with `after()` callbacks at ~16ms intervals (60fps).

### `HomeScreen`
- Deck cards in a scrollable grid, each showing name, card count, average memory level
- Daily goal progress bar at top: "12 / 20 cards reviewed today"
- Buttons: **Start Review**, **Create Card**, **Import** (scan/PDF), **Settings**

### `ReviewScreen`
- Card frame centred on screen with flip animation for regular cards
- For quiz cards: text input field + Submit button instead of flip button
  - On submit: compare answer to `card.back` (case-insensitive, strip punctuation)
  - If correct: green flash, `memory_level += 20`
  - If wrong: show correct answer + Claude explanation, `memory_level -= 10`
- **Previous** / **Next** navigation buttons to move through session history
- Memory level bar and percentage shown per card
- Session progress counter at top (e.g. "8 / 25")
- "End Session" button writes session end time and returns to HomeScreen

### `CreateScreen`
- Front / Back text fields, `is_quiz` toggle checkbox
- Deck selector dropdown (or "New deck…" option)
- **Scan with Camera** → opens webcam preview window → capture → Claude generates cards → review/edit modal → save
- **Import PDF** → file picker dialog → Claude generates cards → review/edit modal → save
- **Save Card** for manual entries

### `DeckScreen`
- Scrollable list of all cards in the selected deck
- Click any card to open an edit modal: front, back, `is_quiz` toggle
- Delete card button with confirmation dialog
- Rename deck button at top
- Search bar to filter cards within the deck

### `SettingsScreen`
- Daily goal: number spinner
- Notification time: time picker (HH:MM)
- Claude API key: masked text field with show/hide toggle
- Decay rate: slider (0–20 pts/day, default 5)
- Save button writes all values to the `settings` table

---

## Dependencies

| package | purpose |
|---|---|
| `customtkinter` | dark-themed UI framework |
| `anthropic` | Claude API SDK |
| `opencv-python` | webcam capture |
| `pdfplumber` | PDF text extraction |
| `pystray` | system tray icon |
| `plyer` | cross-platform desktop notifications |
| `Pillow` | image handling (required by pystray + CTk) |

All stored in `requirements.txt`. SQLite via Python stdlib `sqlite3` — no ORM.

---

## Key Flows

### Review Session Flow
1. User taps **Start Review** on HomeScreen
2. `ReviewScheduler` builds queue (75% low-memory + 25% random), creates `review_sessions` row
3. `ReviewScreen` shows cards one by one
   - Regular card: user flips, `memory_level += 10` (first time this session only)
   - Quiz card: user types, app compares, adjusts memory, shows explanation if wrong
4. User can tap **Previous** to revisit earlier cards in session (read-only — no memory re-adjustment on revisit)
5. Session ends: `ended_at` written, HomeScreen goal progress updated

### Import Flow
1. User chooses Camera or PDF
2. `ScanService` extracts content, `ClaudeService.generate_cards()` returns proposals
3. Review/edit modal shown — user can modify any card before saving
4. Approved cards written to selected deck

---

## Out of Scope
- Cloud sync / multi-device
- Sharing decks with other users
- Audio/image card content (text only)
- Windows / Linux support (macOS first)
