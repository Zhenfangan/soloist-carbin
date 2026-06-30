[app]
title = Soloist Cabin Pro
package.name = soloistcarbin
package.domain = org.soloist
source.dir = .
source.include_exts = py,png,ttf,atlas,kv,db
version = 1.0.0
requirements = hostpython3==3.11.9,python3==3.11.9,kivy,pillow,cython==3.0.11,plyer,pyjnius
orientation = portrait
fullscreen = 0
android.permissions = INTERNET,CAMERA,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE
android.archs = arm64-v8a
android.api = 34
android.minapi = 24
android.allow_backup = True
android.logcat_filters = *:S python:D
android.accept_sdk_license = True
android.presplash_color = #FFF8E8
android.splash_color = #FFF8E8
p4a.branch = develop

[buildozer]
log_level = 2
warn_on_root = 0
