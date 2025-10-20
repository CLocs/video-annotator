#!/bin/bash

# Build script for VideoMarker on macOS
# Usage: ./build_macos.sh [--bundle-vlc]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Building VideoMarker for macOS...${NC}"

# Check if PyInstaller is installed
if ! command -v pyinstaller &> /dev/null; then
    echo -e "${RED}Error: PyInstaller not found. Install with: pip install pyinstaller${NC}"
    exit 1
fi

# Check if icon file exists
if [ ! -f "./docs/video_mark_icon.ico" ]; then
    echo -e "${YELLOW}Warning: Icon file not found at ./docs/video_mark_icon.ico${NC}"
    ICON_ARG=""
else
    ICON_ARG="--icon ./docs/video_mark_icon.ico"
fi

# Clean previous builds
echo "Cleaning previous builds..."
rm -rf build/ dist/ *.spec

if [ "$1" = "--bundle-vlc" ]; then
    echo -e "${GREEN}Building with VLC bundled...${NC}"
    
    # Try to find VLC installation
    VLC_PATHS=(
        "/Applications/VLC.app/Contents/MacOS/lib"
        "/usr/local/lib"  # Homebrew
        "/opt/homebrew/lib"  # Apple Silicon Homebrew
    )
    
    VLC_PATH=""
    for path in "${VLC_PATHS[@]}"; do
        if [ -d "$path" ] && [ -f "$path/libvlc.dylib" ]; then
            VLC_PATH="$path"
            break
        fi
    done
    
    if [ -z "$VLC_PATH" ]; then
        echo -e "${RED}Error: VLC not found. Please install VLC first.${NC}"
        echo "Try: brew install --cask vlc"
        exit 1
    fi
    
    echo "Found VLC at: $VLC_PATH"
    
    # Build with VLC bundled
    pyinstaller -F -n VideoMarker $ICON_ARG \
        --add-binary "$VLC_PATH/libvlc.dylib:." \
        --add-binary "$VLC_PATH/libvlccore.dylib:." \
        --add-data "$VLC_PATH/../plugins:vlc_plugins" \
        ./app/video_mark.py
    
    echo -e "${GREEN}Build complete! Executable size: ~80MB${NC}"
else
    echo -e "${GREEN}Building without VLC (requires VLC to be installed on target system)...${NC}"
    
    # Build without VLC bundled
    pyinstaller -F -n VideoMarker $ICON_ARG ./app/video_mark.py
    
    echo -e "${GREEN}Build complete! Executable size: ~15MB${NC}"
    echo -e "${YELLOW}Note: Users must have VLC installed on their system${NC}"
fi

echo -e "${GREEN}Executable created at: dist/VideoMarker${NC}"

# Optional: Code signing
if command -v codesign &> /dev/null; then
    echo -e "${YELLOW}To sign the executable for distribution, run:${NC}"
    echo "codesign --force --deep --sign \"Developer ID Application: Your Name\" dist/VideoMarker"
fi
