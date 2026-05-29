import os
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QStandardPaths
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QLabel,
    QFileDialog, QMenuBar, QMenu, QSizePolicy,
)
from PySide6.QtGui import QAction, QKeySequence, QShortcut, QDragEnterEvent, QDropEvent

from .mpv_widget import MpvWidget, ZOOM_STEP, ZOOM_MIN, ZOOM_MAX, _clamp
from .controls import ControlsBar
from .settings import Settings
from .shortcuts_dialog import ShortcutsDialog
from .playlist import Playlist, VIDEO_EXTENSIONS

_SPEED_MIN = 0.25
_SPEED_MAX = 4.0
_SPEED_STEP_FACTOR = 2.0
_CONTROLS_HIDE_DELAY_MS = 2000


class PlayerWindow(QMainWindow):

    def __init__(self, settings: Settings | None = None):
        super().__init__()
        self._settings = settings or Settings()
        self._playlist = Playlist()
        self._current_speed: float = 1.0
        self._is_fullscreen: bool = False
        self._shortcuts: dict[str, QShortcut] = {}

        self._hide_controls_timer = QTimer(self)
        self._hide_controls_timer.setSingleShot(True)
        self._hide_controls_timer.timeout.connect(self._hide_controls)

        self.setWindowTitle("Simple Playback")
        self.setAcceptDrops(True)
        self.setMinimumSize(480, 320)

        self._build_ui()
        self._build_menu()
        self._connect_signals()
        self.apply_shortcuts()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        central = QWidget()
        central.setStyleSheet("background-color: #0d0d0d;")
        self.setCentralWidget(central)

        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._drop_overlay = QLabel("Drop a video file here\n\nor  Ctrl+O  to browse")
        self._drop_overlay.setObjectName("drop_overlay")
        self._drop_overlay.setAlignment(Qt.AlignCenter)
        self._drop_overlay.setStyleSheet(
            "color: #555555; font-size: 18pt; font-family: 'Segoe UI';"
        )
        self._drop_overlay.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self._drop_overlay, stretch=1)

        self._mpv = MpvWidget(self)
        self._mpv.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._mpv.setVisible(False)
        layout.addWidget(self._mpv, stretch=1)

        self._controls = ControlsBar(self)
        layout.addWidget(self._controls, stretch=0)

        if not self._mpv.is_available():
            self._drop_overlay.setText(
                "python-mpv / libmpv not found.\n\n"
                "Place mpv-2.dll in the  dlls\\  folder and restart."
            )

    def _build_menu(self):
        menubar: QMenuBar = self.menuBar()

        # File menu
        file_menu: QMenu = menubar.addMenu("&File")

        open_act = QAction("&Open File...", self)
        open_act.triggered.connect(self._open_file_dialog)
        file_menu.addAction(open_act)

        open_folder_act = QAction("Open &Folder...", self)
        open_folder_act.triggered.connect(self._open_folder_dialog)
        file_menu.addAction(open_folder_act)

        file_menu.addSeparator()

        close_act = QAction("&Close", self)
        close_act.triggered.connect(self._close_file)
        file_menu.addAction(close_act)

        file_menu.addSeparator()

        exit_act = QAction("E&xit", self)
        exit_act.setShortcut(QKeySequence("Alt+F4"))
        exit_act.triggered.connect(self.close)
        file_menu.addAction(exit_act)

        # Settings menu
        settings_menu: QMenu = menubar.addMenu("&Settings")

        shortcuts_act = QAction("&Shortcuts...", self)
        shortcuts_act.triggered.connect(self._open_shortcuts_dialog)
        settings_menu.addAction(shortcuts_act)

    def _connect_signals(self):
        m = self._mpv
        c = self._controls

        m.time_changed.connect(c.update_position)
        m.duration_changed.connect(c.update_duration)
        m.pause_changed.connect(c.update_pause_state)
        m.eof_reached.connect(self._on_eof)
        m.zoom_changed.connect(c.update_zoom_label)

        c.play_pause_clicked.connect(m.toggle_pause)
        c.frame_back_clicked.connect(m.frame_back_step)
        c.frame_forward_clicked.connect(m.frame_step)
        c.prev_file_clicked.connect(self._prev_file)
        c.next_file_clicked.connect(self._next_file)
        c.seek_requested.connect(m.seek)
        c.speed_changed.connect(self._on_speed_changed)
        c.zoom_in_clicked.connect(m.zoom_in)
        c.zoom_out_clicked.connect(m.zoom_out)
        c.volume_changed.connect(m.set_volume)
        c.mute_toggled.connect(m.set_mute)

    # ------------------------------------------------------------------
    # Dynamic shortcuts
    # ------------------------------------------------------------------

    def apply_shortcuts(self):
        """Create or update all QShortcuts from current settings."""
        actions = {
            "toggle_pause":  self._mpv.toggle_pause,
            "frame_forward": self._mpv.frame_step,
            "frame_back":    self._mpv.frame_back_step,
            "speed_up":      self._speed_up,
            "speed_down":    self._speed_down,
            "zoom_in":       self._mpv.zoom_in,
            "zoom_out":      self._mpv.zoom_out,
            "zoom_reset":    self._mpv.reset_zoom,
            "fullscreen":    self._toggle_fullscreen,
            "escape":        self._on_escape,
            "open_file":     self._open_file_dialog,
            "next_file":     self._next_file,
            "prev_file":     self._prev_file,
        }
        for action, slot in actions.items():
            key = self._settings.get_shortcut(action)
            if action in self._shortcuts:
                self._shortcuts[action].setKey(QKeySequence(key))
            else:
                sc = QShortcut(QKeySequence(key), self)
                sc.activated.connect(slot)
                self._shortcuts[action] = sc

    # ------------------------------------------------------------------
    # File / folder loading
    # ------------------------------------------------------------------

    def load_file(self, path: str):
        if not Path(path).exists():
            return
        # If this file belongs to the current playlist, just seek to it;
        # otherwise create a single-file playlist.
        if not self._playlist.try_set_current(path):
            self._playlist.set_single(path)
        self._mpv.load_file(path)
        self._drop_overlay.setVisible(False)
        self._mpv.setVisible(True)
        self._update_title()

    def _open_file_dialog(self):
        movies = QStandardPaths.writableLocation(QStandardPaths.MoviesLocation)
        ext_filter = (
            "Video Files (*.mp4 *.m4v *.mov *.mkv *.avi *.webm "
            "*.gif *.ts *.wmv *.flv *.mpg *.mpeg *.3gp *.ogv *.m2ts *.mts);;"
            "All Files (*)"
        )
        path, _ = QFileDialog.getOpenFileName(self, "Open Video", movies, ext_filter)
        if path:
            self.load_file(path)

    def _open_folder_dialog(self):
        movies = QStandardPaths.writableLocation(QStandardPaths.MoviesLocation)
        folder = QFileDialog.getExistingDirectory(self, "Open Folder", movies)
        if not folder:
            return
        self._playlist.load_folder(folder)
        if self._playlist.is_empty():
            return
        first = self._playlist.current()
        if first:
            self._mpv.load_file(first)
            self._drop_overlay.setVisible(False)
            self._mpv.setVisible(True)
            self._update_title()

    def _close_file(self):
        self._mpv.stop()
        self._mpv.setVisible(False)
        self._drop_overlay.setVisible(True)
        self.setWindowTitle("Simple Playback")

    # ------------------------------------------------------------------
    # Playlist navigation
    # ------------------------------------------------------------------

    def _next_file(self):
        path = self._playlist.next()
        if path:
            self._mpv.load_file(path)
            self._update_title()

    def _prev_file(self):
        path = self._playlist.prev()
        if path:
            self._mpv.load_file(path)
            self._update_title()

    def _on_eof(self):
        self._controls.update_eof()
        # Auto-advance to next file if the playlist has one
        if self._playlist.has_next():
            path = self._playlist.next()
            if path:
                self._mpv.load_file(path)
                self._update_title()

    def _update_title(self):
        path = self._playlist.current()
        if not path:
            self.setWindowTitle("Simple Playback")
            return
        name = Path(path).name
        count = self._playlist.count()
        idx = self._playlist.current_index() + 1
        if count > 1:
            self.setWindowTitle(f"Simple Playback - {name}  [{idx}/{count}]")
        else:
            self.setWindowTitle(f"Simple Playback - {name}")

    # ------------------------------------------------------------------
    # Settings dialog
    # ------------------------------------------------------------------

    def _open_shortcuts_dialog(self):
        dlg = ShortcutsDialog(self._settings, self)
        if dlg.exec():
            self.apply_shortcuts()

    # ------------------------------------------------------------------
    # Speed control
    # ------------------------------------------------------------------

    def _on_speed_changed(self, factor: float):
        self._current_speed = factor
        self._mpv.set_speed(factor)

    def _speed_up(self):
        new_speed = _clamp(self._current_speed * _SPEED_STEP_FACTOR, _SPEED_MIN, _SPEED_MAX)
        self._current_speed = new_speed
        self._mpv.set_speed(new_speed)
        self._controls.set_speed_display(new_speed)

    def _speed_down(self):
        new_speed = _clamp(self._current_speed / _SPEED_STEP_FACTOR, _SPEED_MIN, _SPEED_MAX)
        self._current_speed = new_speed
        self._mpv.set_speed(new_speed)
        self._controls.set_speed_display(new_speed)

    # ------------------------------------------------------------------
    # Fullscreen
    # ------------------------------------------------------------------

    def _toggle_fullscreen(self):
        if self._is_fullscreen:
            self.showNormal()
            self._is_fullscreen = False
            self._controls.setVisible(True)
            self._hide_controls_timer.stop()
            self.menuBar().setVisible(True)
        else:
            self.showFullScreen()
            self._is_fullscreen = True
            self.menuBar().setVisible(False)
            self._restart_hide_timer()

    def _on_escape(self):
        if self._is_fullscreen:
            self._toggle_fullscreen()

    def _restart_hide_timer(self):
        self._controls.setVisible(True)
        self._hide_controls_timer.start(_CONTROLS_HIDE_DELAY_MS)

    def _hide_controls(self):
        if self._is_fullscreen:
            self._controls.setVisible(False)

    def mouseMoveEvent(self, event):
        if self._is_fullscreen:
            self._restart_hide_timer()
        super().mouseMoveEvent(event)

    # ------------------------------------------------------------------
    # Drag-and-drop
    # ------------------------------------------------------------------

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if Path(url.toLocalFile()).suffix.lower() in VIDEO_EXTENSIONS:
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dropEvent(self, event: QDropEvent):
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if Path(path).suffix.lower() in VIDEO_EXTENSIONS:
                self.load_file(path)
                event.acceptProposedAction()
                return
        event.ignore()

    # ------------------------------------------------------------------
    # Window close
    # ------------------------------------------------------------------

    def closeEvent(self, event):
        self._mpv.closeEvent(event)
        super().closeEvent(event)
