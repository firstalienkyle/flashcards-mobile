# Flashcards

A spaced-repetition flashcard app with a Python desktop version and a native Android app, both sharing the same SQLite database over WiFi sync.

## Features

- **Spaced repetition** — cards are prioritised by memory decay, so you review what you're about to forget
- **Two card types** — flip cards (see the answer) and quiz cards (type the answer)
- **Android app** — full native APK built with Kivy, works offline
- **Desktop app** — PyQt5 app for Mac/Windows/Linux
- **WiFi sync** — pull your desktop decks onto your phone or push phone cards back
- **Import from file** — bulk import cards from a `.txt` file (front/back pairs separated by blank lines) or Excel (column A = front, column B = back)

## Download

Grab the latest Android APK from the [Releases page](../../releases/latest) — no Play Store needed.

## Project Structure

```
flashcards/
├── mobile_version/       # Android app (Kivy)
│   ├── ui/               # All 5 screens
│   ├── services/         # Spaced repetition, review scheduler
│   ├── data/             # SQLite models and database layer
│   ├── sync_client.py    # WiFi sync (pull/push)
│   └── buildozer.spec    # Android build config
├── computer_version/     # Desktop app (PyQt5)  (not in this repo)
│   └── sync_server.py    # Flask server the phone connects to
└── .github/workflows/    # CI — builds APK on every push to master
```

## Running the Android App

Install the APK from the Releases page. On first install Android will ask you to allow installs from unknown sources — this is a one-time prompt.

## Running the Desktop App

```bash
cd computer_version
pip install -r requirements.txt
python main.py
```

## WiFi Sync

1. Run the sync server on your computer:
   ```bash
   cd computer_version
   python sync_server.py
   ```
2. Find your computer's local IP:
   ```bash
   ipconfig getifaddr en0   # Mac
   ```
3. In the Android app go to **Settings**, enter `http://<your-ip>:5000` as the Desktop IP, then tap **Pull from Desktop**.

## TXT Import Format

```
What is the capital of France?

Paris

What year did WW2 end?

1945
```

Front and back separated by a blank line, pairs separated by a blank line.

## Building the APK Yourself

Push to the `master` branch — GitHub Actions builds the APK automatically and publishes it as a Release. First build takes ~25 minutes (NDK download), subsequent builds use the cache.

## Tech Stack

| Layer | Technology |
|---|---|
| Android UI | Python 3, Kivy 2.3 |
| Desktop UI | Python 3, PyQt5 |
| Database | SQLite (via Python built-in) |
| Sync | Flask (server) + requests (client) |
| Android build | buildozer + python-for-android |
| CI/CD | GitHub Actions |
