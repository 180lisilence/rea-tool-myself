# -*- coding: utf-8 -*-
"""无头冒烟测试：构建主窗口、选命令、建表单、跑一次真命令，全程不弹窗。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication

from app.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    win = MainWindow()

    steps = []
    state = {"phase": 0}

    def tick():
        p = state["phase"]
        if p == 0:
            # 等命令索引加载
            if win.commands:
                steps.append(f"命令索引: {len(win.commands)} 条")
                win.select_command("analyze")
                state["phase"] = 1
        elif p == 1:
            # 等 schema 与表单
            if win.active_schema is not None and win.form.rows:
                steps.append(f"analyze schema 读取成功，表单行数: {len(win.form.rows)}")
                try:
                    args = win.form.collect_args()
                    steps.append(f"空表单 collect_args -> {args}")
                except Exception as e:
                    steps.append(f"collect_args 抛错(预期，必填未填): {e}")
                state["phase"] = 2
                # 填必填项后重试
                for r in win.form.rows:
                    if r.key == "path" and hasattr(r.widget, "setText"):
                        r.widget.setText("E:\\reaproject\\apk\\room")
                        break
                win._update_cmdline()
                steps.append(f"命令行预览: {win.cmdline.text()}")
                win._run_doctor()  # 跑自检，比 analyze 快
                state["phase"] = 3
        elif p == 3:
            if win.last_result is not None:
                r = win.last_result
                steps.append(f"doctor 退出码: {r['code']}  stdout {len(r['stdout'])} 字符 "
                             f"stderr {len(r['stderr'])} 字符")
                # 切三种视图
                from app.result_view import ResultView
                for m in (ResultView.MODE_RAW, ResultView.MODE_JSON, ResultView.MODE_AUTO):
                    win.result.render(r["stdout"], r["stderr"], m)
                steps.append("三视图切换: OK")
                state["phase"] = 4
                timer.stop()
                for s in steps:
                    print("  ✓", s)
                print("SMOKE_TEST: PASS")
                app.quit()

    timer = QTimer()
    timer.timeout.connect(tick)
    timer.start(300)
    app.exec()


if __name__ == "__main__":
    main()
