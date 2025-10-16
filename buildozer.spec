[app]
title = Slingo
package.name = slingo
package.domain = com.ahlambhr
source.dir = .
source.include_exts = py,kv,png,jpg,jpeg,ttf,json,txt,mp3,wav,xml
version = 0.1
orientation = portrait
fullscreen = 0
entrypoint = main.py

# ---- Python requirements (Android-safe) ----
# Keep this lean to ensure successful builds.
# If you need requests for APIs, it’s already included via 'requests'.
requirements = python3,kivy,android,pyjnius,plyer,requests,certifi,chardet,idna,urllib3,numpy,pillow

# ---- Android permissions ----
# Camera & mic for future features; Internet for APIs; storage for reading/writing JSON/media
android.permissions = CAMERA, RECORD_AUDIO, INTERNET, WRITE_EXTERNAL_STORAGE, READ_EXTERNAL_STORAGE, FOREGROUND_SERVICE

# ---- Include your assets / data ----
# These must match your repo
include_patterns = fonts/*,screens/*,ui/*,models/*,*.json

# ---- SDK/NDK / API Levels ----
android.api = 33
android.minapi = 21
android.ndk = 23b
android.archs = arm64-v8a,armeabi-v7a
android.accept_sdk_license = True
android.build_tools_version = 33.0.2

# ---- Java options (stable defaults) ----
# (you can uncomment and tweak if you need)
# android.add_jars =

# Build a debug APK (what the workflow outputs)
android.debug = True

# ---- Kivy graphics / window tweaks (optional) ----
# kivy.require = 2.3.0

[buildozer]
log_level = 2
warn_on_root = 1
