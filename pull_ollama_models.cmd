@echo off
cd /d "%~dp0"

where ollama >nul 2>nul
if errorlevel 1 (
  echo Ollama CLI not found. Install Ollama first, then run this file again.
  pause
  exit /b 1
)

ollama --version
ollama pull qwen2.5:1.5b
ollama pull qwen2.5:0.5b
ollama pull moondream

echo.
echo Optional higher-quality text model:
echo   ollama pull exaone3.5:2.4b
echo.
echo Optional heavier vision model:
echo   ollama pull gemma3:4b
echo.
curl http://127.0.0.1:11434/api/tags
echo.
pause
