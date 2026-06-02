[app]
title = Soloist Cabin Pro
package.name = soloistcarbin
package.domain = org.soloist
source.dir = .
source.include_exts = py,png,ttf,atlas,kv,db
version = 1.0.0
requirements = python3,kivy==2.3.1,pillow
orientation = portrait
fullscreen = 0
android.archs = arm64-v8a
android.api = 33
android.minapi = 24
android.allow_backup = True
android.logcat_filters = *:S python:D
p4a.branch = master
android.accept_sdk_license = True
android.presplash_color = #FFF8E8
android.splash_color = #FFF8E8

[buildozer]
log_level = 2
warn_on_root = 1
