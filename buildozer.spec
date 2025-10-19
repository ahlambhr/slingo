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

# ---- Minimal, Android-safe deps (fast & reliable) ----
# KivyMD version pinned for stability with p4a in the Docker image.
requirements = python3,kivy==2.2.1,kivymd==1.1.1,android,pyjnius,plyer,requests,pillow,urllib3,certifi,chardet,idna

# ---- Permissions ----
android.permissions = INTERNET, CAMERA, RECORD_AUDIO, READ_EXTERNAL_STORAGE, WRITE_EXTERNAL_STORAGE, FOREGROUND_SERVICE

# ---- Include your assets / data ----
include_patterns = assets/*,datapics/*,datavideos/*,dataset/*,fonts/*,models/*,screens/*,ui/*,*.json,*.kv

# ---- SDK/NDK / Architectures ----
# Single-arch = faster CI and fewer link/memory issues.
android.api = 33
android.minapi = 21
android.ndk = 23b
android.archs = arm64-v8a
android.accept_sdk_license = True

# Use the default Gradle from the Docker image (stable).
# If you ever need pins, uncomment:
# android.gradle_plugin_version = 7.4.2
# android.gradle_version = 7.5

[buildozer]
log_level = 2
warn_on_root = 1
