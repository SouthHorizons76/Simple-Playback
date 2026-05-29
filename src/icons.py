"""SVG-based icon generators using Material Design paths (24x24 viewbox)."""
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtGui import QIcon, QPixmap, QPainter
from PySide6.QtCore import Qt, QByteArray

# Material Design icon path data
_PATHS = {
    "play":         "M8 5v14l11-7z",
    "pause":        "M6 19h4V5H6v14zm8-14v14h4V5h-4z",
    # Frame step: triangle + bar (skip_next / skip_previous style)
    "frame_fwd":    "M6 18l8.5-6L6 6v12zM16 6v12h2V6h-2z",
    "frame_back":   "M6 6h2v12H6zm3.5 6l8.5 6V6z",
    # File skip: double triangles (fast_forward / fast_rewind style)
    "next_file":    "M4 18l8.5-6L4 6v12zm9 0l8.5-6L13 6v12z",
    "prev_file":    "M11 18V6l-8.5 6 8.5 6zm.5-6l8.5 6V6l-8.5 6z",
    # Volume
    "volume":       "M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02z",
    "volume_off":   "M16.5 12c0-1.77-1.02-3.29-2.5-4.03v2.21l2.45 2.45c.03-.2.05-.41.05-.63zm2.5 0c0 .94-.2 1.82-.54 2.64l1.51 1.51C20.63 14.91 21 13.5 21 12c0-4.28-2.99-7.86-7-8.77v2.06c2.89.86 5 3.54 5 6.71zM4.27 3L3 4.27 7.73 9H3v6h4l5 5v-6.73l4.25 4.25c-.67.52-1.42.93-2.25 1.18v2.06c1.38-.31 2.63-.95 3.69-1.81L19.73 21 21 19.73l-9-9L4.27 3zM12 4L9.91 6.09 12 8.18V4z",
    # Folder open
    "open_folder":  "M10 4H4c-1.1 0-1.99.9-1.99 2L2 18c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2h-8l-2-2z",
    # Settings gear
    "settings":     "M19.14 12.94c.04-.3.06-.61.06-.94 0-.32-.02-.64-.07-.94l2.03-1.58c.18-.14.23-.41.12-.61l-1.92-3.32c-.12-.22-.37-.29-.59-.22l-2.39.96c-.5-.38-1.03-.7-1.62-.94l-.36-2.54c-.04-.24-.24-.41-.48-.41h-3.84c-.24 0-.43.17-.47.41l-.36 2.54c-.59.24-1.13.57-1.62.94l-2.39-.96c-.22-.08-.47 0-.59.22L2.74 8.87c-.12.21-.08.47.12.61l2.03 1.58c-.05.3-.09.63-.09.94s.02.64.07.94l-2.03 1.58c-.18.14-.23.41-.12.61l1.92 3.32c.12.22.37.29.59.22l2.39-.96c.5.38 1.03.7 1.62.94l.36 2.54c.05.24.24.41.48.41h3.84c.24 0 .44-.17.47-.41l.36-2.54c.59-.24 1.13-.56 1.62-.94l2.39.96c.22.08.47 0 .59-.22l1.92-3.32c.12-.22.07-.47-.12-.61l-2.01-1.58zM12 15.6c-1.98 0-3.6-1.62-3.6-3.6s1.62-3.6 3.6-3.6 3.6 1.62 3.6 3.6-1.62 3.6-3.6 3.6z",
    # Camera / screenshot
    "camera":       "M9 2L7.17 4H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2h-3.17L15 2H9zm3 15c-2.76 0-5-2.24-5-5s2.24-5 5-5 5 2.24 5 5-2.24 5-5 5zm0-8c-1.66 0-3 1.34-3 3s1.34 3 3 3 3-1.34 3-3-1.34-3-3-3z",
    # Headphones / audio tracks
    "headphones":   "M12 1c-4.97 0-9 4.03-9 9v7c0 1.66 1.34 3 3 3h3v-8H5v-2c0-3.87 3.13-7 7-7s7 3.13 7 7v2h-4v8h3c1.66 0 3-1.34 3-3v-7c0-4.97-4.03-9-9-9z",
}


def _make(path_d: str, color: str, size: int) -> QIcon:
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
        f'<path fill="{color}" d="{path_d}"/>'
        f'</svg>'
    )
    renderer = QSvgRenderer(QByteArray(svg.encode()))
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.Antialiasing)
    renderer.render(painter)
    painter.end()
    return QIcon(pix)


def get(name: str, color: str = "#e8e8e8", size: int = 20) -> QIcon:
    """Returns a QIcon by icon name. Raises KeyError if name is unknown."""
    return _make(_PATHS[name], color, size)


def app_icon() -> QIcon:
    """Multi-resolution app icon: play triangle on a dark circle."""
    icon = QIcon()
    for size in (16, 32, 48, 64, 128, 256):
        svg = (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
            f'<circle cx="12" cy="12" r="11" fill="#1a1a1a"/>'
            f'<path fill="#4a9eff" d="{_PATHS["play"]}"/>'
            f'</svg>'
        )
        renderer = QSvgRenderer(QByteArray(svg.encode()))
        pix = QPixmap(size, size)
        pix.fill(Qt.transparent)
        painter = QPainter(pix)
        painter.setRenderHint(QPainter.Antialiasing)
        renderer.render(painter)
        painter.end()
        icon.addPixmap(pix)
    return icon
