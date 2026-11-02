@echo off
setlocal
cd /d "%~dp0"

set "PYTHON="
where py >nul 2>nul
if not errorlevel 1 py -c "import sys" >nul 2>nul
if not errorlevel 1 set "PYTHON=py"

if not defined PYTHON (
    where python >nul 2>nul
    if not errorlevel 1 python -c "import sys" >nul 2>nul
    if not errorlevel 1 set "PYTHON=python"
)

if not defined PYTHON (
    echo Python 3 is not installed. The Windows py launcher alone is not enough.
    echo Install Python from https://www.python.org/downloads/windows/
    echo Then close this window and double-click run.bat again.
    pause
    exit /b 1
)

echo Installing Flask requirements...
%PYTHON% -m pip install -r requirements.txt
if errorlevel 1 (
    echo Flask installation failed. Check your internet connection and Python installation.
    pause
    exit /b 1
)

echo Starting Hands Together at http://127.0.0.1:5000
%PYTHON% app.py
if errorlevel 1 pause
