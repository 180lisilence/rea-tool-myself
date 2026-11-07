# -*- coding: utf-8 -*-
"""生成应用图标 assets/icon.ico（纯代码绘制，无需外部素材）"""
import os
import struct

from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QBrush, QColor, QFont, QImage, QLinearGradient, QPainter, QPainterPath
from PyQt6.QtWidgets import QApplication

HERE = os.path.dirname(os.path.abspath(__file__))


def render(size: int) -> QImage:
    img = QImage(size, size, QImage.Format.Format_ARGB32)
    img.fill(Qt.GlobalColor.transparent)

    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setRenderHint(QPainter.RenderHint.TextAntialiasing)

    # 圆角底板 + 渐变
    r = size * 0.22
    path = QPainterPath()
    path.addRoundedRect(QRectF(0, 0, size, size), r, r)
    grad = QLinearGradient(0, 0, size, size)
    grad.setColorAt(0.0, QColor("#1b2740"))
    grad.setColorAt(1.0, QColor("#0d0f14"))
    p.fillPath(path, QBrush(grad))

    # 边框光晕
    p.setPen(QColor("#4c8dff"))
    pen_w = max(1.0, size * 0.022)
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawRoundedRect(QRectF(pen_w / 2, pen_w / 2, size - pen_w, size - pen_w), r, r)

    # 文字 REA
    f = QFont("Consolas", int(size * 0.30))
    f.setBold(True)
    p.setFont(f)
    p.setPen(QColor("#4c8dff"))
    p.drawText(QRectF(0, -size * 0.04, size, size), Qt.AlignmentFlag.AlignCenter, "REA")

    # 底部小点装饰
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor("#3fb950"))
    d = size * 0.07
    p.drawEllipse(QRectF(size * 0.36, size * 0.74, d, d))
    p.setBrush(QColor("#d29922"))
    p.drawEllipse(QRectF(size * 0.465, size * 0.74, d, d))
    p.setBrush(QColor("#f85149"))
    p.drawEllipse(QRectF(size * 0.57, size * 0.74, d, d))

    p.end()
    return img


def main():
    app = QApplication([])  # noqa: F841
    out_dir = os.path.join(os.path.dirname(HERE), "assets")
    os.makedirs(out_dir, exist_ok=True)

    sizes = [16, 24, 32, 48, 64, 128, 256]
    imgs = [render(s) for s in sizes]

    # 写 PNG（供 Qt 运行时使用）
    imgs[-1].save(os.path.join(out_dir, "icon.png"), "PNG")

    # 手工组装多尺寸 ICO
    ico_path = os.path.join(out_dir, "icon.ico")
    pngs = []
    for im in imgs:
        from PyQt6.QtCore import QBuffer, QByteArray, QIODevice

        ba = QByteArray()
        buf = QBuffer(ba)
        buf.open(QIODevice.OpenModeFlag.WriteOnly)
        im.save(buf, "PNG")
        buf.close()
        pngs.append((im.width(), bytes(ba.data())))

    with open(ico_path, "wb") as f:
        # ICONDIR
        f.write(struct.pack("<HHH", 0, 1, len(pngs)))
        offset = 6 + 16 * len(pngs)
        entries = b""
        for w, data in pngs:
            dw = 0 if w >= 256 else w
            entries += struct.pack("<BBBBHHII", dw, dw, 0, 0, 1, 32, len(data), offset)
            offset += len(data)
        f.write(entries)
        for _w, data in pngs:
            f.write(data)

    print("icon.ico ->", ico_path, os.path.getsize(ico_path), "bytes")
    print("icon.png ->", os.path.join(out_dir, "icon.png"))


if __name__ == "__main__":
    main()
