"""Generates icons/app.ico using PySide6's SVG renderer (matches the runtime app_icon)."""
import os
import struct
import sys

from PySide6.QtCore import Qt, QByteArray, QBuffer, QIODevice
from PySide6.QtGui import QPainter, QImage
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QApplication

SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
    '<circle cx="12" cy="12" r="11" fill="#1a1a1a"/>'
    '<path fill="#4a9eff" d="M8 5v14l11-7z"/>'
    '</svg>'
)


def _render_png(size: int) -> bytes:
    renderer = QSvgRenderer(QByteArray(SVG.encode()))
    img = QImage(size, size, QImage.Format.Format_ARGB32)
    img.fill(Qt.transparent)
    painter = QPainter(img)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    renderer.render(painter)
    painter.end()

    buf = QBuffer()
    buf.open(QIODevice.OpenModeFlag.WriteOnly)
    ok = img.save(buf, "PNG")
    buf.close()
    if not ok:
        raise RuntimeError(f"Failed to save PNG at size {size}")
    return bytes(buf.data())


def _pack_ico(pngs: dict) -> bytes:
    sizes = sorted(pngs)
    n = len(sizes)
    header = struct.pack("<HHH", 0, 1, n)

    dir_bytes = b""
    data_bytes = b""
    offset = 6 + 16 * n

    for sz in sizes:
        png = pngs[sz]
        w = sz if sz < 256 else 0
        h = sz if sz < 256 else 0
        dir_bytes += struct.pack("<BBBBHHII", w, h, 0, 0, 1, 32, len(png), offset)
        data_bytes += png
        offset += len(png)

    return header + dir_bytes + data_bytes


def main():
    app = QApplication.instance() or QApplication(sys.argv)

    os.makedirs("icons", exist_ok=True)
    pngs = {sz: _render_png(sz) for sz in (16, 32, 48, 64, 128, 256)}
    ico = _pack_ico(pngs)

    with open("icons/app.ico", "wb") as f:
        f.write(ico)
    print("Generated icons/app.ico")


if __name__ == "__main__":
    main()
