@echo off
REM Final Windows Build Script for VideoMarker with proper VLC bundling
REM Usage: build_final.bat [bundle-vlc] [clean]

setlocal enabledelayedexpansion

set BUNDLE_VLC=0
set CLEAN_BUILD=0

REM Parse command line arguments
:parse_args
if "%~1"=="" goto :start_build
if /i "%~1"=="bundle-vlc" (
    set BUNDLE_VLC=1
    shift
    goto :parse_args
)
if /i "%~1"=="clean" (
    set CLEAN_BUILD=1
    shift
    goto :parse_args
)
if /i "%~1"=="--help" goto :show_help
if /i "%~1"=="-h" goto :show_help
shift
goto :parse_args

:show_help
echo Final Windows Build Script for VideoMarker
echo.
echo Usage:
echo   build_final.bat                    # Build without VLC (requires VLC on target system)
echo   build_final.bat bundle-vlc         # Build with VLC bundled
echo   build_final.bat clean              # Clean build directories first
echo   build_final.bat bundle-vlc clean   # Build with VLC and clean first
echo.
echo Options:
echo   bundle-vlc    Bundle VLC with the executable (~65 MB)
echo   clean         Clean build directories before building
echo.
echo Examples:
echo   build_final.bat bundle-vlc
echo   build_final.bat bundle-vlc clean
goto :end

:start_build
echo === VideoMarker Windows Build Script (Final) ===
echo.

REM Check if we're in the right directory
if not exist "app\video_mark.py" (
    echo Error: video_mark.py not found. Please run this script from the project root directory.
    goto :end
)

REM Clean build directories if requested
if %CLEAN_BUILD%==1 (
    echo Cleaning build directories...
    if exist "build" rmdir /s /q "build"
    if exist "dist" rmdir /s /q "dist"
    if exist "*.spec" del /q "*.spec"
    echo Cleaned build directories
)

REM Activate virtual environment
if exist "venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call "venv\Scripts\activate.bat"
) else (
    echo Warning: Virtual environment not found. Make sure dependencies are installed.
)

REM Check if pyinstaller is available
pyinstaller --version >nul 2>&1
if errorlevel 1 (
    echo Error: PyInstaller not found. Please install it with: pip install pyinstaller
    goto :end
)

REM Build based on options
if %BUNDLE_VLC%==1 (
    call :build_with_vlc_final
) else (
    call :build_without_vlc
)

echo.
echo Build completed! Executable is in the 'dist' directory.
echo.

REM Show file sizes
if exist "dist\VideoMarker.exe" (
    for %%A in ("dist\VideoMarker.exe") do (
        set /a size_mb=%%~zA/1048576
        echo Executable size: !size_mb! MB
    )
)

echo === Build Summary ===
if %BUNDLE_VLC%==1 (
    echo VLC bundled with executable
    echo Self-contained - no external dependencies
    echo Larger file size but more portable
) else (
    echo Lightweight executable
    echo Requires VLC to be installed on target system
    echo Smaller file size
)

goto :end

:build_without_vlc
echo Building VideoMarker without VLC bundled...

pyinstaller -F -n VideoMarker --icon ".\docs\video_mark_icon.ico" ".\app\video_mark.py" --clean
if errorlevel 1 (
    echo Error: PyInstaller failed
    goto :end
)

echo Build completed successfully!
echo   Size: ~9 MB
echo   Note: Users must have VLC installed on their system
goto :eof

:build_with_vlc_final
echo Building VideoMarker with VLC bundled (final method)...

REM Find VLC installation
set VLC_FOUND=0
for %%P in (
    "C:\Program Files\VideoLAN\VLC"
    "C:\Program Files (x86)\VideoLAN\VLC"
    "C:\VLC"
) do (
    if exist "%%~P\libvlc.dll" if exist "%%~P\libvlccore.dll" if exist "%%~P\plugins" (
        set VLC_PATH=%%~P
        set VLC_FOUND=1
        echo Found VLC at: %%~P
        goto :vlc_found_final
    )
)

if %VLC_FOUND%==0 (
    echo Error: VLC installation not found in standard locations.
    echo Please install VLC from https://www.videolan.org/vlc/
    echo.
    echo Standard VLC locations checked:
    echo   - C:\Program Files\VideoLAN\VLC
    echo   - C:\Program Files (x86)\VideoLAN\VLC
    echo   - C:\VLC
    goto :end
)

:vlc_found_final
REM First, build the base executable without VLC bundling
echo Building base executable...
pyinstaller -F -n VideoMarker --icon ".\docs\video_mark_icon.ico" ".\app\video_mark.py" --clean

if errorlevel 1 (
    echo Error: PyInstaller failed
    goto :end
)

REM Now copy VLC files to the dist directory
echo Copying VLC files to executable directory...

REM Copy ALL DLLs from VLC directory (including dependencies)
echo Copying all VLC DLLs...
xcopy "%VLC_PATH%\*.dll" "dist\" /Y /Q >nul 2>&1

REM Copy VLC plugins to a vlc subdirectory
if not exist "dist\vlc" mkdir "dist\vlc"
echo Copying VLC plugins...
xcopy "%VLC_PATH%\plugins\*" "dist\vlc\" /E /I /Y /Q >nul 2>&1

echo Build completed successfully!
echo   Size: ~65 MB
echo   Note: VLC is bundled - no external dependencies required
echo   VLC files copied to dist directory
goto :eof

:end
