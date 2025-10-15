[app]
title = Slingo
package.name = slingo
package.domain = com.ahlambhr
source.dir = .
source.include_exts = py,kv,png,jpg,ttf,json
version = 0.1
orientation = portrait
fullscreen = 0
entrypoint = main.py

requirements = python3,kivy,opencv-python,numpy,pillow,arabic_reshaper,python-bidi,pytesseract,pdf2image,tensorflow,scikit-learn,mediapipe,SpeechRecognition
android.permissions = CAMERA, RECORD_AUDIO, INTERNET, WRITE_EXTERNAL_STORAGE, READ_EXTERNAL_STORAGE

# ✅ Force stable Android SDK + Build-Tools
android.api = 33
android.minapi = 21
android.build_tools_version = 33.0.2
android.sdk_path = $HOME/android-sdk
android.ndk = 23b
android.archs = arm64-v8a, armeabi-v7a

# Assets
include_patterns = screens/*, ui/*, fonts/*, models/*, *.json

# Icon (add later)
icon.filename = %(source.dir)s/data/icon.png

# Debug mode build
android.debug = 1

[buildozer]
log_level = 2
warn_on_root = 1
