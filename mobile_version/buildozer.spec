[app]
title = Flashcards
package.name = flashcards
package.domain = com.flashcards

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,txt,xlsx
source.exclude_dirs = tests,__pycache__,.venv,.pytest_cache

version = 1.0.0

# python3,kivy must come first; sqlite3 is a built-in and must NOT be listed
requirements = python3,kivy==2.3.0,pillow,requests,certifi,charset-normalizer,idna,urllib3,anthropic,httpx,httpcore,anyio,sniffio,h11,typing_extensions,pydantic,pydantic_core,distro,jiter,annotated_types,openpyxl,et_xmlfile,plyer

[buildozer]
log_level = 2
warn_on_root = 1

[app:android]
android.permissions = INTERNET
android.api = 33
android.minapi = 26
android.ndk = 25b
android.sdk = 33
android.archs = arm64-v8a

orientation = portrait
fullscreen = 0
