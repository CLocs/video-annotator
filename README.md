# Video Marker

## Intro

Mark Window
![VideoMark: Mark Window](docs/video-mark-window-v1.1.png)

Functions
- Space toggles play/pause.
- M or Double-click the big “MARK (double-click)” button to mark an event.
- U undoes last mark.
- S saves to CSV anytime (it also auto-saves on quit).

Notes
- Precision: VLC gives current time in milliseconds; we write seconds with millisecond precision (#.###).
- Double-click vs hotkey: The big button only registers a double-click (single clicks are ignored). Many participants prefer the M key—less cursor movement, fewer misses.
- Debounce: Default 250 ms between marks to avoid accidental duplicates

Save Window
![VideoMark: Save Window](docs/video-mark-window-v1.1-save.png)

# Developer Guide

## Setup

1. Install VLC (the desktop app):

- macOS: `brew install --cask vlc` or use link below
- Windows: install from https://www.videolan.org/vlc/
- Linux: your package manager (apt install vlc)

2. Install Python deps:

- python -m venv .venv
- pip install -r requirements.txt

## Run

```shell
python video_mark.py
```

## Build executable

### Windows

**Quick build (recommended):**
Build without VLC bundled (requires VLC on target system)
```cmd
.\build.bat
```

**Manual build:**

Option A (install VLC prior) - ~9 MB
```shell
pyinstaller -F -n VideoMarker --icon .\docs\video_mark_icon.ico .\app\video_mark.py
```
Note: Users must have VLC installed (matching 64-bit vs 32-bit).

Option B (VLC bundled in) - ~65 MB
```shell
pyinstaller -F -n VideoMarker --icon "./docs/video_mark_icon.ico" --add-binary "C:\Program Files\VideoLAN\VLC\libvlc.dll;." --add-binary "C:\Program Files\VideoLAN\VLC\libvlccore.dll;." --add-data "C:\Program Files\VideoLAN\VLC\plugins;vlc_plugins" ./app/video_mark.py
```

### macOS
~15 MB

**Quick build (recommended):**
```shell
# Build without VLC bundled (requires VLC on target system)
./build_macos.sh

# Build with VLC bundled (larger but self-contained)
./build_macos.sh --bundle-vlc
```

**Manual build:**

Option A (install VLC prior)
```shell
pyinstaller -F -n VideoMarker --icon ./docs/video_mark_icon.ico ./app/video_mark.py
```
Note: Users must have VLC installed via Homebrew or from videolan.org.

Option B (VLC bundled in)
```shell
# First, find VLC installation path (adjust if VLC is installed elsewhere)
VLC_PATH="/Applications/VLC.app/Contents/MacOS/lib"
pyinstaller -F -n VideoMarker --icon ./docs/video_mark_icon.ico \
  --add-binary "$VLC_PATH/libvlc.dylib:." \
  --add-binary "$VLC_PATH/libvlccore.dylib:." \
  --add-data "$VLC_PATH/../plugins:vlc_plugins" \
  ./app/video_mark.py
```
~80 MB

**Code signing (for distribution):**
```shell
# macOS
codesign --force --deep --sign "Developer ID Application: Your Name" dist/VideoMarker
```

### Windows Code Signing

**Quick start:**
For testing (self-signed)
```cmd
.\codesign_windows.bat create-cert
.\codesign_windows.bat sign
```

See [CODE_SIGNING_GUIDE.md](CODE_SIGNING_GUIDE.md) for detailed instructions including:
- Self-signed certificates (free, for testing)
- Commercial certificates (recommended for distribution)
- Certificate providers and pricing
- CI/CD integration
- Troubleshooting

**Requirements:**
- VLC Media Player installed (download from https://www.videolan.org/vlc/)



