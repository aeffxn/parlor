@echo off
cd /d "%~dp0"
python server.py
if errorlevel 1 (
  echo.
  echo Parlor could not start. Install Python 3.10 or newer, then try again.
  pause
)

