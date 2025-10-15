[app]
title = Slingo
package.name = slingo
package.domain = com.ahlambhr
source.dir = .
source.include_exts = py,kv,png,jpg,ttf,json
version = 0.1
orientation = portrait
fullscreen = 0

# Main Python file
entrypoint = main.py

# Permissions
android.permissions = CAMERA, RECORD_AUDIO, INTERNET, WRITE_EXTERNAL_STORAGE, READ_EXTERNAL_STORAGE

# Requirements
requirements = python3,kivy,opencv-python,numpy,pillow,arabic_reshaper,python-bidi,pytesseract,pdf2image,tensorflow,scikit-learn,mediapipe,SpeechRecognition

# Android specific settings
android.api = 31
android.minapi = 21
android.ndk = 23b
android.archs = arm64-v8a, armeabi-v7a
android.sdk = 20

# Add fonts folder
android.presplash_color = #FFFFFF
android.allow_backup = True
android.add_src = fonts

# Icon (you can add later)
icon.filename = %(source.dir)s/data/icon.png

# Code signing disabled for now
android.debug = 1

# Include these folders
include_patterns = screens/*, ui/*, fonts/*, models/*, *.json

[buildozer]
log_level = 2
warn_on_root = 1


