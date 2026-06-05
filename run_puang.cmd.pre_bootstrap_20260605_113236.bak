@echo off
setlocal
cd /d "%~dp0"

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
