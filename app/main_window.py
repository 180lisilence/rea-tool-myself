# -*- coding: utf-8 -*-
"""
main_window.py — REA Panel 主窗口

布局：
  ┌─ 顶栏：品牌 / 命令搜索 / 环境徽章 / 自检 / 停止 ────────────┐
  │ 左：命令树  │  中：参数表单（schema 自动生成）  │ 右：结果三视图 │
  └─ 底部：运行日志 ────────────────────────────────────────┘
"""

from __future__ import annotations

import os
import time

from PyQt6.QtCore import QThread, Qt, pyqtSignal
from PyQt6.QtGui import QAction, QFont, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from . import rea_backend as rb
from .result_view import ResultView
from .schema_form import SchemaForm
from .theme import DARK_QSS

# 命令分类规则（顺序即优先级）
GROUPS: list[tuple[str, object]] = [
    ("总览 / 能力", lambda n: n in {"analyze", "capabilities", "doctor", "compare"}),
    ("JavaScript / Electron",
     lambda n: any(k in n for k in ("javascript", "electron", "web-bundle", "web-capture",
                                    "web-screenshot", "wasm"))),
    ("Android / ADB", lambda n: any(k in n for k in ("adb", "android", "apk"))),
    ("原生 / 二进制",
     lambda n: any(k in n for k in ("native", "binary", "file-offset", "annotate", "managed",
                                    "process", "cutter", "gdb", "objdump", "macho", "plist",
                                    "signature", "demangle", "architecture", "dispatch"))),
    ("浏览器自动化",
     lambda n: any(k in n for k in ("browser", "playwright", "page", "origin", "screenshot"))),
    ("比对 / 差分", lambda n: n.startswith("compare")),
    ("其他", lambda n: True),
]


def group_of(name: str) -> str:
    for label, test in GROUPS:
        if test(name):
            return label
    return "其他"


# ---------------------------------------------------------------- 执行线程


class RunWorker(QThread):
    """在后台线程执行 rea 命令并流式回传输出"""

    chunk = pyqtSignal(str)
    finished_ok = pyqtSignal(dict)

    def __init__(self, env: rb.ReaEnv, args: list[str], cwd: str | None = None):
        super().__init__()
        self.env = env
        self.args = args
        self.cwd = cwd
        self._stop = False

    def stop(self):
        self._stop = True

    def run(self):  # noqa: D102
        res = rb.run_stream(
            self.env,
            self.args,
            on_output=lambda t: self.chunk.emit(t),
            should_stop=lambda: self._stop,
            cwd=self.cwd,
        )
        self.finished_ok.emit(res)


class FetchWorker(QThread):
    """后台拉取命令索引或 schema，避免阻塞 UI"""

    done = pyqtSignal(object)

    def __init__(self, fn, *args):
        super().__init__()
        self._fn = fn
        self._args = args

    def run(self):  # noqa: D102
        try:
            self.done.emit(self._fn(*self._args))
        except Exception as e:  # noqa: BLE001
            self.done.emit({"error": f"{type(e).__name__}: {e}"})


# ---------------------------------------------------------------- 主窗口


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("REA Panel — 逆向工程控制台")
        self.resize(1460, 920)
        self.setMinimumSize(1080, 660)

        self.env = rb.resolve_rea()
        self.commands: list[dict] = []
        self.active_cmd: str | None = None
        self.active_schema: dict | None = None
        self.worker: RunWorker | None = None
        self.last_result: dict | None = None
        self.run_seq = 0

        self.setStyleSheet(DARK_QSS)
        self._build_ui()
        self._wire_shortcuts()
        self._bootstrap()

    # ---------------------------------------------------------- UI 搭建

    def _build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        outer.addWidget(self._build_topbar())

        split = QSplitter(Qt.Orientation.Horizontal)
        split.addWidget(self._build_left())
        split.addWidget(self._build_mid())
        split.addWidget(self._build_right())
        split.setSizes([280, 460, 700])
        split.setStretchFactor(0, 0)
        split.setStretchFactor(1, 3)
        split.setStretchFactor(2, 4)
        outer.addWidget(split, 1)

        outer.addWidget(self._build_log())

        self.statusBar().showMessage("就绪")

    def _build_topbar(self) -> QWidget:
        bar = QFrame()
        bar.setObjectName("TopBar")
        bar.setFixedHeight(52)
        h = QHBoxLayout(bar)
        h.setContentsMargins(14, 8, 14, 8)
        h.setSpacing(12)

        logo = QLabel("REA")
        logo.setObjectName("BrandLogo")
        sub = QLabel("逆向工程控制台")
        sub.setObjectName("BrandSub")
        h.addWidget(logo)
        h.addWidget(sub)

        h.addStretch(1)

        self.search = QLineEdit()
        self.search.setPlaceholderText("搜索命令…（Ctrl+F 聚焦，Esc 清空）")
        self.search.setFixedWidth(420)
        self.search.textChanged.connect(self._filter_commands)
        h.addWidget(self.search)

        h.addStretch(1)

        self.env_badge = QLabel("检测中…")
        self.env_badge.setProperty("role", "muted")
        self.env_badge.setToolTip(self.env.describe())
        h.addWidget(self.env_badge)

        self.btn_doctor = QPushButton("自检")
        self.btn_doctor.setProperty("role", "mini")
        self.btn_doctor.clicked.connect(self._run_doctor)
        h.addWidget(self.btn_doctor)

        self.btn_stop = QPushButton("停止")
        self.btn_stop.setProperty("role", "danger")
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self._stop_run)
        h.addWidget(self.btn_stop)

        return bar

    def _pane_head(self, title: str) -> tuple[QFrame, QHBoxLayout]:
        head = QFrame()
        head.setObjectName("PaneHead")
        head.setFixedHeight(38)
        h = QHBoxLayout(head)
        h.setContentsMargins(12, 6, 12, 6)
        h.setSpacing(8)
        lbl = QLabel(title)
        lbl.setProperty("role", "paneTitle")
        h.addWidget(lbl)
        h.addStretch(1)
        return head, h

    def _build_left(self) -> QWidget:
        pane = QWidget()
        v = QVBoxLayout(pane)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)

        head, h = self._pane_head("命令")
        self.cmd_count = QLabel("0")
        self.cmd_count.setProperty("role", "muted")
        h.addWidget(self.cmd_count)
        v.addWidget(head)

        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setIndentation(12)
        self.tree.itemClicked.connect(self._on_tree_click)
        v.addWidget(self.tree, 1)
        return pane

    def _build_mid(self) -> QWidget:
        pane = QWidget()
        v = QVBoxLayout(pane)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)

        head, h = self._pane_head("未选择命令")
        self.mid_title = head.findChild(QLabel)
        self.btn_run = QPushButton("运行 ▶")
        self.btn_run.setProperty("role", "primary")
        self.btn_run.setEnabled(False)
        self.btn_run.clicked.connect(self._run_command)
        h.addWidget(self.btn_run)
        v.addWidget(head)

        body = QWidget()
        bv = QVBoxLayout(body)
        bv.setContentsMargins(12, 10, 12, 10)
        bv.setSpacing(10)

        self.cmd_summary = QLabel("")
        self.cmd_summary.setWordWrap(True)
        self.cmd_summary.setProperty("role", "muted")
        bv.addWidget(self.cmd_summary)

        # 命令行预览（等宽、可选中复制）
        self.cmdline = QLineEdit()
        self.cmdline.setReadOnly(True)
        self.cmdline.setPlaceholderText("rea …")
        bv.addWidget(self.cmdline)

        self.form = SchemaForm()
        self.form.changed.connect(self._update_cmdline)
        bv.addWidget(self.form, 1)

        v.addWidget(body, 1)
        return pane

    def _build_right(self) -> QWidget:
        pane = QWidget()
        v = QVBoxLayout(pane)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)

        head, h = self._pane_head("结果")
        self.exit_badge = QLabel("")
        self.exit_badge.setProperty("role", "muted")
        h.addWidget(self.exit_badge)

        self.view_mode = QComboBox()
        self.view_mode.addItem("自动", ResultView.MODE_AUTO)
        self.view_mode.addItem("JSON 树", ResultView.MODE_JSON)
        self.view_mode.addItem("原始文本", ResultView.MODE_RAW)
        self.view_mode.setFixedWidth(96)
        self.view_mode.currentIndexChanged.connect(self._refresh_result)
        h.addWidget(self.view_mode)

        self.btn_export = QPushButton("导出")
        self.btn_export.setProperty("role", "mini")
        self.btn_export.setEnabled(False)
        self.btn_export.clicked.connect(self._export_result)
        h.addWidget(self.btn_export)

        v.addWidget(head)

        self.result = ResultView()
        v.addWidget(self.result, 1)
        return pane

    def _build_log(self) -> QWidget:
        pane = QWidget()
        pane.setFixedHeight(150)
        v = QVBoxLayout(pane)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)

        head, h = self._pane_head("日志")
        self.log_status = QLabel("就绪")
        self.log_status.setProperty("role", "muted")
        h.addWidget(self.log_status)
        btn_clear = QPushButton("清空")
        btn_clear.setProperty("role", "mini")
        btn_clear.clicked.connect(lambda: self.log_view.clear())
        h.addWidget(btn_clear)
        v.addWidget(head)

        self.log_view = QPlainTextEdit()
        self.log_view.setObjectName("LogView")
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumBlockCount(5000)
        v.addWidget(self.log_view, 1)
        return pane

    def _wire_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+F"), self, lambda: self.search.setFocus())
        QShortcut(QKeySequence("Ctrl+Return"), self, self._run_command)
        QShortcut(QKeySequence("Ctrl+Enter"), self, self._run_command)
        act = QAction(self)
        act.setShortcut(QKeySequence("F5"))
        act.triggered.connect(self._run_command)
        self.addAction(act)

    # ---------------------------------------------------------- 启动流程

    def _bootstrap(self):
        self.log(f"REA Panel 启动")
        self.log(f"执行环境: {self.env.describe()}  [{self.env.kind}]")
        self.env_badge.setText("rea 就绪" if self.env.kind != "bare" else "rea (PATH)")
        self._load_commands()

    def _load_commands(self):
        self.worker_fetch = FetchWorker(rb.list_commands, self.env)
        self.worker_fetch.done.connect(self._on_commands)
        self.worker_fetch.start()

    def _on_commands(self, cmds):
        if isinstance(cmds, dict) and cmds.get("error"):
            self.log(f"命令索引加载失败：{cmds['error']}", "err")
            return
        self.commands = cmds
        self.cmd_count.setText(str(len(cmds)))
        self._render_tree()
        self.log(f"加载命令 {len(cmds)} 个", "ok")

    # ---------------------------------------------------------- 命令树

    def _render_tree(self, keyword: str = ""):
        self.tree.clear()
        kw = keyword.strip().lower()
        buckets: dict[str, list[dict]] = {}

        for c in self.commands:
            if kw and kw not in c["name"].lower() and kw not in c["summary"].lower():
                continue
            buckets.setdefault(group_of(c["name"]), []).append(c)

        bold = QFont()
        bold.setBold(True)

        for label, _ in GROUPS:
            items = buckets.get(label)
            if not items:
                continue
            grp = QTreeWidgetItem([f"{label}  ({len(items)})"])
            grp.setFont(0, bold)
            grp.setForeground(0, self._brush("#6b7488"))
            grp.setFlags(grp.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            self.tree.addTopLevelItem(grp)

            for c in items:
                child = QTreeWidgetItem([c["name"]])
                child.setToolTip(0, f"{c['name']}\n{c['summary']}")
                child.setData(0, Qt.ItemDataRole.UserRole, c["name"])
                grp.addChild(child)

        self.tree.expandAll()
        if not self.tree.topLevelItemCount():
            self.tree.addTopLevelItem(QTreeWidgetItem(["无匹配命令"]))

    @staticmethod
    def _brush(color: str):
        from PyQt6.QtGui import QBrush, QColor

        return QBrush(QColor(color))

    def _filter_commands(self, text: str):
        self._render_tree(text)

    def _on_tree_click(self, item: QTreeWidgetItem, _col: int):
        name = item.data(0, Qt.ItemDataRole.UserRole)
        if name:
            self.select_command(name)

    # ---------------------------------------------------------- 选择命令

    def select_command(self, name: str):
        self.active_cmd = name
        self.active_schema = None
        self.last_result = None
        self.mid_title.setText(name)
        meta = next((c for c in self.commands if c["name"] == name), None)
        self.cmd_summary.setText(meta["summary"] if meta else "")
        self.btn_run.setEnabled(False)
        self.btn_export.setEnabled(False)
        self.exit_badge.setText("")
        self.result.clear_view()
        self.cmdline.setText("")

        self.worker_schema = FetchWorker(rb.get_schema, self.env, name)
        self.worker_schema.done.connect(self._on_schema)
        self.worker_schema.start()

    def _on_schema(self, schema):
        self.active_schema = schema
        self.form.build(self.active_cmd, schema)
        self.btn_run.setEnabled(True)
        self._update_cmdline()
        if isinstance(schema, dict) and schema.get("error"):
            self.log(f"schema({self.active_cmd}) 失败：{schema['error']}", "err")

    # ---------------------------------------------------------- 命令行预览

    def _update_cmdline(self):
        """实时预览命令行。必填项未填时不报错，用 <参数名> 占位显示。"""
        if not self.active_cmd:
            return
        try:
            args = self.form.collect_args()
            text = "rea " + " ".join([self.active_cmd, *args])
        except ValueError as e:
            # 必填未填：展示已填部分 + 占位符提示
            name = str(e).split("：")[-1] if "：" in str(e) else "?"
            partial = self._collect_lenient()
            shown = self.active_cmd
            if partial:
                shown += " " + " ".join(partial)
            text = f"rea {shown} <{name}>    ← 必填项待填写"
        self.cmdline.setText(text)

    def _collect_lenient(self) -> list[str]:
        """宽容版参数收集：跳过校验，只取已填值（用于预览）。"""
        out: list[str] = []
        for r in self.form.rows:
            try:
                from PyQt6.QtWidgets import QCheckBox

                if isinstance(r.widget, QCheckBox):
                    if r.widget.isChecked():
                        out.append(f"--{r.key}")
                    continue
                val = r.value()
                if val is None:
                    continue
                if r.kind == "arg":
                    out.append(str(val))
                else:
                    out.append(f"--{r.key}")
                    out.append(str(val))
            except Exception:  # noqa: BLE001
                continue
        return out


    # ---------------------------------------------------------- 执行

    def _run_command(self):
        if not self.active_cmd or self.worker is not None:
            return
        try:
            args = [self.active_cmd, *self.form.collect_args()]
        except ValueError as e:
            self.log(str(e), "err")
            QMessageBox.warning(self, "参数不完整", str(e))
            return

        self.run_seq += 1
        self.result.clear_view()
        self.btn_run.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.btn_export.setEnabled(False)
        self.exit_badge.setText("")
        self.statusBar().showMessage("运行中…")
        self.log(f"▶ rea {' '.join(args)}")

        self._t0 = time.time()
        self._buf = ""

        self.worker = RunWorker(self.env, args)
        self.worker.chunk.connect(self._on_chunk)
        self.worker.finished_ok.connect(self._on_done)
        self.worker.start()

    def _on_chunk(self, text: str):
        self._buf += text
        self.result.show_running(self._buf)

    def _on_done(self, res: dict):
        self.worker = None
        self.btn_run.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.btn_export.setEnabled(True)

        ms = int((time.time() - self._t0) * 1000)
        self.last_result = res
        code = res.get("code", -1)

        if res.get("error"):
            self.exit_badge.setText(f"错误 · {ms}ms")
            self.log(f"✘ {res['error']}", "err")
            self.statusBar().showMessage("失败")
        elif code == 0:
            self.exit_badge.setText(f"退出码 0 · {ms}ms")
            self.log(f"✔ 完成，用时 {ms}ms", "ok")
            self.statusBar().showMessage("完成")
        else:
            self.exit_badge.setText(f"退出码 {code} · {ms}ms")
            self.log(f"✘ 失败，退出码 {code}", "err")
            self.statusBar().showMessage("失败")

        self._refresh_result()

    def _stop_run(self):
        if self.worker is not None:
            self.worker.stop()
            self.log("已发送停止信号", "err")
            self.statusBar().showMessage("已停止")

    def _refresh_result(self):
        if not self.last_result:
            return
        mode = self.view_mode.currentData()
        self.result.render(
            self.last_result.get("stdout", ""),
            self.last_result.get("stderr", ""),
            mode,
        )

    def _run_doctor(self):
        if self.worker is not None:
            return
        self.active_cmd = "doctor"
        self.mid_title.setText("doctor")
        args = ["doctor"]
        self.run_seq += 1
        self.result.clear_view()
        self.btn_stop.setEnabled(True)
        self.log("▶ rea doctor")
        self._t0 = time.time()
        self._buf = ""
        self.worker = RunWorker(self.env, args)
        self.worker.chunk.connect(self._on_chunk)
        self.worker.finished_ok.connect(self._on_done)
        self.worker.start()

    # ---------------------------------------------------------- 导出

    def _export_result(self):
        if not self.last_result:
            return
        content = self.result.export_text(
            self.last_result.get("stdout", ""), self.last_result.get("stderr", "")
        )
        default = f"rea-{self.active_cmd or 'output'}-{int(time.time())}.txt"
        path, _ = QFileDialog.getSaveFileName(self, "导出结果", default)
        if path:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(content)
                self.log(f"已导出：{path}", "ok")
            except Exception as e:  # noqa: BLE001
                self.log(f"导出失败：{e}", "err")

    # ---------------------------------------------------------- 日志

    def log(self, text: str, level: str = ""):
        ts = time.strftime("%H:%M:%S")
        line = f"[{ts}] {text}"
        if level:
            line += f"   <{level}>"
        self.log_view.appendPlainText(line)
        self.log_status.setText(text[:60])
        sb = self.log_view.verticalScrollBar()
        sb.setValue(sb.maximum())

    # ---------------------------------------------------------- 关闭

    def closeEvent(self, event):  # noqa: N802
        if self.worker is not None:
            self.worker.stop()
            self.worker.wait(2000)
        super().closeEvent(event)
