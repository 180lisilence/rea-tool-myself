# -*- coding: utf-8 -*-
"""真实窗口模式截图（验证字体渲染正常）"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication

from app.main_window import MainWindow

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "shot_real")


def main():
    os.makedirs(OUT, exist_ok=True)
    app = QApplication(sys.argv)

    from PyQt6.QtGui import QFontDatabase
    print("字体族总数:", len(QFontDatabase.families()))

    win = MainWindow()
    win.resize(1460, 920)
    win.show()

    st = {"p": 0}

    def tick():
        if st["p"] == 0 and win.commands:
            win.grab().save(os.path.join(OUT, "01_tree.png"))
            win.select_command("analyze")
            st["p"] = 1
        elif st["p"] == 1 and win.active_schema is not None and win.form.rows:
            for r in win.form.rows:
                if r.key == "path" and hasattr(r.widget, "setText"):
                    r.widget.setText(r"E:\reaproject\apk\room")
                    break
            win._update_cmdline()
            QTimer.singleShot(500, snap2)
            st["p"] = 2

    def snap2():
        win.grab().save(os.path.join(OUT, "02_form.png"))
        win._run_doctor()
        QTimer.singleShot(7000, snap3)

    def snap3():
        win.grab().save(os.path.join(OUT, "03_result.png"))
        # 切 JSON 视图
        win.view_mode.setCurrentIndex(1)
        win._refresh_result()
        QTimer.singleShot(600, snap4)

    def snap4():
        win.grab().save(os.path.join(OUT, "04_json.png"))
        print("DONE ->", OUT)
        app.quit()

    t = QTimer()
    t.timeout.connect(tick)
    t.start(300)
    app.exec()


if __name__ == "__main__":
    main()
