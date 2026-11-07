# -*- coding: utf-8 -*-
"""
REA Panel 启动入口

直接运行：  python main.py
打包 exe ：  pyinstaller --clean -F -w -n REA-Panel main.py
"""

from __future__ import annotations

import os
import sys

# 让 app 包可被导入（打包后路径处理）
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

from app.main_window import MainWindow


def main() -> int:
    # 高 DPI 适配（Qt6 默认已开启，这里仅设置舍入策略）
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("REA Panel")
    app.setOrganizationName("local.rea.panel")

    icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "icon.ico")
    if os.path.isfile(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    win = MainWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
