# -*- coding: utf-8 -*-
"""
result_view.py — 结果三视图：JSON 树 / 原始文本 / 图片预览

自动模式：若输出里出现图片路径则显示图片，否则是合法 JSON 就上树，否则显示原始文本。
"""

from __future__ import annotations

import json
import os
import re

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QLabel,
    QPlainTextEdit,
    QStackedWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

_IMG_RE = re.compile(
    r"(?:[A-Za-z]:\\[^\s\"'<>|]+|/[^\s\"'<>|]+)\.(?:png|jpg|jpeg|bmp|gif)", re.I
)


class ResultView(QStackedWidget):
    """结果展示器"""

    MODE_AUTO = 0
    MODE_JSON = 1
    MODE_RAW = 2

    def __init__(self, parent=None):
        super().__init__(parent)

        # 0: 占位提示
        self._hint = QLabel("运行命令后，结果显示在这里")
        self._hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._hint.setProperty("role", "hint")
        self.addWidget(self._hint)

        # 1: JSON 树
        self._tree = QTreeWidget()
        self._tree.setHeaderHidden(True)
        self._tree.setAlternatingRowColors(False)
        self._tree.setUniformRowHeights(True)
        self.addWidget(self._tree)

        # 2: 原始文本
        self._text = QPlainTextEdit()
        self._text.setReadOnly(True)
        self._text.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        self.addWidget(self._text)

        # 3: 图片
        self._img_holder = QWidget()
        iv = QVBoxLayout(self._img_holder)
        iv.setContentsMargins(8, 8, 8, 8)
        self._img = QLabel()
        self._img.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._img.setMinimumHeight(200)
        iv.addWidget(self._img)
        self.addWidget(self._img_holder)

    # ---- 对外接口 -----------------------------------------------------------

    def clear_view(self):
        self._tree.clear()
        self._text.clear()
        self._img.clear()
        self.setCurrentIndex(0)

    def show_running(self, text: str):
        """运行中的实时输出"""
        self._text.setPlainText(text)
        if self.currentIndex() != 2:
            self.setCurrentIndex(2)
        sb = self._text.verticalScrollBar()
        sb.setValue(sb.maximum())

    def render(self, stdout: str, stderr: str, mode: int = MODE_AUTO):
        combined = stdout or ""
        if stderr:
            combined = (combined + "\n" + stderr) if combined else stderr

        if mode == self.MODE_RAW:
            self._show_text(combined)
            return

        # 自动/JSON：先找图片
        if mode == self.MODE_AUTO:
            img = self._detect_image(stdout)
            if img and self._show_image(img):
                return

        parsed = self._try_json(stdout)
        if parsed is not None and mode in (self.MODE_AUTO, self.MODE_JSON):
            self._show_json(parsed)
        else:
            self._show_text(combined)

    # ---- 内部 ---------------------------------------------------------------

    def _detect_image(self, text: str) -> str | None:
        if not text:
            return None
        m = _IMG_RE.search(text)
        return m.group(0) if m else None

    def _show_image(self, path: str) -> bool:
        if not os.path.isfile(path):
            return False
        pm = QPixmap(path)
        if pm.isNull():
            return False
        self._img.setPixmap(pm)
        self.setCurrentIndex(3)
        return True

    def _show_text(self, text: str):
        self._text.setPlainText(text)
        self.setCurrentIndex(2)

    def _show_json(self, value):
        self._tree.clear()
        self._build_tree(None, value, depth=0)
        self._tree.expandToDepth(1)
        self.setCurrentIndex(1)

    def _build_tree(self, parent, value, depth: int, key: str | None = None):
        if isinstance(value, dict):
            item = self._make_item(parent, key, f"{{…}} {len(value)} 项", depth)
            for k, v in value.items():
                self._build_tree(item, v, depth + 1, str(k))
        elif isinstance(value, list):
            item = self._make_item(parent, key, f"[…] {len(value)} 项", depth)
            for i, v in enumerate(value):
                self._build_tree(item, v, depth + 1, f"[{i}]")
        else:
            item = self._make_item(parent, key, self._scalar(value), depth, leaf=True)
        return item

    def _make_item(self, parent, key, text, depth, leaf=False):
        label = text if key is None else f"{key}:  {text}"
        item = QTreeWidgetItem([label])
        if leaf:
            item.setForeground(0, self._leaf_brush(text))
        if parent is None:
            self._tree.addTopLevelItem(item)
        else:
            parent.addChild(item)
        return item

    @staticmethod
    def _scalar(v):
        if v is None:
            return "null"
        if isinstance(v, bool):
            return "true" if v else "false"
        if isinstance(v, str):
            return json.dumps(v, ensure_ascii=False)
        return str(v)

    @staticmethod
    def _leaf_brush(text: str):
        from PyQt6.QtGui import QBrush, QColor

        if text == "null":
            return QBrush(QColor("#6b7488"))
        if text in ("true", "false"):
            return QBrush(QColor("#a371f7"))
        if text.startswith('"'):
            return QBrush(QColor("#a5e075"))
        return QBrush(QColor("#f0a45d"))

    @staticmethod
    def _try_json(text: str):
        if not text:
            return None
        t = text.strip()
        if not t or t[0] not in "{[":
            return None
        try:
            return json.loads(t)
        except Exception:  # noqa: BLE001
            return None

    def export_text(self, stdout: str, stderr: str) -> str:
        out = stdout or ""
        if stderr:
            out += "\n--- stderr ---\n" + stderr
        return out
