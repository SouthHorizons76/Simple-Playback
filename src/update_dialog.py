import os
import tempfile
import webbrowser

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QProgressBar, QTextEdit,
)
from PySide6.QtCore import Qt, QThread
from PySide6.QtGui import QTextOption

from .updater import (
    CheckThread, DownloadThread, ExtractThread,
    find_extractor, write_updater_script, launch_updater_script,
    is_newer, is_packaged, is_dir_writable, app_dir, app_exe,
    GITHUB_REPO,
)
from .version import VERSION

_RELEASES_URL = f"https://github.com/{GITHUB_REPO}/releases/latest"

_BTN_PRIMARY = (
    "QPushButton { background: #2a6ecf; color: #fff; padding: 5px 16px;"
    " border-radius: 4px; border: none; }"
    "QPushButton:hover { background: #3a7edf; }"
    "QPushButton:disabled { background: #2a2a2a; color: #555; border: none; }"
)
_BTN_SECONDARY = (
    "QPushButton { background: #2e2e2e; color: #ccc; padding: 5px 16px;"
    " border-radius: 4px; border: 1px solid #3c3c3c; }"
    "QPushButton:hover { background: #3a3a3a; }"
)


class UpdateDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Check for Updates")
        self.setMinimumWidth(430)
        self.setModal(True)

        self._temp_dir      = None
        self._release_info  = None
        self._extracted_dir = None
        self._extractor     = find_extractor()
        self._threads: list = []

        self._build_ui()
        self._start_check()

    # ── UI ─────────────────────────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 16)
        root.setSpacing(10)

        self._status_lbl = QLabel("Checking for updates…")
        self._status_lbl.setStyleSheet("font-size: 10pt; color: #e0e0e0;")
        self._status_lbl.setWordWrap(True)
        root.addWidget(self._status_lbl)

        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setFixedHeight(6)
        self._progress.setTextVisible(False)
        self._progress.setStyleSheet(
            "QProgressBar { background: #252525; border-radius: 3px; border: none; }"
            "QProgressBar::chunk { background: #2a6ecf; border-radius: 3px; }"
        )
        self._progress.setVisible(False)
        root.addWidget(self._progress)

        self._notes = QTextEdit()
        self._notes.setReadOnly(True)
        self._notes.setFixedHeight(130)
        self._notes.setWordWrapMode(QTextOption.WrapMode.WordWrap)
        self._notes.setStyleSheet(
            "QTextEdit { background: #181818; color: #aaaaaa; border: 1px solid #303030;"
            " border-radius: 4px; font-size: 9pt; padding: 4px; }"
            "QScrollBar:vertical { background: #1e1e1e; width: 8px; }"
            "QScrollBar::handle:vertical { background: #404040; border-radius: 4px; }"
        )
        self._notes.setVisible(False)
        root.addWidget(self._notes)

        root.addSpacing(4)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        btn_row.addStretch()

        self._close_btn = QPushButton("Close")
        self._close_btn.setFixedWidth(80)
        self._close_btn.setStyleSheet(_BTN_SECONDARY)
        self._close_btn.clicked.connect(self.reject)
        btn_row.addWidget(self._close_btn)

        self._action_btn = QPushButton()
        self._action_btn.setMinimumWidth(140)
        self._action_btn.setStyleSheet(_BTN_PRIMARY)
        self._action_btn.setVisible(False)
        btn_row.addWidget(self._action_btn)

        root.addLayout(btn_row)
        self.adjustSize()

    # ── check phase ────────────────────────────────────────────────────────

    def _start_check(self):
        t = CheckThread()
        t.done.connect(self._on_check_done)
        t.error.connect(self._on_check_error)
        t.finished.connect(lambda: self._drop_thread(t))
        self._threads.append(t)
        t.start()

    def _on_check_done(self, info: dict):
        self._release_info = info
        tag = info["tag"]

        if not is_newer(tag):
            self._status_lbl.setText(f"You're running the latest version ({VERSION}).")
            self.adjustSize()
            return

        # Update is available — decide which action button to show
        can_auto = is_packaged() and bool(info.get("rar_url")) and self._extractor is not None

        self._status_lbl.setText(f"Version {tag} is available.")

        if info.get("body"):
            self._notes.setPlainText(info["body"].strip())
            self._notes.setVisible(True)

        if can_auto:
            self._set_action("Download & Install", self._start_download)
        else:
            if not is_packaged():
                note = "Auto-update is only available in the packaged app."
            elif not info.get("rar_url"):
                note = "No downloadable release asset was found."
            else:
                note = "WinRAR or 7-Zip is required for auto-update."
            self._status_lbl.setText(f"Version {tag} is available.\n{note}")
            self._set_action("Open Download Page", self._open_page)

        self.adjustSize()

    def _on_check_error(self, msg: str):
        self._status_lbl.setText(f"Failed to check for updates:\n{msg}")
        self.adjustSize()

    # ── download phase ─────────────────────────────────────────────────────

    def _start_download(self):
        self._temp_dir = tempfile.mkdtemp(prefix="sp_update_")
        url = self._release_info["rar_url"]
        tag = self._release_info["tag"]

        self._status_lbl.setText(f"Downloading {tag}…")
        self._notes.setVisible(False)
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setVisible(True)
        self._action_btn.setEnabled(False)
        self.adjustSize()

        t = DownloadThread(url, self._temp_dir)
        t.progress.connect(self._on_download_progress)
        t.done.connect(self._on_download_done)
        t.error.connect(self._on_download_error)
        t.finished.connect(lambda: self._drop_thread(t))
        self._threads.append(t)
        t.start()

    def _on_download_progress(self, done: int, total: int):
        if total > 0:
            self._progress.setRange(0, 100)
            self._progress.setValue(int(done * 100 / total))
            self._status_lbl.setText(
                f"Downloading… ({done / 1048576:.1f} MB / {total / 1048576:.1f} MB)"
            )
        else:
            self._progress.setRange(0, 0)  # indeterminate
            self._status_lbl.setText(f"Downloading… ({done / 1048576:.1f} MB)")

    def _on_download_done(self, rar_path: str):
        self._progress.setRange(0, 100)
        self._progress.setValue(100)
        self._status_lbl.setText("Extracting update…")

        t = ExtractThread(rar_path, self._temp_dir, self._extractor)
        t.done.connect(self._on_extract_done)
        t.error.connect(self._on_extract_error)
        t.finished.connect(lambda: self._drop_thread(t))
        self._threads.append(t)
        t.start()

    def _on_download_error(self, msg: str):
        self._progress.setVisible(False)
        self._status_lbl.setText(f"Download failed:\n{msg}")
        self._set_action("Open Download Page", self._open_page)
        self._action_btn.setEnabled(True)
        self.adjustSize()

    # ── extract phase ──────────────────────────────────────────────────────

    def _on_extract_done(self, source_dir: str):
        self._extracted_dir = source_dir
        self._progress.setVisible(False)
        self._status_lbl.setText(
            "Update ready.\n\n"
            "The app will close and restart automatically to apply the update."
        )
        self._set_action("Install Now", self._install)
        self._action_btn.setEnabled(True)
        self.adjustSize()

    def _on_extract_error(self, msg: str):
        self._progress.setVisible(False)
        self._status_lbl.setText(f"Extraction failed:\n{msg}")
        self._set_action("Open Download Page", self._open_page)
        self._action_btn.setEnabled(True)
        self.adjustSize()

    # ── install ─────────────────────────────────────────────────────────────

    def _install(self):
        dest = app_dir()
        if not is_dir_writable(dest):
            self._status_lbl.setText(
                "Cannot write to the installation folder.\n\n"
                "Please close this app and re-run it as Administrator, then try again."
            )
            self._action_btn.setVisible(False)
            self.adjustSize()
            return

        script = write_updater_script(
            self._extracted_dir,
            dest,
            app_exe(),
            os.getpid(),
            self._temp_dir,
        )
        launch_updater_script(script)
        from PySide6.QtWidgets import QApplication
        QApplication.quit()

    # ── helpers ─────────────────────────────────────────────────────────────

    def _open_page(self):
        url = self._release_info.get("html_url", _RELEASES_URL) if self._release_info else _RELEASES_URL
        webbrowser.open(url)
        self.accept()

    def _set_action(self, label: str, slot):
        try:
            self._action_btn.clicked.disconnect()
        except RuntimeError:
            pass
        self._action_btn.setText(label)
        self._action_btn.clicked.connect(slot)
        self._action_btn.setVisible(True)

    def _drop_thread(self, t: QThread):
        if t in self._threads:
            self._threads.remove(t)

    def closeEvent(self, event):
        for t in list(self._threads):
            if hasattr(t, "abort"):
                t.abort()
            t.wait(2000)
        super().closeEvent(event)
