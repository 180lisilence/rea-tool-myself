# -*- coding: utf-8 -*-
"""
schema_form.py — 由 REA 的 JSON Schema 自动生成 Qt 参数表单

REA 的 --schema 输出形如：
{
  "args":    { "type":"object", "properties": {...}, "required": [...] },
  "options": { "type":"object", "properties": {...} }
}

本模块把每个 property 映射成合适的 Qt 控件：
  enum     -> QComboBox
  boolean  -> QCheckBox（= flag）
  integer  -> QSpinBox
  number   -> QDoubleSpinBox
  array    -> QLineEdit（JSON 数组语法）
  string   -> QLineEdit  （路径类字段带「浏览…」按钮）
"""

from __future__ import annotations

import json
import re

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

# 路径类字段的启发式判定
_PATH_HINT = re.compile(r"path|file|dir|input|output|jar|exe|apk|db|snapshot|target", re.I)
_DIR_HINT = re.compile(r"dir|directory|folder", re.I)


class FieldRow:
    """描述一个已生成的表单行，便于回读取值"""

    def __init__(self, key: str, kind: str, ftype: str, widget, section: str):
        self.key = key
        self.kind = kind        # 'arg' | 'opt'
        self.ftype = ftype
        self.widget = widget
        self.section = section

    def value(self):
        """返回该行的原始值；None 表示「未设置」"""
        w = self.widget
        if isinstance(w, QCheckBox):
            return w.isChecked()
        if isinstance(w, QComboBox):
            return w.currentData()
        if isinstance(w, (QSpinBox, QDoubleSpinBox)):
            return None if w.value() == w.minimum() and w.specialValueText() else w.value()
        if isinstance(w, QLineEdit):
            t = w.text().strip()
            return t or None
        return None


class SchemaForm(QWidget):
    """参数表单容器"""

    changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.rows: list[FieldRow] = []
        self._outer = QVBoxLayout(self)
        self._outer.setContentsMargins(0, 0, 0, 0)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._outer.addWidget(self._scroll)

        self._body = QWidget()
        self._scroll.setWidget(self._body)
        self._body_layout = QVBoxLayout(self._body)
        self._body_layout.setContentsMargins(0, 0, 0, 0)
        self._body_layout.setSpacing(12)

        self._placeholder = QLabel("← 从左侧选择一个命令")
        self._placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._placeholder.setProperty("role", "hint")
        self._body_layout.addWidget(self._placeholder)

    # ---- 构建 ---------------------------------------------------------------

    def build(self, command: str, schema: dict):
        """按 schema 重建表单"""
        self.rows.clear()
        self._clear_body()

        if not schema or "error" in schema:
            msg = "该命令无可用参数定义，可直接运行。"
            if schema and schema.get("error"):
                msg = f"Schema 读取失败：{schema['error']}\n仍可直接运行。"
            lbl = QLabel(msg)
            lbl.setWordWrap(True)
            lbl.setProperty("role", "hint")
            self._body_layout.addWidget(lbl)
            self._body_layout.addStretch(1)
            return

        args = schema.get("args") or {}
        options = schema.get("options") or {}

        arg_props = args.get("properties") or {}
        opt_props = options.get("properties") or {}
        required = args.get("required") or []

        if arg_props:
            self._add_section("位置参数", arg_props, required, "arg")
        if opt_props:
            self._add_section(f"选项参数（{len(opt_props)}）", opt_props, [], "opt")

        if not arg_props and not opt_props:
            lbl = QLabel("该命令无参数，可直接运行。")
            lbl.setProperty("role", "hint")
            self._body_layout.addWidget(lbl)

        self._body_layout.addStretch(1)
        self.changed.emit()

    def _clear_body(self):
        while self._body_layout.count():
            item = self._body_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

    def _add_section(self, title: str, props: dict, required: list, kind: str):
        box = QFrame()
        box.setProperty("role", "section")
        v = QVBoxLayout(box)
        v.setContentsMargins(12, 10, 12, 12)
        v.setSpacing(8)

        head = QLabel(title)
        head.setProperty("role", "sectionTitle")
        v.addWidget(head)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
        form.setFormAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        form.setHorizontalSpacing(14)
        form.setVerticalSpacing(12)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.DontWrapRows)

        for key, spec in props.items():
            widget = self._make_widget(key, spec, kind)
            label = self._make_label(key, spec, key in required)
            label.setMinimumWidth(150)
            label.setMaximumWidth(150)
            if isinstance(widget, QCheckBox):
                # 布尔：标签放右侧，行内排布
                form.addRow("", widget)
            else:
                form.addRow(label, widget)

            self.rows.append(FieldRow(key, kind, spec.get("type", "string"), widget, title))

        v.addLayout(form)
        self._body_layout.addWidget(box)

    def _make_label(self, key: str, spec: dict, required: bool) -> QWidget:
        holder = QWidget()
        v = QVBoxLayout(holder)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(1)

        top = QLabel(("＊ " if required else "") + key)
        top.setProperty("role", "fieldLabel")
        v.addWidget(top)

        if spec.get("description"):
            d = QLabel(spec["description"])
            d.setWordWrap(True)
            d.setProperty("role", "fieldDesc")
            v.addWidget(d)
        return holder

    def _make_widget(self, key: str, spec: dict, kind: str):
        ftype = spec.get("type", "string")
        enum = spec.get("enum")

        # --- 枚举 ---
        if enum:
            cb = QComboBox()
            cb.addItem("— 未设置 —", None)
            for v in enum:
                cb.addItem(str(v), str(v))
            cb.currentIndexChanged.connect(self.changed)
            return cb

        # --- 布尔 ---
        if ftype == "boolean":
            cb = QCheckBox(key)
            cb.toggled.connect(self.changed)
            return cb

        # --- 整数 ---
        if ftype == "integer":
            sp = QSpinBox()
            sp.setRange(-(2**31), 2**31 - 1)
            sp.setSpecialValueText("—")
            sp.setValue(sp.minimum())
            sp.valueChanged.connect(self.changed)
            return sp

        # --- 浮点 ---
        if ftype == "number":
            sp = QDoubleSpinBox()
            sp.setRange(-1e12, 1e12)
            sp.setDecimals(6)
            sp.setSpecialValueText("—")
            sp.setValue(sp.minimum())
            sp.valueChanged.connect(self.changed)
            return sp

        # --- 路径类字符串：带浏览按钮 ---
        if ftype == "string" and _PATH_HINT.search(key):
            holder = QWidget()
            h = QHBoxLayout(holder)
            h.setContentsMargins(0, 0, 0, 0)
            h.setSpacing(6)
            le = QLineEdit()
            le.setPlaceholderText("绝对路径")
            le.textChanged.connect(self.changed)
            h.addWidget(le, 1)

            btn = QPushButton("浏览…")
            btn.setProperty("role", "mini")

            def pick(_=False, line=le, k=key):
                if _DIR_HINT.search(k):
                    p = QFileDialog.getExistingDirectory(self, f"选择 {k}")
                else:
                    p, _f = QFileDialog.getOpenFileName(self, f"选择 {k}")
                if p:
                    line.setText(p)

            btn.clicked.connect(pick)
            h.addWidget(btn)
            return holder

        # --- 默认：字符串 ---
        le = QLineEdit()
        if spec.get("default") is not None:
            le.setText(str(spec["default"]))
        if ftype == "array":
            le.setPlaceholderText('JSON 数组，如 ["a","b"]')
        le.textChanged.connect(self.changed)
        return le

    # ---- 回读 ---------------------------------------------------------------

    def collect_args(self) -> list[str]:
        """把表单值转成 CLI 参数数组。抛 ValueError 表示必填缺失。"""
        out: list[str] = []
        opts: list[tuple[str, str | None]] = []

        for r in self.rows:
            if isinstance(r.widget, QCheckBox):
                if r.widget.isChecked():
                    opts.append((r.key, None))  # flag，无值
                continue

            val = r.value()
            if val is None:
                if r.kind == "arg" and self._is_required_shown(r):
                    raise ValueError(f"必填参数未填写：{r.key}")
                continue

            if r.ftype == "array":
                try:
                    arr = json.loads(str(val))
                    if isinstance(arr, list):
                        for item in arr:
                            opts.append((r.key, str(item)))
                        continue
                except Exception:  # noqa: BLE001
                    pass
                opts.append((r.key, str(val)))
                continue

            if r.kind == "arg":
                out.append(str(val))
            else:
                opts.append((r.key, str(val)))

        for k, v in opts:
            out.append(f"--{k}")
            if v is not None:
                out.append(v)
        return out

    def _is_required_shown(self, row: FieldRow) -> bool:
        # 简化处理：位置参数缺值即视为必填未填（REA 的 arg 基本都是必填）
        return row.kind == "arg"
