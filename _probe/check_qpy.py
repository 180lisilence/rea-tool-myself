# -*- coding: utf-8 -*-
"""验证 PyQt6 + PyInstaller 可用性（不弹窗，仅检测 API 与版本）"""
import sys

print("python:", sys.version.split()[0], sys.executable)

try:
    from PyQt6.QtCore import QT_VERSION_STR, PYQT_VERSION_STR
    print("Qt:", QT_VERSION_STR, "PyQt:", PYQT_VERSION_STR)
except Exception as e:
    print("PyQt6 FAIL:", e)

try:
    from PyQt6.QtWebEngineWidgets import QWebEngineView  # noqa
    print("QtWebEngine: OK")
except Exception as e:
    print("QtWebEngine FAIL:", e)

try:
    from PyQt6.QtWidgets import QApplication, QMainWindow, QSplitter, QTreeWidget, QFormLayout  # noqa
    print("QtWidgets: OK")
except Exception as e:
    print("QtWidgets FAIL:", e)

try:
    import PyInstaller
    print("PyInstaller:", PyInstaller.__version__)
except Exception as e:
    print("PyInstaller FAIL:", e)
