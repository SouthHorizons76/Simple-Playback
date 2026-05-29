@echo off
setlocal enabledelayedexpansion
title Simple Playback - Build

echo ============================================================
echo  Simple Playback - PyInstaller Build
echo ============================================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Install from https://www.python.org/
    exit /b 1
)

:: Check that libmpv DLL exists
if not exist "dlls\mpv-2.dll" (
    echo ERROR: dlls\mpv-2.dll not found.
    echo.
    echo  1. Download the latest libmpv build for Windows:
    echo     https://sourceforge.net/projects/mpv-player-windows/files/libmpv/
    echo.
    echo  2. Extract the .7z archive.
    echo.
    echo  3. Copy ALL .dll files into the  dlls\  folder next to this script.
    echo     The folder should contain mpv-2.dll and several avcodec/avformat/etc DLLs.
    echo.
    exit /b 1
)

:: Clean previous build artifacts
echo [1/4] Cleaning previous build...
if exist "dist\SimplePlayback" rmdir /s /q "dist\SimplePlayback"
if exist "build" rmdir /s /q "build"

:: Install / update dependencies
echo [2/4] Installing dependencies...
python -m pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo ERROR: pip install failed.
    exit /b 1
)

:: Generate icon if it doesn't exist yet
if not exist "icons\app.ico" (
    echo [3/4] Generating placeholder icon...
    if not exist "icons" mkdir icons
    python generate_icon.py 2>nul
    if errorlevel 1 (
        echo   (Icon generation skipped - no icon will be embedded)
    )
) else (
    echo [3/4] Using existing icons\app.ico
)

:: Run PyInstaller
echo [4/4] Building with PyInstaller...
python -m PyInstaller build.spec --noconfirm
if errorlevel 1 (
    echo ERROR: PyInstaller build failed.
    exit /b 1
)

echo.
echo ============================================================
echo  Build successful!
echo  Output: dist\SimplePlayback\SimplePlayback.exe
echo ============================================================
echo.

:: Optionally open the output folder
:: explorer "dist\SimplePlayback"

endlocal
