[app]
title = Flashcards
package.name = flashcards
package.domain = com.flashcards

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,txt,xlsx
source.exclude_dirs = tests,__pycache__,.venv,.pytest_cache

version = 1.0.0

# Only list packages that have p4a recipes or are pure-Python.
# anthropic SDK is replaced with plain requests (pydantic-core is Rust, can't cross-compile).
# sqlite3 is a Python built-in — do NOT list it here.
requirements = python3,kivy==2.3.0,pillow,requests,plyer,openpyxl,et_xmlfile
# Note: no anthropic SDK - Claude removed. requests is still needed for WiFi sync.

orientation = portrait
fullscreen = 0

android.permissions = INTERNET
android.api = 33
android.minapi = 26
android.ndk = 25b
android.archs = arm64-v8a

[buildozer]
log_level = 2
warn_on_root = 1
