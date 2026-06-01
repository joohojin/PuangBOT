@echo off
setlocal
cd /d "%~dp0"

if not exist "searxng\settings.yml" (
  echo searxng\settings.yml was not found.
  echo Run setup_searxng.cmd first.
  exit /b 1
)

docker compose up -d
endlocal
