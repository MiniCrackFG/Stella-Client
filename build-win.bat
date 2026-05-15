@echo off
REM =========================================
REM Stella Client - Windows Build Script
REM =========================================

echo.
echo === Stella Client Windows Build ===
echo.

REM 1. Install Python if not already installed
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo ERROR: Python not found. Install Python 3.12+ from https://python.org
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

REM 2. Create virtual environment
if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
)

REM 3. Activate and install dependencies
echo Installing dependencies...
call venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install pywebview minecraft-launcher-lib Pillow requests pypresence psutil pyinstaller

REM 4. Build with PyInstaller
echo.
echo Building executable...
pyinstaller main-win.spec

REM 5. Done
echo.
echo === Build complete! ===
echo Executable: dist\stella-client.exe
echo.
pause
