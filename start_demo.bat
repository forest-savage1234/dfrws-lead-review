@echo off
cd /d "%~dp0"
py -3 -m lead_review serve
if errorlevel 1 (
  echo Python 3.11 or newer is required. See README.md.
  pause
)
