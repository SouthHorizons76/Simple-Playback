# PyInstaller spec for Simple Playback
# Run with:  python -m PyInstaller build.spec --noconfirm

import glob
import os

block_cipher = None

# Collect all DLLs from the dlls\ folder (mpv-2.dll + FFmpeg companions)
_dlls_path = os.path.join(os.getcwd(), "dlls")
_dll_files = glob.glob(os.path.join(_dlls_path, "*.dll")) if os.path.isdir(_dlls_path) else []
binaries = [(dll, ".") for dll in _dll_files]

# App icon
_icon_path = os.path.join(os.getcwd(), "icons", "app.ico")
_has_icon = os.path.isfile(_icon_path)

a = Analysis(
    [os.path.join("src", "main.py")],
    pathex=[os.getcwd()],
    binaries=binaries,
    datas=[
        ("icons", "icons"),
    ] if os.path.isdir("icons") else [],
    hiddenimports=[
        "PySide6.QtCore",
        "PySide6.QtGui",
        "PySide6.QtWidgets",
        "mpv",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "matplotlib",
        "numpy",
        "scipy",
        "PIL",
        "PySide6.QtWebEngine",
        "PySide6.QtWebEngineCore",
        "PySide6.QtWebEngineWidgets",
        "PySide6.QtBluetooth",
        "PySide6.Qt3DCore",
        "PySide6.Qt3DRender",
        "PySide6.QtCharts",
        "PySide6.QtDataVisualization",
        "PySide6.QtMultimedia",
        "PySide6.QtLocation",
        "PySide6.QtPositioning",
        "PySide6.QtSensors",
        "PySide6.QtSerialPort",
        "PySide6.QtSql",
        "PySide6.QtTest",
        "PySide6.QtXml",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,          # folder mode — no single-file temp extraction
    name="SimplePlayback",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,                  # no console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    icon=_icon_path if _has_icon else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[
        # Do NOT compress these — UPX breaks some DLLs
        "mpv-2.dll",
        "libmpv-2.dll",
        "avcodec*.dll",
        "avformat*.dll",
        "avutil*.dll",
        "avdevice*.dll",
        "avfilter*.dll",
        "swscale*.dll",
        "swresample*.dll",
        "postproc*.dll",
    ],
    name="SimplePlayback",
)
