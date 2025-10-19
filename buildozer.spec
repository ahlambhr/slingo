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

# Minimal, Android-safe deps (fast & reliable)
requirements = python3,kivy==2.2.1,kivymd==1.1.1,android,pyjnius,plyer,requests,pillow,urllib3,certifi,chardet,idna

# Permissions
android.permissions = INTERNET, CAMERA, RECORD_AUDIO, READ_EXTERNAL_STORAGE, WRITE_EXTERNAL_STORAGE, FOREGROUND_SERVICE

# Package your assets & data
include_patterns = assets/*,datapics/*,datavideos/*,dataset/*,fonts/*,models/*,screens/*,ui/*,*.json,*.kv

# SDK/NDK/arch
android.api = 33
android.minapi = 21
android.ndk = 23b
android.archs = arm64-v8a
android.accept_sdk_license = True

[buildozer]
log_level = 2
warn_on_root = 1
