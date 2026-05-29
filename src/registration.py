import os
import sys

_APP_KEY       = r"Software\Classes\Applications\SimplePlayback.exe"
_APP_PATHS_KEY = r"Software\Microsoft\Windows\CurrentVersion\App Paths\SimplePlayback.exe"

VIDEO_EXTENSIONS = [
    '.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm',
    '.m4v', '.ts', '.m2ts', '.mpeg', '.mpg', '.3gp', '.ogv', '.vob',
]


def _exe_path() -> str | None:
    """Returns the bundled exe path, or None when running from source."""
    if getattr(sys, 'frozen', False):
        return sys.executable
    return None


def is_registered() -> bool:
    """True if the registry points to the current exe."""
    try:
        import winreg
        exe = _exe_path()
        if not exe:
            return False
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            _APP_KEY + r"\shell\open\command",
        )
        val, _ = winreg.QueryValueEx(key, "")
        winreg.CloseKey(key)
        return exe.lower() in val.lower()
    except Exception:
        return False


def register() -> bool:
    try:
        import winreg
        exe = _exe_path()
        if not exe:
            return False

        app_dir = os.path.dirname(exe)
        cmd = f'"{exe}" "%1"'
        hkcu = winreg.HKEY_CURRENT_USER

        def setval(path, name, value):
            key = winreg.CreateKey(hkcu, path)
            winreg.SetValueEx(key, name, 0, winreg.REG_SZ, value)
            winreg.CloseKey(key)

        setval(_APP_KEY,                          "FriendlyAppName", "Simple Playback")
        setval(_APP_KEY + r"\DefaultIcon",        "",                f'"{exe}",0')
        setval(_APP_KEY + r"\shell\open\command", "",                cmd)

        key = winreg.CreateKey(hkcu, _APP_KEY + r"\SupportedTypes")
        for ext in VIDEO_EXTENSIONS:
            winreg.SetValueEx(key, ext, 0, winreg.REG_SZ, "")
        winreg.CloseKey(key)

        key = winreg.CreateKey(hkcu, _APP_PATHS_KEY)
        winreg.SetValueEx(key, "",     0, winreg.REG_SZ, exe)
        winreg.SetValueEx(key, "Path", 0, winreg.REG_SZ, app_dir)
        winreg.CloseKey(key)

        for ext in VIDEO_EXTENSIONS:
            key = winreg.CreateKey(hkcu, f"Software\\Classes\\{ext}\\OpenWithList\\SimplePlayback.exe")
            winreg.CloseKey(key)

        return True
    except Exception:
        return False


def unregister() -> bool:
    try:
        import winreg
        hkcu = winreg.HKEY_CURRENT_USER

        def try_del(path):
            try:
                winreg.DeleteKey(hkcu, path)
            except Exception:
                pass

        try_del(_APP_KEY + r"\SupportedTypes")
        try_del(_APP_KEY + r"\DefaultIcon")
        try_del(_APP_KEY + r"\shell\open\command")
        try_del(_APP_KEY + r"\shell\open")
        try_del(_APP_KEY + r"\shell")
        try_del(_APP_KEY)
        try_del(_APP_PATHS_KEY)

        for ext in VIDEO_EXTENSIONS:
            try_del(f"Software\\Classes\\{ext}\\OpenWithList\\SimplePlayback.exe")

        return True
    except Exception:
        return False
