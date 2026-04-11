[app]
title = Flashcards
package.name = flashcards
package.domain = com.flashcards

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,db

version = 1.0.0

requirements = python3,kivy,plyer,openpyxl,requests,certifi

orientation = portrait

android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE,VIBRATE,RECEIVE_BOOT_COMPLETED

android.api = 33
android.minapi = 21
android.ndk = 25b
android.ndk_api = 21
android.arch = arm64-v8a

[buildozer]
log_level = 2
warn_on_root = 1
