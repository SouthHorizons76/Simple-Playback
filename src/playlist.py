import re
from pathlib import Path

VIDEO_EXTENSIONS = {
    ".mp4", ".m4v", ".mov", ".mkv", ".avi", ".webm",
    ".gif", ".ts", ".wmv", ".flv", ".mpg", ".mpeg",
    ".3gp", ".ogv", ".hevc", ".m2ts", ".mts",
}


def _natural_key(path: str) -> list:
    """Sort key for natural ordering: 'clip2' before 'clip10'."""
    parts = re.split(r"(\d+)", Path(path).name.lower())
    return [int(p) if p.isdigit() else p for p in parts]


class Playlist:
    def __init__(self):
        self._files: list[str] = []
        self._index: int = -1

    def load_folder(self, folder: str):
        p = Path(folder)
        files = [
            str(f) for f in p.iterdir()
            if f.is_file() and f.suffix.lower() in VIDEO_EXTENSIONS
        ]
        files.sort(key=_natural_key)
        self._files = files
        self._index = 0 if files else -1

    def set_single(self, path: str):
        """Set a single file with no folder context."""
        self._files = [path]
        self._index = 0

    def try_set_current(self, path: str) -> bool:
        """Locate path in current list and make it active. Returns True if found."""
        norm = str(Path(path).resolve())
        for i, f in enumerate(self._files):
            if str(Path(f).resolve()) == norm:
                self._index = i
                return True
        return False

    def current(self) -> str | None:
        if 0 <= self._index < len(self._files):
            return self._files[self._index]
        return None

    def next(self) -> str | None:
        if self._index + 1 < len(self._files):
            self._index += 1
            return self.current()
        return None

    def prev(self) -> str | None:
        if self._index > 0:
            self._index -= 1
            return self.current()
        return None

    def has_next(self) -> bool:
        return self._index + 1 < len(self._files)

    def has_prev(self) -> bool:
        return self._index > 0

    def count(self) -> int:
        return len(self._files)

    def current_index(self) -> int:
        return self._index

    def is_empty(self) -> bool:
        return not self._files
