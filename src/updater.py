import os
import sys
import json
import shutil
import tempfile
import subprocess
import urllib.request
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from .version import VERSION

GITHUB_REPO  = "SouthHorizons76/Simple-Playback"
_API_URL     = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
_RELEASES_URL = f"https://github.com/{GITHUB_REPO}/releases/latest"
_HEADERS     = {"User-Agent": "SimplePlayback-Updater", "Accept": "application/vnd.github+json"}

_EXTRACTOR_CANDIDATES = [
    (r"C:\Program Files\WinRAR\UnRAR.exe",       "unrar"),
    (r"C:\Program Files (x86)\WinRAR\UnRAR.exe", "unrar"),
    (r"C:\Program Files\WinRAR\WinRAR.exe",       "winrar"),
    (r"C:\Program Files (x86)\WinRAR\WinRAR.exe", "winrar"),
    (r"C:\Program Files\7-Zip\7z.exe",            "7zip"),
    (r"C:\Program Files (x86)\7-Zip\7z.exe",      "7zip"),
]


# ── helpers ────────────────────────────────────────────────────────────────

def _ver_tuple(v: str) -> tuple:
    return tuple(int(x) for x in v.lstrip("v").split("."))


def is_newer(tag: str) -> bool:
    try:
        return _ver_tuple(tag) > _ver_tuple(VERSION)
    except (ValueError, AttributeError):
        return False


def is_packaged() -> bool:
    return getattr(sys, "frozen", False)


def app_dir() -> str:
    return str(Path(sys.executable).parent) if is_packaged() else ""


def app_exe() -> str:
    return sys.executable if is_packaged() else ""


def is_dir_writable(path: str) -> bool:
    """Return True if we can create files in path (quick UAC/permission probe)."""
    try:
        test = os.path.join(path, ".sp_write_test")
        with open(test, "w"):
            pass
        os.remove(test)
        return True
    except OSError:
        return False


def find_extractor() -> tuple | None:
    """Return (tool_path, kind) for the first usable RAR extractor, or None."""
    for cmd, kind in [("unrar", "unrar"), ("7z", "7zip"), ("7za", "7zip")]:
        p = shutil.which(cmd)
        if p:
            return (p, kind)
    for path, kind in _EXTRACTOR_CANDIDATES:
        if os.path.isfile(path):
            return (path, kind)
    return None


def _run_extract(rar_path: str, dest_dir: str, extractor: tuple) -> bool:
    tool, kind = extractor
    sep = os.sep
    dest_sep = dest_dir.rstrip(sep) + sep
    if kind == "unrar":
        cmd = [tool, "x", "-y", "-o+", rar_path, dest_sep]
    elif kind == "winrar":
        cmd = [tool, "x", rar_path, f"-o{dest_sep}", "-y"]
    else:  # 7zip
        cmd = [tool, "x", rar_path, f"-o{dest_dir}", "-y"]
    result = subprocess.run(cmd, capture_output=True)
    return result.returncode == 0


def write_updater_script(source_dir: str, dest_dir: str, exe_path: str, pid: int, script_dir: str) -> str:
    """
    Write a PowerShell script that waits for the app to exit, robocopy-updates
    the install directory, then relaunches the app.
    """
    src = source_dir.replace("'", "''")
    dst = dest_dir.replace("'", "''")
    exe = exe_path.replace("'", "''")

    # Log in %TEMP% root so it's easy to find regardless of what happens to script_dir
    log = os.path.join(os.environ.get("TEMP", script_dir), "sp_update_log.txt").replace("'", "''")

    # Capture robocopy stdout into a variable to avoid the 2>&1 / ErrorRecord issue
    # in PS 5.1, then write it directly to the log.
    script = (
        f"$log = '{log}'\n"
        f"\"$(Get-Date -f 'HH:mm:ss') Updater started, waiting for PID {pid}\" | Out-File -FilePath $log -Force\n"
        f"$p = {pid}\n"
        f"while ($null -ne (Get-Process -Id $p -ErrorAction SilentlyContinue)) {{\n"
        f"    Start-Sleep -Milliseconds 500\n"
        f"}}\n"
        f"\"$(Get-Date -f 'HH:mm:ss') App exited, running robocopy\" | Add-Content $log\n"
        f"$out = robocopy '{src}' '{dst}' /E /IS /IT /R:3 /W:2\n"
        f"$out | Add-Content $log\n"
        f"$rc = $LASTEXITCODE\n"
        f"\"$(Get-Date -f 'HH:mm:ss') robocopy exit code: $rc\" | Add-Content $log\n"
        f"if ($rc -lt 8) {{\n"
        f"    \"$(Get-Date -f 'HH:mm:ss') Launching updated app\" | Add-Content $log\n"
        f"    Start-Process '{exe}'\n"
        f"}} else {{\n"
        f"    \"$(Get-Date -f 'HH:mm:ss') Update FAILED (robocopy error $rc) - try running as Administrator\" | Add-Content $log\n"
        f"}}\n"
        f"Remove-Item -LiteralPath $PSCommandPath -Force -ErrorAction SilentlyContinue\n"
    )
    script_path = os.path.join(script_dir, "sp_update.ps1")
    with open(script_path, "w", encoding="utf-8") as fh:
        fh.write(script)
    return script_path


def launch_updater_script(script_path: str) -> None:
    """Launch the updater PowerShell script hidden, independent of this process."""
    # CREATE_NO_WINDOW only — combining DETACHED_PROCESS with CREATE_NO_WINDOW
    # can silently prevent the process from starting on some Windows configs.
    subprocess.Popen(
        [
            "powershell.exe",
            "-NoProfile",
            "-NonInteractive",
            "-WindowStyle", "Hidden",
            "-ExecutionPolicy", "Bypass",
            "-File", script_path,
        ],
        creationflags=0x08000000,  # CREATE_NO_WINDOW
    )


# ── background threads ──────────────────────────────────────────────────────

class CheckThread(QThread):
    done  = Signal(dict)
    error = Signal(str)

    def run(self):
        try:
            req = urllib.request.Request(_API_URL, headers=_HEADERS)
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
            tag      = data.get("tag_name", "")
            html_url = data.get("html_url", _RELEASES_URL)
            body     = data.get("body", "")
            name     = data.get("name", tag)
            rar_url  = next(
                (a["browser_download_url"] for a in data.get("assets", [])
                 if a.get("name", "").lower().endswith(".rar")),
                None,
            )
            self.done.emit({"tag": tag, "name": name, "body": body,
                            "rar_url": rar_url, "html_url": html_url})
        except Exception as exc:
            self.error.emit(str(exc))


class DownloadThread(QThread):
    progress = Signal(int, int)  # bytes_done, bytes_total
    done     = Signal(str)       # path to downloaded .rar
    error    = Signal(str)

    def __init__(self, url: str, dest_dir: str):
        super().__init__()
        self._url      = url
        self._dest_dir = dest_dir
        self._aborted  = False

    def abort(self) -> None:
        self._aborted = True

    def run(self):
        try:
            filename  = self._url.split("/")[-1]
            dest_path = os.path.join(self._dest_dir, filename)
            req = urllib.request.Request(self._url, headers={"User-Agent": "SimplePlayback-Updater"})
            with urllib.request.urlopen(req, timeout=120) as resp:
                total      = int(resp.headers.get("Content-Length", 0))
                downloaded = 0
                with open(dest_path, "wb") as fh:
                    while not self._aborted:
                        chunk = resp.read(65536)
                        if not chunk:
                            break
                        fh.write(chunk)
                        downloaded += len(chunk)
                        self.progress.emit(downloaded, total)
            if not self._aborted:
                self.done.emit(dest_path)
        except Exception as exc:
            self.error.emit(str(exc))


class ExtractThread(QThread):
    done  = Signal(str)  # path to extracted app folder
    error = Signal(str)

    def __init__(self, rar_path: str, dest_dir: str, extractor: tuple):
        super().__init__()
        self._rar       = rar_path
        self._dest_dir  = dest_dir
        self._extractor = extractor

    def run(self):
        try:
            out = os.path.join(self._dest_dir, "extracted")
            os.makedirs(out, exist_ok=True)
            if not _run_extract(self._rar, out, self._extractor):
                self.error.emit("Extraction returned a non-zero exit code.")
                return
            # If the archive unpacks to a single subfolder, use that as source
            items = [p for p in Path(out).iterdir()]
            if len(items) == 1 and items[0].is_dir():
                out = str(items[0])
            self.done.emit(out)
        except Exception as exc:
            self.error.emit(str(exc))
