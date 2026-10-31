@echo off
setlocal
cd /d "%~dp0"

py -3.12 -m PyInstaller --clean --noconfirm --workpath build\DEADLAST main.spec
if errorlevel 1 (
    echo Build failed. Check the output above.
    exit /b 1
)

echo.
echo Build complete: "%~dp0dist\DEADLAST.exe"
exit /b 0
