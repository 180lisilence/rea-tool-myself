# -*- coding: utf-8 -*-
"""theme.py — 深色主题（QSS）"""

DARK_QSS = """
* { outline: none; }

QWidget {
    background-color: #12141a;
    color: #e6e9f0;
    font-family: "Microsoft YaHei UI", "Segoe UI", sans-serif;
    font-size: 13px;
}

QMainWindow, QDialog { background-color: #0d0f14; }

/* ---------- 顶栏 ---------- */
#TopBar { background-color: #171a22; border-bottom: 1px solid #2a2f3d; }
#BrandLogo {
    color: #4c8dff; font-family: Consolas, monospace;
    font-size: 17px; font-weight: bold; letter-spacing: 1px;
}
#BrandSub { color: #6b7488; font-size: 11px; }

/* ---------- 输入 ---------- */
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QPlainTextEdit {
    background-color: #1e222c;
    border: 1px solid #2a2f3d;
    border-radius: 5px;
    padding: 5px 8px;
    color: #e6e9f0;
    selection-background-color: #2d5aa8;
    font-family: Consolas, "Cascadia Mono", monospace;
}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {
    border-color: #4c8dff;
}
QLineEdit::placeholder { color: #6b7488; }

QComboBox::drop-down { border: none; width: 18px; }
QComboBox QAbstractItemView {
    background-color: #1e222c; border: 1px solid #2a2f3d;
    selection-background-color: #2d5aa8; color: #e6e9f0;
}

/* ---------- 按钮 ---------- */
QPushButton {
    background-color: #1e222c;
    border: 1px solid #2a2f3d;
    border-radius: 6px;
    padding: 6px 14px;
    color: #e6e9f0;
}
QPushButton:hover:!disabled { background-color: #232836; border-color: #3a4256; }
QPushButton:disabled { color: #565f73; background-color: #171a22; }

QPushButton[role="primary"] {
    background-color: #4c8dff; border-color: #4c8dff;
    color: #06101f; font-weight: bold;
}
QPushButton[role="primary"]:hover:!disabled { background-color: #5f9bff; }
QPushButton[role="primary"]:disabled { background-color: #24314a; color: #5a6a85; }

QPushButton[role="danger"] {
    background-color: #2a1414; border-color: #5a2020; color: #f85149;
}
QPushButton[role="danger"]:hover:!disabled { background-color: #3a1a1a; }

QPushButton[role="mini"] {
    padding: 3px 10px; font-size: 12px;
}

/* ---------- 面板 ---------- */
#PaneHead {
    background-color: #171a22;
    border-bottom: 1px solid #22262f;
}
QLabel[role="paneTitle"] { color: #a8b0c2; font-weight: bold; font-size: 12px; }
QLabel[role="hint"] { color: #6b7488; padding: 18px; }
QLabel[role="muted"] { color: #6b7488; font-size: 11px; }

/* ---------- 命令树 ---------- */
QTreeWidget {
    background-color: #12141a;
    border: none;
    font-family: Consolas, "Cascadia Mono", monospace;
}
QTreeWidget::item { padding: 4px 6px; border-radius: 4px; color: #c8cede; }
QTreeWidget::item:hover { background-color: #1e222c; }
QTreeWidget::item:selected { background-color: #2d5aa8; color: #ffffff; }
QTreeWidget::branch { background: transparent; }

/* ---------- 表单 ---------- */
QFrame[role="section"] {
    background-color: #171a22;
    border: 1px solid #22262f;
    border-radius: 7px;
}
QLabel[role="sectionTitle"] {
    color: #6b7488; font-size: 11px;
    text-transform: uppercase; letter-spacing: 1px;
}
QLabel[role="fieldLabel"] { color: #a8b0c2; }
QLabel[role="fieldDesc"] { color: #6b7488; font-size: 11px; }

QCheckBox { color: #a8b0c2; }
QCheckBox::indicator {
    width: 15px; height: 15px;
    border: 1px solid #3a4256; border-radius: 3px;
    background-color: #1e222c;
}
QCheckBox::indicator:checked {
    background-color: #4c8dff; border-color: #4c8dff;
}

/* ---------- 结果 / 日志 ---------- */
QPlainTextEdit {
    font-family: Consolas, "Cascadia Mono", monospace;
    font-size: 12px; line-height: 1.5;
}
#LogView {
    background-color: #171a22;
    border: none; border-top: 1px solid #2a2f3d;
    font-size: 11.5px; color: #a8b0c2;
}

/* ---------- 状态条 ---------- */
QStatusBar { background-color: #171a22; color: #6b7488; }
QStatusBar::item { border: none; }

/* ---------- 分隔条 ---------- */
QSplitter::handle { background-color: #22262f; }
QSplitter::handle:horizontal { width: 3px; }
QSplitter::handle:hover { background-color: #2d5aa8; }

/* ---------- 滚动条 ---------- */
QScrollBar:vertical {
    background: transparent; width: 10px; margin: 0;
}
QScrollBar::handle:vertical {
    background: #2c3242; border-radius: 5px; min-height: 30px;
}
QScrollBar::handle:vertical:hover { background: #3a4256; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; }

QScrollBar:horizontal {
    background: transparent; height: 10px; margin: 0;
}
QScrollBar::handle:horizontal {
    background: #2c3242; border-radius: 5px; min-width: 30px;
}
QScrollBar::handle:horizontal:hover { background: #3a4256; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal { background: none; }

/* ---------- 提示气泡 ---------- */
QToolTip {
    background-color: #1e222c; color: #e6e9f0;
    border: 1px solid #3a4256; padding: 4px 6px;
}
"""
