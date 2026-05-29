from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout
from PySide6.QtCore import Qt

from .version import APP_NAME, VERSION, BUILD_DATE, COPYRIGHT


class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"About {APP_NAME}")
        self.setFixedSize(340, 200)
        self.setModal(True)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 20)
        layout.setSpacing(6)

        name_lbl = QLabel(APP_NAME)
        name_lbl.setAlignment(Qt.AlignCenter)
        name_lbl.setStyleSheet("font-size: 15pt; font-weight: bold; color: #e8e8e8;")
        layout.addWidget(name_lbl)

        ver_lbl = QLabel(f"Version {VERSION}  -  Build {BUILD_DATE}")
        ver_lbl.setAlignment(Qt.AlignCenter)
        ver_lbl.setStyleSheet("font-size: 9pt; color: #888888;")
        layout.addWidget(ver_lbl)

        layout.addSpacing(14)

        copy_lbl = QLabel(COPYRIGHT)
        copy_lbl.setAlignment(Qt.AlignCenter)
        copy_lbl.setWordWrap(True)
        copy_lbl.setStyleSheet("font-size: 9pt; color: #666666;")
        layout.addWidget(copy_lbl)

        layout.addStretch()

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        ok_btn = QPushButton("OK")
        ok_btn.setDefault(True)
        ok_btn.setFixedWidth(80)
        ok_btn.setStyleSheet(
            "QPushButton { background: #2a6ecf; color: #fff; padding: 5px 0;"
            " border-radius: 4px; }"
            "QPushButton:hover { background: #3a7edf; }"
        )
        ok_btn.clicked.connect(self.accept)
        btn_row.addWidget(ok_btn)
        layout.addLayout(btn_row)
