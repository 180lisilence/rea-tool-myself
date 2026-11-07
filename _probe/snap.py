# -*- coding: utf-8 -*-
"""启动 GUI、等待加载完成后自动截图保存，然后退出。用于界面验证。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication

from app.main_window import MainWindow

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "shot")


def main():
    os.makedirs(OUT, exist_ok=True)
    app = QApplication(sys.argv)
    win = MainWindow()
    win.resize(1460, 920)
    win.show()

    state = {"p": 0, "shots": 0}

    def tick():
        p = state["p"]
        if p == 0 and win.commands:
            win.resize(1460, 920)
            win.grab().save(os.path.join(OUT, "01_tree.png"))
            state["shots"] += 1
            win.select_command("analyze")
            state["p"] = 1
        elif p == 1 and win.active_schema is not None and win.form.rows:
            for r in win.form.rows:
                if r.key == "path" and hasattr(r.widget, "setText"):
                    r.widget.setText(r"E:\reaproject\apk\room")
                    break
            win._update_cmdline()
            QTimer.singleShot(400, snap_form)
            state["p"] = 2

    def snap_form():
        win.grab().save(os.path.join(OUT, "02_form.png"))
        state["shots"] += 1
        win.view_mode.setCurrentIndex(0)
        win._run_doctor()
        QTimer.singleShot(6000, snap_result)

    def snap_result():
        win.grab().save(os.path.join(OUT, "03_result.png"))
        state["shots"] += 1
        print(f"SHOTS: {state['shots']} -> {OUT}")
        app.quit()

    t = QTimer()
    t.timeout.connect(tick)
    t.start(300)
    app.exec()


if __name__ == "__main__":
    main()
