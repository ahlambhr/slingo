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

# ---- Minimal, Android-safe deps (KivyMD included) ----
# Keep this lean so CI builds reliably. Add more later if needed.
requirements = python3,kivy==2.2.1,kivymd,android,pyjnius,plyer,requests,urllib3,certifi,chardet,idna

# ---- Permissions ----
android.permissions = INTERNET, CAMERA, RECORD_AUDIO, READ_EXTERNAL_STORAGE, WRITE_EXTERNAL_STORAGE, FOREGROUND_SERVICE

# ---- Include your assets / data ----
include_patterns = assets/*,datapics/*,datavideos/*,dataset/*,fonts/*,models/*,screens/*,ui/*,*.json,*.kv

# ---- SDK/NDK / Architectures ----
android.api = 33
android.minapi = 21
android.ndk = 23b

# Build only one arch to reduce time/memory on GitHub runners
android.archs = arm64-v8a

android.accept_sdk_license = True
android.build_tools_version = 33.0.2

# ---- Optional p4a tuning (keeps memory lower) ----
# p4a.cflags = -O1
# p4a.bootstrap = sdl2

[buildozer]
log_level = 2
warn_on_root = 1
