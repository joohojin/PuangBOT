@echo off
setlocal
cd /d "%~dp0"

where docker >nul 2>nul
if errorlevel 1 (
  echo Docker was not found. Skipping local SearXNG setup.
  echo Install Docker Desktop later if you want local AI web search through SearXNG.
  exit /b 1
)

docker compose version >nul 2>nul
if errorlevel 1 (
  echo Docker Compose was not found or is not available through "docker compose".
  echo Install/repair Docker Desktop later if you want local AI web search through SearXNG.
  exit /b 1
)

if not exist "searxng" mkdir "searxng"

if exist "searxng\settings.yml" (
  echo searxng\settings.yml already exists.
) else (
  echo Creating searxng\settings.yml from settings.example.yml...
  for /f "usebackq delims=" %%A in (`powershell -NoProfile -Command "[Convert]::ToBase64String([Security.Cryptography.RandomNumberGenerator]::GetBytes(48))"`) do set "SEARXNG_SECRET=%%A"
  powershell -NoProfile -Command "$template = Get-Content -Raw 'searxng\settings.example.yml'; $template.Replace('CHANGE_THIS_TO_A_LONG_RANDOM_SECRET', $env:SEARXNG_SECRET) | Set-Content -Encoding UTF8 'searxng\settings.yml'"
)

docker compose pull
docker compose up -d

echo.
echo SearXNG should be available at http://127.0.0.1:8080
echo Run test_searxng.cmd to verify the JSON API.
endlocal
