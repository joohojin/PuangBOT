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

echo [PuangBOT] Checking Python modules and required runtime files...
python "%~dp0bootstrap_puang.py"
if errorlevel 1 (
  echo [PuangBOT] ERROR: Bootstrap failed. Check the messages above.
  pause
  exit /b 1
)

echo [PuangBOT] Preparing local SearXNG search service...
call "%~dp0setup_searxng.cmd"
if errorlevel 1 (
  echo [PuangBOT] WARNING: SearXNG setup failed. AI web search may be unavailable.
) else (
  echo [PuangBOT] Testing SearXNG JSON API...
  call "%~dp0test_searxng.cmd"
  if errorlevel 1 (
    echo [PuangBOT] WARNING: SearXNG JSON API test failed. AI web search may be unavailable.
  )
)

echo [PuangBOT] Starting Discord bot...
python Puang.py
pause
endlocal
