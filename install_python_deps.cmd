@echo off
setlocal
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
  echo [PuangBOT] ERROR: Python was not found in PATH.
  echo [PuangBOT] Install Python 3.10+ and enable "Add python.exe to PATH".
  pause
  exit /b 1
)

python "%~dp0bootstrap_puang.py" --force
if errorlevel 1 (
  echo [PuangBOT] ERROR: Dependency installation failed.
  pause
  exit /b 1
)

echo [PuangBOT] Dependency installation/check complete.
pause
endlocal
