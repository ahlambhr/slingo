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

# -------- Requirements (Android-safe & minimal) --------
# Kivy + KivyMD + essentials. Keep this lean for a guaranteed build.
requirements = python3,kivy==2.3.0,kivymd,android,pyjnius,plyer,requests,urllib3,certifi,chardet,idna,pillow

# -------- Permissions --------
android.permissions = INTERNET, CAMERA, RECORD_AUDIO, READ_EXTERNAL_STORAGE, WRITE_EXTERNAL_STORAGE, FOREGROUND_SERVICE

# -------- Include your assets / data --------
# (Matches your repo)
include_patterns = assets/*,datapics/*,datavideos/*,dataset/*,fonts/*,models/*,screens/*,ui/*,*.json,*.kv

# -------- Android SDK/NDK --------
android.api = 33
android.minapi = 21
android.ndk = 23b
android.archs = arm64-v8a,armeabi-v7a
android.accept_sdk_license = True
android.build_tools_version = 33.0.2

# Optional: keep logs reasonable in CI
[buildozer]
log_level = 2
warn_on_root = 1
