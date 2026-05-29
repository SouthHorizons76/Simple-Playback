from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QSlider,
    QPushButton, QLabel, QSizePolicy, QFrame,
)
from PySide6.QtGui import QMouseEvent

from .theme import CONTROLS_HEIGHT
from . import icons

_SEEK_RESOLUTION = 1000  # ticks per second
_SPEED_VALUES = [0.25, 0.5, 1.0, 2.0, 4.0]
_SPEED_LABELS = ["0.25×", "0.5×", "1×", "2×", "4×"]
_ICON_SIZE    = 20   # px for transport icons
_ICON_SIZE_SM = 18   # px for file-nav icons (slightly smaller to differentiate)


def _fmt_time(seconds: float) -> str:
    seconds = max(0.0, seconds)
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h}:{m:02d}:{s:02d}" if h > 0 else f"{m:02d}:{s:02d}"


def _icon_btn(object_name: str, icon_name: str, tooltip: str,
              icon_size: int = _ICON_SIZE, btn_size: int = 36) -> QPushButton:
    btn = QPushButton()
    btn.setObjectName(object_name)
    btn.setToolTip(tooltip)
    btn.setIcon(icons.get(icon_name, size=icon_size))
    from PySide6.QtCore import QSize
    btn.setIconSize(QSize(icon_size, icon_size))
    btn.setFixedSize(btn_size, btn_size)
    btn.setStyleSheet(
        f"QPushButton#{object_name} {{"
        "  background: transparent;"
        "  border-radius: 18px;"
        "  border: none;"
        "}"
        f"QPushButton#{object_name}:hover {{ background: #252525; }}"
        f"QPushButton#{object_name}:pressed {{ background: #2e2e2e; }}"
    )
    return btn


class SeekSlider(QSlider):
    seek_requested = Signal(float)  # absolute seconds

    def __init__(self, parent=None):
        super().__init__(Qt.Horizontal, parent)
        self.setObjectName("seek_slider")
        self.setRange(0, 0)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setFixedHeight(20)
        self._user_seeking = False
        self._duration = 0.0

    def set_duration(self, seconds: float):
        self._duration = max(0.0, seconds)
        self.setRange(0, int(self._duration * _SEEK_RESOLUTION))

    def set_position(self, seconds: float):
        if not self._user_seeking and self._duration > 0:
            self.blockSignals(True)
            self.setValue(int(seconds * _SEEK_RESOLUTION))
            self.blockSignals(False)

    def set_to_end(self):
        if not self._user_seeking:
            self.blockSignals(True)
            self.setValue(self.maximum())
            self.blockSignals(False)

    def _seek_at_ratio(self, ratio: float):
        ratio = max(0.0, min(1.0, ratio))
        value = int(ratio * self.maximum())
        self.blockSignals(True)
        self.setValue(value)
        self.blockSignals(False)
        self.seek_requested.emit(ratio * self._duration)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self._user_seeking = True
            self._seek_at_ratio(event.position().x() / max(self.width(), 1))
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._user_seeking:
            self._seek_at_ratio(event.position().x() / max(self.width(), 1))
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self._user_seeking = False
            event.accept()
        else:
            super().mouseReleaseEvent(event)


class ControlsBar(QWidget):
    """
    Layout (left → right):
    [prev_file] [frame_back] [play/pause] [frame_fwd] [next_file]
    | seek (stretch) | speed buttons | zoom − label + | vol icon slider | time
    """

    play_pause_clicked    = Signal()
    frame_back_clicked    = Signal()
    frame_forward_clicked = Signal()
    prev_file_clicked     = Signal()
    next_file_clicked     = Signal()
    seek_requested        = Signal(float)
    speed_changed         = Signal(float)
    zoom_in_clicked       = Signal()
    zoom_out_clicked      = Signal()
    volume_changed        = Signal(int)
    mute_toggled          = Signal(bool)
    audio_btn_clicked     = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("controls_bar")
        self.setFixedHeight(CONTROLS_HEIGHT)
        self._duration = 0.0
        self._muted = False
        self._current_speed_idx = 2  # default 1×
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Seek bar (full width, above controls)
        self._seek = SeekSlider()
        self._seek.seek_requested.connect(self.seek_requested)
        root.addWidget(self._seek)

        # Controls row
        row = QHBoxLayout()
        row.setContentsMargins(8, 0, 10, 0)
        row.setSpacing(2)

        # --- File navigation + transport ---
        self._btn_prev_file = _icon_btn(
            "btn_prev_file", "prev_file",
            "Previous file  (P)", _ICON_SIZE_SM, 30
        )
        self._btn_prev_file.clicked.connect(self.prev_file_clicked)
        row.addWidget(self._btn_prev_file)

        self._btn_frame_back = _icon_btn(
            "btn_frame_back", "frame_back",
            "Previous frame  (←)", _ICON_SIZE, 36
        )
        self._btn_frame_back.clicked.connect(self.frame_back_clicked)
        row.addWidget(self._btn_frame_back)

        self._btn_play = _icon_btn(
            "btn_play_pause", "play",
            "Play / Pause  (Space)", _ICON_SIZE, 36
        )
        self._btn_play.clicked.connect(self.play_pause_clicked)
        row.addWidget(self._btn_play)

        self._btn_frame_fwd = _icon_btn(
            "btn_frame_fwd", "frame_fwd",
            "Next frame  (→)", _ICON_SIZE, 36
        )
        self._btn_frame_fwd.clicked.connect(self.frame_forward_clicked)
        row.addWidget(self._btn_frame_fwd)

        self._btn_next_file = _icon_btn(
            "btn_next_file", "next_file",
            "Next file  (N)", _ICON_SIZE_SM, 30
        )
        self._btn_next_file.clicked.connect(self.next_file_clicked)
        row.addWidget(self._btn_next_file)

        row.addSpacing(6)

        # Time label
        self._lbl_time = QLabel("00:00 / 00:00")
        self._lbl_time.setObjectName("lbl_time")
        row.addWidget(self._lbl_time)

        # Spacer — stretches to fill gap before speed buttons
        row.addStretch(1)

        # --- Speed buttons ---
        self._speed_btns: list[QPushButton] = []
        for i, label in enumerate(_SPEED_LABELS):
            btn = QPushButton(label)
            btn.setProperty("class", "speed_btn")
            btn.setToolTip(f"Playback speed {label}")
            btn.setProperty("active", "false")
            idx = i
            btn.clicked.connect(lambda checked=False, i=idx: self._on_speed_clicked(i))
            self._speed_btns.append(btn)
            row.addWidget(btn)
        self._set_active_speed(self._current_speed_idx)

        row.addSpacing(10)

        # --- Zoom controls ---
        self._btn_zoom_out = QPushButton("−")
        self._btn_zoom_out.setObjectName("btn_zoom_out")
        self._btn_zoom_out.setToolTip("Zoom out  (−)")
        self._btn_zoom_out.clicked.connect(self.zoom_out_clicked)
        row.addWidget(self._btn_zoom_out)

        self._lbl_zoom = QLabel("100%")
        self._lbl_zoom.setObjectName("lbl_zoom")
        row.addWidget(self._lbl_zoom)

        self._btn_zoom_in = QPushButton("+")
        self._btn_zoom_in.setObjectName("btn_zoom_in")
        self._btn_zoom_in.setToolTip("Zoom in  (=)")
        self._btn_zoom_in.clicked.connect(self.zoom_in_clicked)
        row.addWidget(self._btn_zoom_in)

        row.addSpacing(6)

        # --- Audio tracks ---
        self._btn_audio = _icon_btn(
            "btn_audio", "headphones",
            "Audio Tracks", _ICON_SIZE_SM, 28
        )
        self._btn_audio.clicked.connect(self.audio_btn_clicked)
        row.addWidget(self._btn_audio)

        row.addSpacing(6)

        # --- Volume ---
        self._btn_vol = QPushButton()
        self._btn_vol.setObjectName("btn_volume")
        self._btn_vol.setIcon(icons.get("volume", size=_ICON_SIZE_SM))
        from PySide6.QtCore import QSize
        self._btn_vol.setIconSize(QSize(_ICON_SIZE_SM, _ICON_SIZE_SM))
        self._btn_vol.setFixedSize(28, 28)
        self._btn_vol.setToolTip("Mute / Unmute")
        self._btn_vol.clicked.connect(self._on_mute_clicked)
        row.addWidget(self._btn_vol)

        self._slider_vol = QSlider(Qt.Horizontal)
        self._slider_vol.setObjectName("slider_volume")
        self._slider_vol.setRange(0, 100)
        self._slider_vol.setValue(100)
        self._slider_vol.setToolTip("Volume")
        self._slider_vol.valueChanged.connect(self.volume_changed)
        row.addWidget(self._slider_vol)

        root.addLayout(row)

    # ------------------------------------------------------------------
    # Update slots
    # ------------------------------------------------------------------

    def update_position(self, seconds: float):
        self._seek.set_position(seconds)
        self._lbl_time.setText(f"{_fmt_time(seconds)} / {_fmt_time(self._duration)}")

    def update_duration(self, seconds: float):
        self._duration = seconds
        self._seek.set_duration(seconds)
        self._lbl_time.setText(f"00:00 / {_fmt_time(seconds)}")

    def update_pause_state(self, paused: bool):
        icon_name = "play" if paused else "pause"
        self._btn_play.setIcon(icons.get(icon_name, size=_ICON_SIZE))

    def update_eof(self):
        self._seek.set_to_end()
        self._btn_play.setIcon(icons.get("play", size=_ICON_SIZE))

    def update_zoom_label(self, zoom_level: float):
        pct = int(round(2.0 ** zoom_level * 100))
        self._lbl_zoom.setText(f"{pct}%")

    def set_speed_display(self, factor: float):
        for i, val in enumerate(_SPEED_VALUES):
            if abs(val - factor) < 0.001:
                self._set_active_speed(i)
                return
        for btn in self._speed_btns:
            btn.setProperty("active", "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _on_speed_clicked(self, index: int):
        self._set_active_speed(index)
        self.speed_changed.emit(_SPEED_VALUES[index])

    def _set_active_speed(self, index: int):
        self._current_speed_idx = index
        for i, btn in enumerate(self._speed_btns):
            btn.setProperty("active", "true" if i == index else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def _on_mute_clicked(self):
        self._muted = not self._muted
        icon_name = "volume_off" if self._muted else "volume"
        self._btn_vol.setIcon(icons.get(icon_name, size=_ICON_SIZE_SM))
        self.mute_toggled.emit(self._muted)
