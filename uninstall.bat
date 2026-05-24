@echo off
chcp 65001 >nul
echo ============================================================
echo Internet Generation JP Patch v1.0.0 - Uninstaller
echo ============================================================
echo.
echo Restores the original game files from .bak backups.
echo.
pause

python "%~dp0tools\patcher.py" --uninstall %*
if errorlevel 1 (
    echo [ERROR] Uninstall failed.
    pause
    exit /b 1
)

echo.
echo Restored to original. JP patch is now removed.
pause
