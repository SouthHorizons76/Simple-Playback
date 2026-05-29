import math
from PySide6.QtCore import Qt, Signal, QObject
from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QMouseEvent, QWheelEvent

try:
    import mpv
    MPV_AVAILABLE = True
except ImportError:
    MPV_AVAILABLE = False


ZOOM_STEP     = 0.5   # button / scroll-wheel zoom step
ZOOM_STEP_KEY = 0.1   # keyboard zoom step (fine-grained)
ZOOM_MIN  = -2.0   # 25%
ZOOM_MAX  = 4.0    # 1600%


def _clamp(val, lo, hi):
    return max(lo, min(hi, val))


class _Bridge(QObject):
    """Thread-safe signal bridge: MPV observer callbacks fire on MPV's thread."""
    time_changed          = Signal(float)
    duration_changed      = Signal(float)
    pause_changed         = Signal(bool)
    eof_reached           = Signal()
    audio_tracks_changed  = Signal(object)  # list[dict]


class MpvWidget(QWidget):
    """QWidget that embeds libmpv's renderer directly into its HWND on Windows."""

    # Public signals forwarded from the bridge
    time_changed          = Signal(float)
    duration_changed      = Signal(float)
    pause_changed         = Signal(bool)
    eof_reached           = Signal()
    zoom_changed          = Signal(float)   # current zoom level (log2)
    audio_tracks_changed  = Signal(object)  # list[dict]

    def __init__(self, parent=None):
        super().__init__(parent)

        # These three attributes are REQUIRED before passing winId() to MPV on Windows.
        # WA_NativeWindow forces Qt to allocate a real HWND immediately.
        # WA_PaintOnScreen + paintEngine()=None prevents Qt's own painter from
        # drawing over the surface that MPV owns.
        self.setAttribute(Qt.WA_NativeWindow, True)
        self.setAttribute(Qt.WA_PaintOnScreen, True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.setStyleSheet("background-color: black;")

        self._zoom_level: float = 0.0
        self._pan_x: float = 0.0
        self._pan_y: float = 0.0
        self._panning: bool = False
        self._pan_start = None
        self._pan_start_x: float = 0.0
        self._pan_start_y: float = 0.0

        self._bridge = _Bridge()
        self._bridge.time_changed.connect(self.time_changed)
        self._bridge.duration_changed.connect(self.duration_changed)
        self._bridge.pause_changed.connect(self.pause_changed)
        self._bridge.eof_reached.connect(self.eof_reached)
        self._bridge.audio_tracks_changed.connect(self.audio_tracks_changed)

        self._mpv = None
        if MPV_AVAILABLE:
            self._init_mpv()

    def _init_mpv(self):
        # Trigger native HWND creation before querying winId()
        self.winId()
        wid = int(self.winId())

        self._mpv = mpv.MPV(
            wid=str(wid),
            keep_open="yes",
            keep_open_pause="no",
            vo="gpu",
            hwdec="auto-safe",
            input_default_bindings=False,
            input_vo_keyboard=False,
            osc=False,
            config=False,
        )

        # Suppress MPV log output
        self._mpv.log_handler = lambda level, component, message: None

        # Property observers — these fire on MPV's internal event thread.
        # Emitting PySide6 signals from a non-Qt thread is safe; the connection
        # is automatically queued across the thread boundary.
        @self._mpv.property_observer("time-pos")
        def _on_time(name, value):
            if value is not None:
                self._bridge.time_changed.emit(float(value))

        @self._mpv.property_observer("duration")
        def _on_duration(name, value):
            if value is not None:
                self._bridge.duration_changed.emit(float(value))

        @self._mpv.property_observer("pause")
        def _on_pause(name, value):
            if value is not None:
                self._bridge.pause_changed.emit(bool(value))

        # Use the eof-reached property instead of the end-file event.
        # eof-reached becomes True only on natural end-of-file; it stays False
        # when a file is replaced via mpv.play(), so no spurious playlist advance.
        @self._mpv.property_observer("eof-reached")
        def _on_eof_reached(name, value):
            if value:
                self._bridge.eof_reached.emit()

        @self._mpv.property_observer("track-list")
        def _on_track_list(name, value):
            if value is not None:
                audio = [t for t in value if t.get("type") == "audio"]
                self._bridge.audio_tracks_changed.emit(audio)

    # ------------------------------------------------------------------
    # Qt overrides
    # ------------------------------------------------------------------

    def paintEngine(self):
        # Returning None tells Qt not to create a paint engine for this widget.
        # This is required when embedding a foreign renderer (MPV/D3D11) directly.
        return None

    def closeEvent(self, event):
        if self._mpv is not None:
            self._mpv.terminate()
        super().closeEvent(event)

    def sizeHint(self):
        from PySide6.QtCore import QSize
        return QSize(1280, 720)

    # ------------------------------------------------------------------
    # Mouse: zoom (wheel) and pan (drag)
    # ------------------------------------------------------------------

    def wheelEvent(self, event: QWheelEvent):
        if self._mpv is None:
            return
        steps = event.angleDelta().y() / 120.0
        new_zoom = _clamp(self._zoom_level + steps * ZOOM_STEP, ZOOM_MIN, ZOOM_MAX)
        if new_zoom != self._zoom_level:
            self._zoom_level = new_zoom
            self._mpv.video_zoom = self._zoom_level
            if self._zoom_level == 0.0:
                self._pan_x = 0.0
                self._pan_y = 0.0
                self._mpv.video_pan_x = 0.0
                self._mpv.video_pan_y = 0.0
            self.zoom_changed.emit(self._zoom_level)

    def mousePressEvent(self, event: QMouseEvent):
        if self._zoom_level > 0 and event.button() == Qt.LeftButton:
            self._panning = True
            self._pan_start = event.position()
            self._pan_start_x = self._pan_x
            self._pan_start_y = self._pan_y
            self.setCursor(Qt.ClosedHandCursor)
        event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._panning and self._pan_start is not None:
            delta = event.position() - self._pan_start
            w = max(self.width(), 1)
            h = max(self.height(), 1)
            pan_x = self._pan_start_x - delta.x() / w
            pan_y = self._pan_start_y - delta.y() / h
            # Clamp pan so the video edge cannot move past the widget edge
            max_pan = (1.0 - 1.0 / (2.0 ** self._zoom_level)) / 2.0 if self._zoom_level > 0 else 0.0
            pan_x = _clamp(pan_x, -max_pan, max_pan)
            pan_y = _clamp(pan_y, -max_pan, max_pan)
            self._pan_x = pan_x
            self._pan_y = pan_y
            if self._mpv:
                self._mpv.video_pan_x = pan_x
                self._mpv.video_pan_y = pan_y
        event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self._panning = False
            self._pan_start = None
            if self._zoom_level > 0:
                self.setCursor(Qt.OpenHandCursor)
            else:
                self.setCursor(Qt.ArrowCursor)
        event.accept()

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self.reset_zoom()
        event.accept()

    # ------------------------------------------------------------------
    # Playback API
    # ------------------------------------------------------------------

    def load_file(self, path: str):
        if self._mpv is None:
            return
        self._reset_zoom_state()
        try:
            self._mpv.command("set", "lavfi-complex", "")
        except Exception:
            pass
        self._mpv.play(path)

    def play(self):
        if self._mpv:
            self._mpv.pause = False

    def pause(self):
        if self._mpv:
            self._mpv.pause = True

    def toggle_pause(self):
        if self._mpv:
            self._mpv.pause = not self._mpv.pause

    def seek(self, seconds: float):
        if self._mpv:
            try:
                self._mpv.seek(seconds, "absolute")
            except Exception:
                pass

    def frame_step(self):
        if self._mpv:
            self._mpv.pause = True
            self._mpv.command("frame-step")

    def frame_back_step(self):
        if self._mpv:
            self._mpv.pause = True
            self._mpv.command("frame-back-step")

    def set_speed(self, factor: float):
        if self._mpv:
            self._mpv.speed = _clamp(factor, 0.01, 100.0)

    def set_volume(self, value: int):
        if self._mpv:
            self._mpv.volume = _clamp(value, 0, 100)

    def set_mute(self, muted: bool):
        if self._mpv:
            self._mpv.mute = muted

    def is_muted(self) -> bool:
        if self._mpv:
            return bool(self._mpv.mute)
        return False

    def export_frame(self, path: str):
        if self._mpv:
            try:
                self._mpv.command("screenshot-to-file", path, "video")
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Audio track API
    # ------------------------------------------------------------------

    def get_audio_tracks(self) -> list:
        if not self._mpv:
            return []
        try:
            tracks = self._mpv.track_list
            if tracks is None:
                return []
            return [t for t in tracks if t.get("type") == "audio"]
        except Exception:
            return []

    def set_audio_tracks(self, track_ids: list):
        """Select which audio tracks to play. Pass multiple IDs to mix them."""
        if not self._mpv:
            return
        if not track_ids:
            try:
                self._mpv.command("set", "lavfi-complex", "")
                self._mpv.command("set", "aid", "no")
            except Exception:
                pass
            return
        if len(track_ids) == 1:
            try:
                self._mpv.command("set", "lavfi-complex", "")
            except Exception:
                pass
            try:
                self._mpv.command("set", "aid", str(track_ids[0]))
            except Exception:
                pass
        else:
            # Mix multiple tracks via FFmpeg's amix filter
            n = len(track_ids)
            inputs = "".join(f"[aid{tid}]" for tid in track_ids)
            filter_str = f"{inputs}amix=inputs={n}[ao]"
            try:
                self._mpv.command("set", "lavfi-complex", filter_str)
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Zoom/pan API (called from PlayerWindow keyboard shortcuts too)
    # ------------------------------------------------------------------

    def set_zoom(self, level: float):
        self._zoom_level = _clamp(level, ZOOM_MIN, ZOOM_MAX)
        if self._mpv:
            self._mpv.video_zoom = self._zoom_level
        if self._zoom_level == 0.0:
            self._pan_x = 0.0
            self._pan_y = 0.0
            if self._mpv:
                self._mpv.video_pan_x = 0.0
                self._mpv.video_pan_y = 0.0
            self.setCursor(Qt.ArrowCursor)
        else:
            self.setCursor(Qt.OpenHandCursor)
        self.zoom_changed.emit(self._zoom_level)

    def zoom_in(self):
        self.set_zoom(self._zoom_level + ZOOM_STEP)

    def zoom_out(self):
        self.set_zoom(self._zoom_level - ZOOM_STEP)

    def zoom_in_key(self):
        self.set_zoom(self._zoom_level + ZOOM_STEP_KEY)

    def zoom_out_key(self):
        self.set_zoom(self._zoom_level - ZOOM_STEP_KEY)

    def reset_zoom(self):
        self.set_zoom(0.0)

    def get_zoom(self) -> float:
        return self._zoom_level

    # ------------------------------------------------------------------
    # State accessors
    # ------------------------------------------------------------------

    def get_position(self) -> float:
        if self._mpv:
            try:
                val = self._mpv.time_pos
                return float(val) if val is not None else 0.0
            except Exception:
                pass
        return 0.0

    def get_duration(self) -> float:
        if self._mpv:
            try:
                val = self._mpv.duration
                return float(val) if val is not None else 0.0
            except Exception:
                pass
        return 0.0

    def is_paused(self) -> bool:
        if self._mpv:
            try:
                return bool(self._mpv.pause)
            except Exception:
                pass
        return True

    def stop(self):
        if self._mpv:
            try:
                self._mpv.stop()
            except Exception:
                pass

    def is_available(self) -> bool:
        return MPV_AVAILABLE and self._mpv is not None

    def get_media_info(self) -> dict:
        if not self._mpv:
            return {}
        info = {}
        for attr, key in [
            ("duration",      "duration"),
            ("width",         "width"),
            ("height",        "height"),
            ("container_fps", "fps"),
            ("video_codec",   "video_codec"),
            ("audio_codec",   "audio_codec"),
            ("video_bitrate", "video_bitrate"),
            ("audio_bitrate", "audio_bitrate"),
            ("file_size",     "file_size"),
            ("metadata",      "tags"),
        ]:
            try:
                v = getattr(self._mpv, attr)
                if v is not None:
                    info[key] = v
            except Exception:
                pass
        return info

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _reset_zoom_state(self):
        self._zoom_level = 0.0
        self._pan_x = 0.0
        self._pan_y = 0.0
        self.setCursor(Qt.ArrowCursor)
