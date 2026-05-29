from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QKeySequenceEdit, QHeaderView,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeySequence

from .settings import Settings

_STYLE_EDIT_IDLE = """
    QKeySequenceEdit {
        background: #252525;
        color: #e8e8e8;
        border: 1px solid #444;
        border-radius: 3px;
        padding: 3px 6px;
        font-size: 10pt;
    }
"""

_STYLE_EDIT_LISTENING = """
    QKeySequenceEdit {
        background: #0d1e33;
        color: #4a9eff;
        border: 2px solid #4a9eff;
        border-radius: 3px;
        padding: 2px 6px;
        font-size: 10pt;
        font-weight: bold;
    }
"""

_TABLE_STYLE = """
QTableWidget {
    background: #1a1a1a;
    border: 1px solid #333;
    gridline-color: #222;
}
QHeaderView::section {
    background: #252525;
    color: #888;
    padding: 6px 8px;
    border: none;
    border-bottom: 1px solid #333;
    font-size: 9pt;
}
QTableWidget::item {
    padding: 4px 8px;
    color: #e8e8e8;
    border-bottom: 1px solid #222;
}
"""


class HotkeyEdit(QKeySequenceEdit):
    """
    QKeySequenceEdit with:
    - Visual "listening" state when focused (blue border + tint)
    - Escape always clears the field (never assigns Escape as a shortcut)
    - Signals for the dialog to show a status banner
    """
    focus_gained = Signal(str)   # emits the human-readable action label
    focus_lost   = Signal()

    def __init__(self, action_label: str, sequence: QKeySequence, parent=None):
        super().__init__(sequence, parent)
        self._action_label = action_label
        self.setStyleSheet(_STYLE_EDIT_IDLE)

    def focusInEvent(self, event):
        self.setStyleSheet(_STYLE_EDIT_LISTENING)
        self.focus_gained.emit(self._action_label)
        super().focusInEvent(event)

    def focusOutEvent(self, event):
        self.setStyleSheet(_STYLE_EDIT_IDLE)
        self.focus_lost.emit()
        super().focusOutEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.clear()
            self.clearFocus()
            event.accept()
            return
        super().keyPressEvent(event)


class ShortcutsDialog(QDialog):
    def __init__(self, settings: Settings, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Shortcuts")
        self.setMinimumWidth(500)
        self.setMinimumHeight(520)
        self.setModal(True)
        self._settings = settings
        self._edits: dict[str, HotkeyEdit] = {}
        self._build_ui()
        self._populate()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        # Status banner — updates live when a field is focused
        self._status = QLabel("Click a shortcut field to change it.  Esc clears a field.")
        self._status.setWordWrap(True)
        self._status.setFixedHeight(36)
        self._status.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        self._status.setContentsMargins(10, 0, 10, 0)
        self._set_status_idle()
        layout.addWidget(self._status)

        # Shortcut table
        self._table = QTableWidget(0, 2)
        self._table.setHorizontalHeaderLabels(["Action", "Shortcut"])
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Fixed)
        self._table.horizontalHeader().resizeSection(1, 180)
        self._table.verticalHeader().setVisible(False)
        self._table.setShowGrid(False)
        self._table.setAlternatingRowColors(False)
        self._table.setSelectionMode(QTableWidget.NoSelection)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.setStyleSheet(_TABLE_STYLE)
        layout.addWidget(self._table)

        # Button row
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        btn_reset = QPushButton("Reset to Defaults")
        btn_reset.setStyleSheet(
            "QPushButton { background: #252525; color: #aaa; padding: 6px 14px; border-radius: 4px; }"
            "QPushButton:hover { background: #2e2e2e; color: #e8e8e8; }"
        )
        btn_reset.clicked.connect(self._on_reset)
        btn_row.addWidget(btn_reset)
        btn_row.addStretch()

        btn_cancel = QPushButton("Cancel")
        btn_cancel.setStyleSheet(
            "QPushButton { background: #252525; color: #aaa; padding: 6px 14px; border-radius: 4px; }"
            "QPushButton:hover { background: #2e2e2e; color: #e8e8e8; }"
        )
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_cancel)

        btn_apply = QPushButton("Apply")
        btn_apply.setDefault(True)
        btn_apply.setStyleSheet(
            "QPushButton { background: #2a6ecf; color: #fff; padding: 6px 18px; border-radius: 4px; }"
            "QPushButton:hover { background: #3a7edf; }"
        )
        btn_apply.clicked.connect(self._on_apply)
        btn_row.addWidget(btn_apply)

        layout.addLayout(btn_row)

    def _set_status_idle(self):
        self._status.setText("Click a shortcut field to change it.  Esc clears a field.")
        self._status.setStyleSheet(
            "background: #1a1a1a; color: #555; border: 1px solid #2a2a2a; border-radius: 4px;"
            "font-size: 9pt;"
        )

    def _set_status_listening(self, action_label: str):
        self._status.setText(f"  ●  Listening for: {action_label}, Esc to clear shortcut")
        self._status.setStyleSheet(
            "background: #0d1e33; color: #4a9eff; border: 1px solid #4a9eff; border-radius: 4px;"
            "font-size: 9pt; font-weight: bold;"
        )

    def _populate(self):
        labels = Settings.shortcut_labels()
        current = self._settings.all_shortcuts()
        self._table.setRowCount(len(labels))
        for row, (action, label) in enumerate(labels.items()):
            item = QTableWidgetItem(label)
            item.setFlags(Qt.ItemIsEnabled)
            self._table.setItem(row, 0, item)
            self._table.setRowHeight(row, 40)

            edit = HotkeyEdit(label, QKeySequence(current.get(action, "")))
            edit.focus_gained.connect(self._set_status_listening)
            edit.focus_lost.connect(self._set_status_idle)
            self._table.setCellWidget(row, 1, edit)
            self._edits[action] = edit

    def _on_apply(self):
        for action, edit in self._edits.items():
            ks = edit.keySequence().toString()
            self._settings.set_shortcut(action, ks)
        self._settings.save()
        self.accept()

    def _on_reset(self):
        defaults = Settings.default_shortcuts()
        for action, edit in self._edits.items():
            edit.setKeySequence(QKeySequence(defaults.get(action, "")))
