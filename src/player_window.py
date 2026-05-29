import os
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QStandardPaths, QPoint, Signal
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QLabel, QFrame, QPushButton,
    QFileDialog, QMenuBar, QMenu, QSizePolicy,
)
from PySide6.QtGui import QAction, QKeySequence, QShortcut, QDragEnterEvent, QDropEvent

from .mpv_widget import MpvWidget
from .controls import ControlsBar
from .settings import Settings
from .shortcuts_dialog import ShortcutsDialog
from .about_dialog import AboutDialog
from .metadata_dialog import MetadataDialog
from .playlist import Playlist, VIDEO_EXTENSIONS
from .theme import MENU_STYLESHEET

_SPEED_MIN_KB  = 0.1
_SPEED_MAX     = 4.0
_SPEED_STEP_KB = 0.1
_CONTROLS_HIDE_DELAY_MS = 2000


# ---------------------------------------------------------------------------
# Floating hint overlay (appears over the video in the top-right corner)
# ---------------------------------------------------------------------------

class _HintOverlay(QLabel):
    """Frameless top-level label that shows transient action feedback."""

    def __init__(self, parent_window):
        super().__init__()
        self._pw = parent_window
        self.setWindowFlags(
            Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAlignment(Qt.AlignCenter)
        self.setObjectName("hint_overlay")
        self.setStyleSheet(
            "#hint_overlay {"
            "  background: rgba(0, 0, 0, 178);"
            "  color: #ffffff;"
            "  font-size: 12pt;"
            "  font-family: \"Segoe UI\";"
            "  padding: 7px 18px;"
            "  border-radius: 6px;"
            "}"
        )
        self._timer = QTimer()
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.hide)

    def show_hint(self, text: str, duration_ms: int = 1700):
        self._timer.stop()
        self.setText(text)
        self.adjustSize()
        self._place()
        self.show()
        self._timer.start(duration_ms)

    def _place(self):
        pw = self._pw
        cw = pw.centralWidget()
        if not cw:
            return
        margin = 14
        top_left = cw.mapToGlobal(QPoint(0, 0))
        x = top_left.x() + cw.width() - self.width() - margin
        y = top_left.y() + margin
        self.move(x, y)


# ---------------------------------------------------------------------------
# Audio track panel (floating popup above the audio button)
# ---------------------------------------------------------------------------

class _AudioTrackPanel(QFrame):
    """Floating panel listing per-track toggle buttons."""

    tracks_changed = Signal(list)   # list[int] of selected track IDs

    _BTN_STYLE = (
        "QPushButton {"
        "  background: #2a2a2a;"
        "  color: #cccccc;"
        "  border: 1px solid #3c3c3c;"
        "  border-radius: 4px;"
        "  padding: 5px 14px;"
        "  text-align: left;"
        "  font-size: 9pt;"
        "  font-family: \"Segoe UI\";"
        "}"
        "QPushButton:checked {"
        "  background: #1a6fb5;"
        "  color: #ffffff;"
        "  border-color: #1a6fb5;"
        "}"
        "QPushButton:hover:!checked { background: #333333; }"
        "QPushButton:hover:checked  { background: #1f80d0; }"
    )

    def __init__(self, parent_window):
        super().__init__()
        self._pw = parent_window
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setObjectName("audio_track_panel")
        self.setStyleSheet(
            "#audio_track_panel {"
            "  background: #1c1c1c;"
            "  border: 1px solid #3c3c3c;"
            "  border-radius: 6px;"
            "}"
            "#audio_track_panel QLabel {"
            "  background: transparent;"
            "  border: none;"
            "}"
        )
        self._track_btns: list[tuple[int, QPushButton]] = []
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 10)
        layout.setSpacing(5)

        title = QLabel("Audio Tracks")
        title.setStyleSheet("color: #888888; font-size: 8pt;")
        layout.addWidget(title)

        self._inner = QVBoxLayout()
        self._inner.setContentsMargins(0, 0, 0, 0)
        self._inner.setSpacing(3)
        layout.addLayout(self._inner)

        self._no_tracks = QLabel("No audio tracks")
        self._no_tracks.setStyleSheet("color: #555555; font-size: 9pt; padding: 4px 0;")
        self._inner.addWidget(self._no_tracks)

    def set_tracks(self, tracks: list):
        for _, btn in self._track_btns:
            btn.setParent(None)
        self._track_btns.clear()

        has = len(tracks) > 0
        self._no_tracks.setVisible(not has)

        for track in tracks:
            tid = track.get("id", 0)
            title_str = track.get("title") or ""
            lang = track.get("lang") or ""
            parts = [f"Track {tid}"]
            if lang:
                parts.append(f"[{lang}]")
            if title_str:
                parts.append(title_str)
            label = "  ".join(parts)

            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setChecked(False)
            btn.setStyleSheet(self._BTN_STYLE)
            btn.toggled.connect(self._on_toggle)
            self._track_btns.append((tid, btn))
            self._inner.addWidget(btn)

        # Default: first track selected (mirrors MPV default)
        if self._track_btns:
            self._track_btns[0][1].setChecked(True)

        self.adjustSize()

    def _on_toggle(self):
        selected = [tid for tid, btn in self._track_btns if btn.isChecked()]
        self.tracks_changed.emit(selected)

    def position_above(self, ref_widget: QWidget):
        self.adjustSize()
        ref_global = ref_widget.mapToGlobal(QPoint(0, 0))
        x = ref_global.x() + ref_widget.width() // 2 - self.width() // 2
        y = ref_global.y() - self.height() - 6
        self.move(x, y)


# ---------------------------------------------------------------------------
# Main window
# ---------------------------------------------------------------------------

class PlayerWindow(QMainWindow):

    def __init__(self, settings: Settings | None = None):
        super().__init__()
        self._settings = settings or Settings()
        self._playlist = Playlist()
        self._current_speed: float = 1.0
        self._is_fullscreen: bool = False
        self._shortcuts: dict[str, QShortcut] = {}
        self._active_audio_tracks: list[int] = []

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

        # Overlay windows (top-level, no Qt parent - managed manually)
        self._hint_overlay = _HintOverlay(self)
        self._audio_panel  = _AudioTrackPanel(self)
        self._audio_panel.tracks_changed.connect(self._on_audio_tracks_selected)

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
            "color: #555555; font-size: 18pt; font-family: \"Segoe UI\";"
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
        file_menu.setStyleSheet(MENU_STYLESHEET)

        open_act = QAction("&Open File...", self)
        open_act.triggered.connect(self._open_file_dialog)
        file_menu.addAction(open_act)

        open_folder_act = QAction("Open &Folder...", self)
        open_folder_act.triggered.connect(self._open_folder_dialog)
        file_menu.addAction(open_folder_act)

        file_menu.addSeparator()

        export_act = QAction("Export &Frame as PNG...", self)
        export_act.triggered.connect(self._export_frame)
        file_menu.addAction(export_act)

        self._metadata_act = QAction("File &Metadata...", self)
        self._metadata_act.triggered.connect(self._open_metadata_dialog)
        self._metadata_act.setVisible(False)
        file_menu.addAction(self._metadata_act)

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
        settings_menu.setStyleSheet(MENU_STYLESHEET)

        shortcuts_act = QAction("&Shortcuts...", self)
        shortcuts_act.triggered.connect(self._open_shortcuts_dialog)
        settings_menu.addAction(shortcuts_act)

        # Help menu
        help_menu: QMenu = menubar.addMenu("&Help")
        help_menu.setStyleSheet(MENU_STYLESHEET)

        about_act = QAction("&About...", self)
        about_act.triggered.connect(self._open_about_dialog)
        help_menu.addAction(about_act)

        from .registration import is_registered, _exe_path
        if _exe_path():
            help_menu.addSeparator()
            self._unregister_act = QAction("Remove from \"Open with\" Menu", self)
            self._unregister_act.triggered.connect(self._on_unregister)
            self._unregister_act.setVisible(is_registered())
            help_menu.addAction(self._unregister_act)
        else:
            self._unregister_act = None

    def _connect_signals(self):
        m = self._mpv
        c = self._controls

        m.time_changed.connect(c.update_position)
        m.duration_changed.connect(c.update_duration)
        m.pause_changed.connect(c.update_pause_state)
        m.eof_reached.connect(self._on_eof)
        m.zoom_changed.connect(c.update_zoom_label)
        m.zoom_changed.connect(self._on_zoom_hint)
        m.audio_tracks_changed.connect(self._on_audio_tracks_changed)

        c.play_pause_clicked.connect(self._toggle_pause_hint)
        c.frame_back_clicked.connect(self._on_frame_back)
        c.frame_forward_clicked.connect(self._on_frame_forward)
        c.prev_file_clicked.connect(self._prev_file)
        c.next_file_clicked.connect(self._next_file)
        c.seek_requested.connect(m.seek)
        c.speed_changed.connect(self._on_speed_changed)
        c.zoom_in_clicked.connect(m.zoom_in)
        c.zoom_out_clicked.connect(m.zoom_out)
        c.volume_changed.connect(m.set_volume)
        c.mute_toggled.connect(m.set_mute)
        c.mute_toggled.connect(self._on_mute_hint)
        c.audio_btn_clicked.connect(self._toggle_audio_panel)

    # ------------------------------------------------------------------
    # Dynamic shortcuts
    # ------------------------------------------------------------------

    def apply_shortcuts(self):
        """Create or update all QShortcuts from current settings."""
        actions = {
            "toggle_pause":  self._toggle_pause_hint,
            "frame_forward": self._on_frame_forward,
            "frame_back":    self._on_frame_back,
            "speed_up":      self._speed_up,
            "speed_down":    self._speed_down,
            "zoom_in":       self._zoom_in_key,
            "zoom_out":      self._zoom_out_key,
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
        if not self._playlist.try_set_current(path):
            self._playlist.set_single(path)
        self._mpv.load_file(path)
        self._drop_overlay.setVisible(False)
        self._mpv.setVisible(True)
        self._metadata_act.setVisible(True)
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
            self._metadata_act.setVisible(True)
            self._update_title()

    def _close_file(self):
        self._mpv.stop()
        self._mpv.setVisible(False)
        self._drop_overlay.setVisible(True)
        self._metadata_act.setVisible(False)
        self.setWindowTitle("Simple Playback")

    # ------------------------------------------------------------------
    # Playlist navigation
    # ------------------------------------------------------------------

    def _next_file(self):
        path = self._playlist.next()
        if path:
            self._mpv.load_file(path)
            self._update_title()
            self._show_hint("Next File")

    def _prev_file(self):
        path = self._playlist.prev()
        if path:
            self._mpv.load_file(path)
            self._update_title()
            self._show_hint("Previous File")

    def _on_eof(self):
        self._controls.update_eof()
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

    def _open_about_dialog(self):
        AboutDialog(self).exec()

    def _open_metadata_dialog(self):
        current = self._playlist.current()
        if not current:
            return
        MetadataDialog(current, self._mpv.get_media_info(), self).exec()

    # ------------------------------------------------------------------
    # Open with registration
    # ------------------------------------------------------------------

    def maybe_prompt_registration(self):
        from .registration import is_registered, register, _exe_path
        from PySide6.QtWidgets import QMessageBox
        if not _exe_path() or is_registered():
            return
        if self._settings.get("registration_declined"):
            return
        result = QMessageBox.question(
            self,
            "Open with Simple Playback",
            "Add Simple Playback to the \"Open with\" menu for video files?\n\n"
            "You can remove it later via Help - Remove from \"Open with\" Menu.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if result == QMessageBox.StandardButton.Yes:
            register()
            if self._unregister_act:
                self._unregister_act.setVisible(True)
        else:
            self._settings.set("registration_declined", True)
            self._settings.save()

    def _on_unregister(self):
        from .registration import unregister
        from PySide6.QtWidgets import QMessageBox
        unregister()
        if self._unregister_act:
            self._unregister_act.setVisible(False)
        QMessageBox.information(
            self,
            "Open with",
            "Simple Playback has been removed from the \"Open with\" menu.",
        )

    # ------------------------------------------------------------------
    # Export frame
    # ------------------------------------------------------------------

    def _export_frame(self):
        if not self._mpv.is_available():
            return
        current = self._playlist.current()
        if current:
            default_dir = str(Path(current).parent)
            stem = Path(current).stem
        else:
            default_dir = QStandardPaths.writableLocation(QStandardPaths.PicturesLocation)
            stem = "frame"

        pos = self._mpv.get_position()
        h = int(pos // 3600)
        m = int((pos % 3600) // 60)
        s = int(pos % 60)
        default_name = f"{stem}_{h:02d}h{m:02d}m{s:02d}s.png"

        path, _ = QFileDialog.getSaveFileName(
            self, "Export Frame",
            str(Path(default_dir) / default_name),
            "PNG Image (*.png)"
        )
        if path:
            if not path.lower().endswith(".png"):
                path += ".png"
            self._mpv.export_frame(path)
            self._show_hint("Frame saved")

    # ------------------------------------------------------------------
    # Speed control
    # ------------------------------------------------------------------

    def _on_speed_changed(self, factor: float):
        """Called when the toolbar preset buttons are clicked."""
        self._current_speed = factor
        self._mpv.set_speed(factor)
        self._show_hint(f"Speed: {factor:.2g}×")

    def _speed_up(self):
        new_speed = round(min(self._current_speed + _SPEED_STEP_KB, _SPEED_MAX), 2)
        self._current_speed = new_speed
        self._mpv.set_speed(new_speed)
        self._controls.set_speed_display(new_speed)
        self._show_hint(f"Speed: {new_speed:.2g}×")

    def _speed_down(self):
        new_speed = round(max(self._current_speed - _SPEED_STEP_KB, _SPEED_MIN_KB), 2)
        self._current_speed = new_speed
        self._mpv.set_speed(new_speed)
        self._controls.set_speed_display(new_speed)
        self._show_hint(f"Speed: {new_speed:.2g}×")

    # ------------------------------------------------------------------
    # Zoom control (keyboard uses fine step, buttons use coarse step)
    # ------------------------------------------------------------------

    def _zoom_in_key(self):
        self._mpv.zoom_in_key()   # emits zoom_changed -> _on_zoom_hint

    def _zoom_out_key(self):
        self._mpv.zoom_out_key()

    # ------------------------------------------------------------------
    # Play / pause & frame step (wrapped to show hints)
    # ------------------------------------------------------------------

    def _toggle_pause_hint(self):
        self._mpv.toggle_pause()
        QTimer.singleShot(60, self._emit_pause_hint)

    def _emit_pause_hint(self):
        self._show_hint("Pause" if self._mpv.is_paused() else "Play")

    def _on_frame_forward(self):
        self._mpv.frame_step()
        self._show_hint("Frame +1")

    def _on_frame_back(self):
        self._mpv.frame_back_step()
        self._show_hint("Frame -1")

    # ------------------------------------------------------------------
    # Hint helpers
    # ------------------------------------------------------------------

    def _show_hint(self, text: str):
        self._hint_overlay.show_hint(text)

    def _on_zoom_hint(self, zoom_level: float):
        pct = int(round(2.0 ** zoom_level * 100))
        self._show_hint(f"Zoom: {pct}%")

    def _on_mute_hint(self, muted: bool):
        self._show_hint("Mute" if muted else "Unmute")

    # ------------------------------------------------------------------
    # Audio track panel
    # ------------------------------------------------------------------

    def _toggle_audio_panel(self):
        if self._audio_panel.isVisible():
            self._audio_panel.hide()
        else:
            self._audio_panel.position_above(self._controls._btn_audio)
            self._audio_panel.show()
            self._audio_panel.raise_()

    def _on_audio_tracks_changed(self, tracks: list):
        self._audio_panel.set_tracks(tracks)
        self._active_audio_tracks = [tracks[0]["id"]] if tracks else []

    def _on_audio_tracks_selected(self, track_ids: list):
        self._active_audio_tracks = track_ids
        self._mpv.set_audio_tracks(track_ids)
        if track_ids:
            names = ", ".join(f"Track {tid}" for tid in track_ids)
            self._show_hint(f"Audio: {names}")
        else:
            self._show_hint("Audio: Off")

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

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "_hint_overlay") and self._hint_overlay.isVisible():
            self._hint_overlay._place()

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
        self._hint_overlay.close()
        self._audio_panel.close()
        self._mpv.closeEvent(event)
        super().closeEvent(event)
