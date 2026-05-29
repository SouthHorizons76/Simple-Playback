import os
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QWidget, QFormLayout, QFrame,
)


def _fmt_size(n_bytes: int) -> str:
    if n_bytes < 1024:
        return f"{n_bytes} B"
    n = n_bytes / 1024
    if n < 1024:
        return f"{n:.1f} KB"
    n /= 1024
    if n < 1024:
        return f"{n:.2f} MB"
    return f"{n / 1024:.2f} GB"


def _fmt_duration(s: float) -> str:
    h = int(s // 3600)
    m = int((s % 3600) // 60)
    sec = int(s % 60)
    ms = int(round((s % 1) * 1000))
    if h:
        return f"{h}:{m:02d}:{sec:02d}.{ms:03d}"
    return f"{m:02d}:{sec:02d}.{ms:03d}"


class MetadataDialog(QDialog):
    def __init__(self, file_path: str, media_info: dict, parent=None):
        super().__init__(parent)
        self._path = file_path
        self._info = media_info
        self.setWindowTitle("File Metadata")
        self.setMinimumWidth(440)
        self.resize(460, 360)
        self.setModal(True)
        self._build_ui()

    def _collect_rows(self) -> list:
        rows = []
        p = Path(self._path)

        # Get file size once - reused for display and VBR detection
        _file_bytes: int | None = None
        try:
            _file_bytes = os.path.getsize(self._path)
        except OSError:
            pass

        # Average bitrate derived from file size and duration (reliable for VBR detection)
        _avg_kbps: float | None = None
        dur = float(self._info.get("duration") or 0)
        if _file_bytes and dur > 0:
            _avg_kbps = _file_bytes * 8 / dur / 1000

        rows.append(("File", p.name))
        if _file_bytes is not None:
            rows.append(("Size", _fmt_size(_file_bytes)))
        elif "file_size" in self._info:
            rows.append(("Size", _fmt_size(int(self._info["file_size"]))))
        rows.append(("Container", p.suffix.lstrip(".").upper() or "Unknown"))

        if "duration" in self._info:
            rows.append(("Duration", _fmt_duration(float(self._info["duration"]))))

        w = self._info.get("width")
        h = self._info.get("height")
        if w and h:
            rows.append(("Resolution", f"{int(w)} × {int(h)}"))

        if "fps" in self._info:
            rows.append(("Frame Rate", f"{float(self._info['fps']):.3f} fps"))

        if "video_codec" in self._info:
            rows.append(("Video Codec", str(self._info["video_codec"])))

        if "video_bitrate" in self._info:
            vid_kbps = int(self._info["video_bitrate"]) // 1000
            aud_kbps = int(self._info.get("audio_bitrate") or 0) // 1000
            declared_kbps = vid_kbps + aud_kbps

            vbr_note = ""
            if _avg_kbps is not None and declared_kbps > 0:
                diff_ratio = abs(_avg_kbps - declared_kbps) / max(_avg_kbps, declared_kbps)
                if diff_ratio > 0.15:
                    vbr_note = " (VBR)"

            rows.append(("Video Bitrate", f"{vid_kbps:,} kbps{vbr_note}"))

        if "audio_codec" in self._info:
            rows.append(("Audio Codec", str(self._info["audio_codec"])))

        if "audio_bitrate" in self._info:
            rows.append(("Audio Bitrate", f"{int(self._info['audio_bitrate']) // 1000:,} kbps"))

        tags = self._info.get("tags")
        if tags and isinstance(tags, dict):
            visible = [
                (k, str(v).strip()) for k, v in tags.items()
                if k and str(v).strip()
            ]
            if visible:
                rows.append(None)  # separator
                for k, v in visible:
                    rows.append((k.title(), v))

        return rows

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 12)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        body = QWidget()
        form = QFormLayout(body)
        form.setContentsMargins(24, 16, 24, 12)
        form.setHorizontalSpacing(16)
        form.setVerticalSpacing(7)
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)

        for row in self._collect_rows():
            if row is None:
                sep = QFrame()
                sep.setFrameShape(QFrame.HLine)
                sep.setFrameShadow(QFrame.Plain)
                sep.setStyleSheet("color: #333333;")
                form.addRow(sep)
                continue

            key, val = row
            k_lbl = QLabel(key + ":")
            k_lbl.setStyleSheet("color: #777777; font-size: 9pt;")

            v_lbl = QLabel(val)
            v_lbl.setStyleSheet("color: #e8e8e8; font-size: 9pt;")
            v_lbl.setWordWrap(True)
            v_lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)

            form.addRow(k_lbl, v_lbl)

        scroll.setWidget(body)
        outer.addWidget(scroll)

        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(0, 0, 16, 0)
        btn_row.addStretch()
        ok = QPushButton("OK")
        ok.setDefault(True)
        ok.setFixedWidth(80)
        ok.setStyleSheet(
            "QPushButton { background: #2a6ecf; color: #fff; padding: 5px 0;"
            " border-radius: 4px; }"
            "QPushButton:hover { background: #3a7edf; }"
        )
        ok.clicked.connect(self.accept)
        btn_row.addWidget(ok)
        outer.addLayout(btn_row)
