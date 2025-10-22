#!/bin/bash

# Build script for VideoMarker on macOS (PySide6 version)
# Usage: ./build_macos.sh

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Building VideoMarker for macOS (PySide6)...${NC}"

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
rm -rf build/ dist/

echo -e "${GREEN}Building with PySide6 (includes audio/video support)...${NC}"

# Build using spec file (works on macOS too)
pyinstaller VideoMarker.spec

# On macOS, PyInstaller creates .app bundles with --onefile
# If you want a .app bundle instead, use --windowed
echo -e "${GREEN}Build complete!${NC}"
echo -e "${GREEN}Executable created at: dist/VideoMarker${NC}"
echo -e "${YELLOW}Note: PySide6 multimedia codecs are bundled${NC}"

# Optional: Code signing
if command -v codesign &> /dev/null; then
    echo ""
    echo -e "${YELLOW}To sign the executable for distribution, run:${NC}"
    echo "codesign --force --deep --sign \"Developer ID Application: Your Name\" dist/VideoMarker"
fi
