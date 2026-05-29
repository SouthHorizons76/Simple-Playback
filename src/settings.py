import json
import os
from pathlib import Path

_DEFAULT_SHORTCUTS: dict[str, str] = {
    "toggle_pause":  "Space",
    "frame_forward": "Right",
    "frame_back":    "Left",
    "speed_up":      "]",
    "speed_down":    "[",
    "zoom_in":       "=",
    "zoom_out":      "-",
    "zoom_reset":    "0",
    "fullscreen":    "F",
    "escape":        "Escape",
    "open_file":     "Ctrl+O",
    "next_file":     "N",
    "prev_file":     "P",
}

_SHORTCUT_LABELS: dict[str, str] = {
    "toggle_pause":  "Play / Pause",
    "frame_forward": "Frame Forward",
    "frame_back":    "Frame Backward",
    "speed_up":      "Speed Up",
    "speed_down":    "Speed Down",
    "zoom_in":       "Zoom In",
    "zoom_out":      "Zoom Out",
    "zoom_reset":    "Reset Zoom",
    "fullscreen":    "Fullscreen Toggle",
    "escape":        "Exit Fullscreen",
    "open_file":     "Open File",
    "next_file":     "Next File in Folder",
    "prev_file":     "Previous File in Folder",
}


def _settings_path() -> Path:
    app_data = os.environ.get("APPDATA", str(Path.home()))
    folder = Path(app_data) / "SimplePlayback"
    folder.mkdir(parents=True, exist_ok=True)
    return folder / "settings.json"


class Settings:
    def __init__(self):
        self._data: dict = {}
        self._load()

    def _load(self):
        path = _settings_path()
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    self._data = json.load(f)
            except Exception:
                self._data = {}

    def save(self):
        path = _settings_path()
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2)
        except Exception:
            pass

    def get_shortcut(self, action: str) -> str:
        return self._data.get("shortcuts", {}).get(
            action, _DEFAULT_SHORTCUTS.get(action, "")
        )

    def set_shortcut(self, action: str, key_sequence: str):
        if "shortcuts" not in self._data:
            self._data["shortcuts"] = {}
        self._data["shortcuts"][action] = key_sequence

    def reset_shortcuts(self):
        self._data["shortcuts"] = dict(_DEFAULT_SHORTCUTS)

    def all_shortcuts(self) -> dict[str, str]:
        result = dict(_DEFAULT_SHORTCUTS)
        result.update(self._data.get("shortcuts", {}))
        return result

    @staticmethod
    def shortcut_labels() -> dict[str, str]:
        return dict(_SHORTCUT_LABELS)

    @staticmethod
    def default_shortcuts() -> dict[str, str]:
        return dict(_DEFAULT_SHORTCUTS)

    def get(self, key: str, default=None):
        return self._data.get(key, default)

    def set(self, key: str, value) -> None:
        self._data[key] = value
