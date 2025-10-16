[app]
title = Slingo
package.name = slingo
package.domain = com.ahlambhr
source.dir = .
source.include_exts = py,kv,png,jpg,ttf,json,txt
version = 0.1
orientation = portrait
fullscreen = 0
entrypoint = main.py

# Dependencies
requirements = python3,kivy,opencv-python,numpy,pillow,arabic_reshaper,python-bidi,pytesseract,pdf2image,tensorflow,scikit-learn,mediapipe,SpeechRecognition

# Permissions
android.permissions = CAMERA, RECORD_AUDIO, INTERNET, WRITE_EXTERNAL_STORAGE, READ_EXTERNAL_STORAGE

# Android SDK/NDK setup
android.api = 31
android.minapi = 21
android.ndk = 23b
android.archs = arm64-v8a, armeabi-v7a
android.sdk_path = /opt/android-sdk
android.accept_sdk_license = True
android.build_tools_version = 33.0.2

# Assets
include_patterns = fonts/*,screens/*,ui/*,models/*,*.json

# Debug APK only
android.debug = True

[buildozer]
log_level = 2
warn_on_root = 1
