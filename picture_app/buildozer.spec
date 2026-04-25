[app]
title = Pictures
package.name = pictures
package.domain = com.pictures

source.dir = .
source.include_exts = py,png,jpg,jpeg,kv,atlas,txt
source.exclude_dirs = tests,__pycache__,.venv,.pytest_cache

version = 1.0.0

requirements = python3,kivy==2.3.0,pillow,plyer

orientation = portrait
fullscreen = 0

android.permissions = READ_EXTERNAL_STORAGE,READ_MEDIA_IMAGES
android.api = 33
android.minapi = 26
android.ndk = 25b
android.archs = arm64-v8a

[buildozer]
log_level = 2
warn_on_root = 1
