@echo off
chcp 65001 >nul
echo ============================================================
echo Internet Generation JP Patch v1.0.0 - Installer
echo ============================================================
echo.
echo This installer applies the Japanese translation patch
echo to your installed copy of Internet Generation (Steam).
echo.
echo - Creates .bak backups before injection
echo - Safe to re-run (re-injects from .bak)
echo - Run uninstall.bat to revert to original
echo.
echo (Detailed instructions in README.md, in Japanese)
echo.
pause

where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.10 or later.
    echo   https://www.python.org/downloads/
    echo   Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

python -c "import UnityPy" >nul 2>nul
if errorlevel 1 (
    echo Installing required Python packages: UnityPy openpyxl Pillow ...
    pip install UnityPy openpyxl Pillow
    if errorlevel 1 (
        echo [ERROR] pip install failed. Please run manually:
        echo   pip install UnityPy openpyxl Pillow
        pause
        exit /b 1
    )
)

python "%~dp0tools\patcher.py" %*
if errorlevel 1 (
    echo.
    echo [ERROR] Patch failed.
    pause
    exit /b 1
)

echo.
echo Done. Launch Internet Generation from Steam.
pause
