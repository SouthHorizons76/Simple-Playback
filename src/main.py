import sys
import os
import shutil

# On Windows, register the dlls\ subfolder as a DLL search path so that
# mpv-2.dll and its FFmpeg companions are found without modifying PATH.
# This must happen before importing mpv.
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Ensure the project root is on sys.path so `from src.X import` works when
# this script is invoked directly as  python src\main.py
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

_dlls_dir = os.path.join(_project_root, "dlls")
if os.path.isdir(_dlls_dir):
    # python-mpv looks for 'mpv-2.dll' on Windows. Some libmpv builds ship
    # the file as 'libmpv-2.dll' instead. Create a copy under the expected
    # name so both naming conventions work without manual renaming.
    _libmpv = os.path.join(_dlls_dir, "libmpv-2.dll")
    _mpv    = os.path.join(_dlls_dir, "mpv-2.dll")
    if os.path.isfile(_libmpv) and not os.path.isfile(_mpv):
        shutil.copy2(_libmpv, _mpv)

    # python-mpv's ctypes loader searches PATH (not os.add_dll_directory)
    os.environ["PATH"] = _dlls_dir + os.pathsep + os.environ.get("PATH", "")
    os.add_dll_directory(_dlls_dir)

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from src.theme import apply_app_palette
from src.player_window import PlayerWindow


def main():
    # High-DPI scaling is enabled by default in Qt6; no explicit attribute needed.
    app = QApplication(sys.argv)
    app.setApplicationName("Simple Playback")
    app.setApplicationDisplayName("Simple Playback")
    app.setOrganizationName("")

    apply_app_palette(app)

    window = PlayerWindow()
    window.resize(1280, 720)
    window.show()

    # Support opening a file passed as a command-line argument
    # (also enables drag-onto-exe-icon behaviour on Windows)
    if len(sys.argv) > 1:
        path = sys.argv[1]
        if os.path.isfile(path):
            window.load_file(path)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
