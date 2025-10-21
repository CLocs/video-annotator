@echo off
REM Windows Code Signing Script for VideoMarker
REM Usage: codesign_windows.bat [create-cert|sign]

setlocal

if "%~1"=="create-cert" goto :create_cert
if "%~1"=="sign" goto :sign_exe
if "%~1"=="" goto :show_help
goto :show_help

:show_help
echo Windows Code Signing Script for VideoMarker
echo.
echo Usage:
echo   codesign_windows.bat create-cert    # Create a self-signed certificate (one-time)
echo   codesign_windows.bat sign           # Sign the VideoMarker.exe
echo.
echo Prerequisites:
echo   - Windows SDK (includes signtool.exe and makecert.exe)
echo   - Run as Administrator for certificate creation
echo.
echo For production use, obtain a code signing certificate from:
echo   - DigiCert, Sectigo, GlobalSign, etc.
echo.
goto :end

:create_cert
echo Creating self-signed certificate...
echo.
echo NOTE: This requires Administrator privileges
echo.

REM Create a self-signed certificate
makecert -r -pe -n "CN=VideoMarker Developer" -ss My -sr CurrentUser -sky signature -eku 1.3.6.1.5.5.7.3.3 VideoMarker.cer

if errorlevel 1 (
    echo Error: Failed to create certificate
    echo Make sure you have Windows SDK installed and are running as Administrator
    goto :end
)

echo.
echo Certificate created successfully!
echo.
echo Next steps:
echo 1. Install the certificate: Double-click VideoMarker.cer
echo 2. Import it to "Trusted Root Certification Authorities"
echo 3. Run: codesign_windows.bat sign
echo.
goto :end

:sign_exe
echo Signing VideoMarker.exe...
echo.

REM Check if executable exists
if not exist "dist\VideoMarker.exe" (
    echo Error: dist\VideoMarker.exe not found
    echo Please build the executable first
    goto :end
)

REM Find signtool.exe
set SIGNTOOL=
for %%i in (
    "C:\Program Files (x86)\Windows Kits\10\bin\*\x64\signtool.exe"
    "C:\Program Files (x86)\Windows Kits\10\bin\10.0.22621.0\x64\signtool.exe"
    "C:\Program Files (x86)\Windows Kits\10\bin\10.0.19041.0\x64\signtool.exe"
    "C:\Program Files (x86)\Microsoft SDKs\Windows\v7.1A\Bin\signtool.exe"
) do (
    if exist "%%~i" (
        set SIGNTOOL=%%~i
        goto :found_signtool
    )
)

echo Error: signtool.exe not found
echo Please install Windows SDK from:
echo https://developer.microsoft.com/en-us/windows/downloads/windows-sdk/
goto :end

:found_signtool
echo Found signtool at: %SIGNTOOL%
echo.

REM Sign with timestamp
"%SIGNTOOL%" sign /n "VideoMarker Developer" /t http://timestamp.digicert.com /fd SHA256 /v "dist\VideoMarker.exe"

if errorlevel 1 (
    echo.
    echo Error: Failed to sign executable
    echo Make sure the certificate is installed in your certificate store
    goto :end
)

echo.
echo ===================================
echo Successfully signed VideoMarker.exe
echo ===================================
echo.

REM Verify signature
echo Verifying signature...
"%SIGNTOOL%" verify /pa /v "dist\VideoMarker.exe"

goto :end

:end
