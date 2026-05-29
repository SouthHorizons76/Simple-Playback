from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

BACKGROUND  = "#0d0d0d"
SURFACE     = "#1a1a1a"
SURFACE2    = "#252525"
SURFACE3    = "#2e2e2e"
ACCENT      = "#4a9eff"
ACCENT_DIM  = "#2a6ecf"
TEXT        = "#e8e8e8"
TEXT_DIM    = "#777777"
BORDER      = "#333333"
DANGER      = "#ff4a4a"

FONT_FAMILY     = "Segoe UI"
FONT_SIZE_SM    = 10
FONT_SIZE_MD    = 11

CONTROLS_HEIGHT = 76
SEEK_GROOVE_H   = 4

STYLESHEET = f"""
QWidget {{
    background-color: {BACKGROUND};
    color: {TEXT};
    font-family: "{FONT_FAMILY}";
    font-size: {FONT_SIZE_MD}pt;
    border: none;
    outline: none;
}}

QMainWindow {{
    background-color: {BACKGROUND};
}}

/* Controls bar background */
#controls_bar {{
    background-color: {SURFACE};
    border-top: 1px solid {BORDER};
}}

/* Play/pause and frame step buttons */
#btn_frame_back, #btn_play_pause, #btn_frame_fwd {{
    background-color: transparent;
    color: {TEXT};
    font-size: 16pt;
    min-width: 36px;
    max-width: 36px;
    min-height: 36px;
    max-height: 36px;
    border-radius: 18px;
    padding: 0px;
}}
#btn_frame_back:hover, #btn_play_pause:hover, #btn_frame_fwd:hover {{
    background-color: {SURFACE2};
}}
#btn_frame_back:pressed, #btn_play_pause:pressed, #btn_frame_fwd:pressed {{
    background-color: {SURFACE3};
}}

/* Speed buttons */
.speed_btn {{
    background-color: {SURFACE2};
    color: {TEXT_DIM};
    font-size: 9pt;
    min-width: 38px;
    max-width: 38px;
    min-height: 22px;
    max-height: 22px;
    border-radius: 4px;
    padding: 0px 4px;
}}
.speed_btn:hover {{
    background-color: {SURFACE3};
    color: {TEXT};
}}
.speed_btn[active="true"] {{
    background-color: {ACCENT_DIM};
    color: {TEXT};
}}

/* Zoom buttons */
#btn_zoom_out, #btn_zoom_in {{
    background-color: {SURFACE2};
    color: {TEXT};
    font-size: 14pt;
    min-width: 26px;
    max-width: 26px;
    min-height: 22px;
    max-height: 22px;
    border-radius: 4px;
    padding: 0px;
}}
#btn_zoom_out:hover, #btn_zoom_in:hover {{
    background-color: {SURFACE3};
}}

/* Zoom label */
#lbl_zoom {{
    color: {TEXT_DIM};
    font-size: 9pt;
    min-width: 40px;
    max-width: 40px;
    qproperty-alignment: AlignCenter;
}}

/* Volume button */
#btn_volume {{
    background-color: transparent;
    color: {TEXT_DIM};
    font-size: 12pt;
    min-width: 26px;
    max-width: 26px;
    min-height: 26px;
    max-height: 26px;
    border-radius: 4px;
    padding: 0px;
}}
#btn_volume:hover {{
    color: {TEXT};
    background-color: {SURFACE2};
}}

/* Volume slider */
#slider_volume {{
    min-width: 70px;
    max-width: 70px;
}}
#slider_volume::groove:horizontal {{
    height: 3px;
    background: {SURFACE3};
    border-radius: 2px;
}}
#slider_volume::sub-page:horizontal {{
    background: {TEXT_DIM};
    border-radius: 2px;
}}
#slider_volume::handle:horizontal {{
    background: {TEXT};
    width: 10px;
    height: 10px;
    margin: -4px 0;
    border-radius: 5px;
}}

/* Time label */
#lbl_time {{
    color: {TEXT_DIM};
    font-size: 9pt;
    font-family: "Consolas", "Courier New", monospace;
    min-width: 130px;
    max-width: 130px;
    qproperty-alignment: AlignRight | AlignVCenter;
}}

/* Seek slider */
#seek_slider::groove:horizontal {{
    height: {SEEK_GROOVE_H}px;
    background: {SURFACE3};
    border-radius: 2px;
}}
#seek_slider::sub-page:horizontal {{
    background: {ACCENT};
    border-radius: 2px;
}}
#seek_slider::handle:horizontal {{
    background: {TEXT};
    width: 12px;
    height: 12px;
    margin: -4px 0;
    border-radius: 6px;
}}
#seek_slider::handle:horizontal:hover {{
    background: {ACCENT};
    width: 14px;
    height: 14px;
    margin: -5px 0;
    border-radius: 7px;
}}

/* Drop overlay */
#drop_overlay {{
    background-color: {BACKGROUND};
    color: {TEXT_DIM};
}}

/* Menu bar */
QMenuBar {{
    background-color: {SURFACE};
    color: {TEXT};
    padding: 2px;
    border-bottom: 1px solid {BORDER};
}}
QMenuBar::item:selected {{
    background-color: {SURFACE2};
    border-radius: 3px;
}}
QMenu {{
    background-color: {SURFACE};
    color: {TEXT};
    border: 1px solid {BORDER};
    padding: 4px 0;
}}
QMenu::item {{
    padding: 5px 24px;
}}
QMenu::item:selected {{
    background-color: {SURFACE2};
}}
QMenu::separator {{
    height: 1px;
    background: {BORDER};
    margin: 3px 8px;
}}

/* Scrollbar (rarely visible but good to style) */
QScrollBar:vertical {{
    background: {SURFACE};
    width: 8px;
}}
QScrollBar::handle:vertical {{
    background: {SURFACE3};
    border-radius: 4px;
    min-height: 20px;
}}
"""


def apply_app_palette(app: QApplication) -> None:
    palette = QPalette()
    bg = QColor(BACKGROUND)
    surface = QColor(SURFACE)
    text = QColor(TEXT)
    text_dim = QColor(TEXT_DIM)
    accent = QColor(ACCENT)

    palette.setColor(QPalette.Window, bg)
    palette.setColor(QPalette.WindowText, text)
    palette.setColor(QPalette.Base, surface)
    palette.setColor(QPalette.AlternateBase, QColor(SURFACE2))
    palette.setColor(QPalette.ToolTipBase, surface)
    palette.setColor(QPalette.ToolTipText, text)
    palette.setColor(QPalette.Text, text)
    palette.setColor(QPalette.Button, surface)
    palette.setColor(QPalette.ButtonText, text)
    palette.setColor(QPalette.BrightText, text)
    palette.setColor(QPalette.Link, accent)
    palette.setColor(QPalette.Highlight, accent)
    palette.setColor(QPalette.HighlightedText, text)
    palette.setColor(QPalette.PlaceholderText, text_dim)

    palette.setColor(QPalette.Disabled, QPalette.WindowText, text_dim)
    palette.setColor(QPalette.Disabled, QPalette.Text, text_dim)
    palette.setColor(QPalette.Disabled, QPalette.ButtonText, text_dim)

    app.setPalette(palette)
    app.setStyleSheet(STYLESHEET)
