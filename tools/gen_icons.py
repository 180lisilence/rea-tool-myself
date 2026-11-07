# -*- coding: utf-8 -*-
"""生成安卓应用图标（各密度 PNG），输出到 res/mipmap-*/ic_launcher.png"""
import os

from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QBrush, QColor, QFont, QImage, QLinearGradient, QPainter, QPainterPath
from PyQt6.QtWidgets import QApplication

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(os.path.dirname(HERE), "res")

# 密度 -> 尺寸
DENSITIES = {
    "mipmap-mdpi": 48,
    "mipmap-hdpi": 72,
    "mipmap-xhdpi": 96,
    "mipmap-xxhdpi": 144,
    "mipmap-xxxhdpi": 192,
}


def render(size: int) -> QImage:
    img = QImage(size, size, QImage.Format.Format_ARGB32)
    img.fill(Qt.GlobalColor.transparent)

    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setRenderHint(QPainter.RenderHint.TextAntialiasing)

    r = size * 0.20
    path = QPainterPath()
    path.addRoundedRect(QRectF(0, 0, size, size), r, r)

    grad = QLinearGradient(0, 0, size, size)
    grad.setColorAt(0.0, QColor("#1b2740"))
    grad.setColorAt(1.0, QColor("#0d0f14"))
    p.fillPath(path, QBrush(grad))

    pen_w = max(1.0, size * 0.03)
    p.setPen(QColor("#4c8dff"))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawRoundedRect(QRectF(pen_w / 2, pen_w / 2, size - pen_w, size - pen_w), r, r)

    f = QFont("Roboto", int(size * 0.28))
    f.setBold(True)
    p.setFont(f)
    p.setPen(QColor("#4c8dff"))
    p.drawText(QRectF(0, -size * 0.03, size, size), Qt.AlignmentFlag.AlignCenter, "REA")

    p.setPen(Qt.PenStyle.NoPen)
    d = size * 0.065
    for i, col in enumerate(("#3fb950", "#d29922", "#f85149")):
        p.setBrush(QColor(col))
        p.drawEllipse(QRectF(size * (0.36 + i * 0.105), size * 0.735, d, d))

    p.end()
    return img


def main():
    app = QApplication([])  # noqa: F841
    total = 0
    for folder, size in DENSITIES.items():
        d = os.path.join(RES, folder)
        os.makedirs(d, exist_ok=True)
        img = render(size)
        out = os.path.join(d, "ic_launcher.png")
        img.save(out, "PNG")
        total += 1
        print(f"  {folder}/ic_launcher.png  {size}x{size}")
    print(f"共 {total} 个图标")


if __name__ == "__main__":
    main()
