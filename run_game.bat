@echo off
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
   ".venv\Scripts\python.exe" --version >nul 2>&1
   if not errorlevel 1 (
       ".venv\Scripts\python.exe" "main.py"
       exit /b
   )
)
python "main.py"
