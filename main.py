"""APK 打包入口垫片。

python-for-android 硬性要求 source.dir 根目录下存在 main.py 作为应用入口。
本项目真正的入口在 app/main.py(包内),故此处转发，桌面端仍可用
`python -m app.main` 启动，两条路径互不影响。
"""

from app.main import main

if __name__ == "__main__":
    main()
