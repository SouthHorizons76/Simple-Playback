# Simple Playback

I was too lazy to find a video playback app that had all the features I actually needed and would use, so I just made one with no bloated features and shits

## Requirements

- Python 3.11+
- libmpv for Windows — download `mpv-dev-x86_64-*.7z` from [sourceforge.net/projects/mpv-player-windows/files/libmpv](https://sourceforge.net/projects/mpv-player-windows/files/libmpv/) and place all `.dll` files in the `dlls/` folder

## Run

```powershell
pip install -r requirements.txt
python src/main.py
```

## Build

```powershell
.\build.bat
```

Output goes to `dist/SimplePlayback/`.
