[app]
title = Slingo
package.name = slingo
package.domain = com.ahlambhr

# Project layout
source.dir = .
source.include_exts = py,kv,png,jpg,ttf,json
entrypoint = main.py

version = 0.1
orientation = portrait
fullscreen = 0

# ---- Runtime requirements (TensorFlow included) ----
requirements = python3,kivy,opencv-python,numpy,pillow,arabic_reshaper,python-bidi,pytesseract,pdf2image,tensorflow,scikit-learn,mediapipe,SpeechRecognition

# ---- Permissions ----
android.permissions = CAMERA, RECORD_AUDIO, INTERNET, WRITE_EXTERNAL_STORAGE, READ_EXTERNAL_STORAGE

# ---- Android toolchain settings ----
android.api = 31            
android.minapi = 21
android.build_tools_version = 33.0.2
android.ndk = 23b
android.archs = arm64-v8a, armeabi-v7a

# Buildozer/p4a will use the SDK we install in the workflow
android.sdk_path = /opt/android-sdk
android.accept_sdk_license = True

# ---- Assets to include ----
include_patterns = screens/*, ui/*, fonts/*, models/*, *.json

# (Optional) Add your icon later to this path
icon.filename = %(source.dir)s/data/icon.png

android.allow_backup = True
android.debug = 1

[buildozer]
log_level = 2
warn_on_root = 1

# Force Buildozer/p4a to use the modern sdkmanager path (workflow also creates a legacy symlink)
android.sdkmanager_path = /opt/android-sdk/cmdline-tools/tools/bin/sdkmanager
