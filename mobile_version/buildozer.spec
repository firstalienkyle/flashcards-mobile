[app]
title = Flashcards
package.name = flashcards
package.domain = com.flashcards

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,db,txt,xlsx

version = 1.0.0

requirements = python3,kivy==2.3.0,anthropic,requests,openpyxl,plyer,pillow,sqlite3,certifi,charset-normalizer,idna,urllib3,httpx,httpcore,anyio,sniffio,h11,typing-extensions,pydantic,pydantic-core,distro,jiter,annotated-types,et-xmlfile

# Entry point
entrypoint = main.py

[buildozer]
log_level = 2
warn_on_root = 1

[app:android]
android.permissions = INTERNET
android.api = 33
android.minapi = 26
android.ndk = 25b
android.sdk = 33
android.archs = arm64-v8a, armeabi-v7a

# Keep screen on during review
android.wakelock = False

orientation = portrait

fullscreen = 0
