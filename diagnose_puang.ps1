$ErrorActionPreference = "Continue"
Set-Location $PSScriptRoot

Write-Host "== PuangBOT diagnostic =="
Write-Host ""

Write-Host "== Python =="
python --version

Write-Host ""
Write-Host "== Bootstrap =="
python "bootstrap_puang.py"
if ($LASTEXITCODE -ne 0) {
  Write-Host "PuangBOT bootstrap: FAILED"
} else {
  Write-Host "PuangBOT bootstrap: OK"
}

Write-Host ""
Write-Host "== Syntax =="
$compileTarget = Join-Path $env:TEMP "PuangBOT_diagnostic.pyc"
python -c "import py_compile; py_compile.compile(r'Puang.py', cfile=r'$compileTarget', doraise=True)"
if ($LASTEXITCODE -eq 0) {
  Write-Host "Puang.py syntax: OK"
} else {
  Write-Host "Puang.py syntax: FAILED"
}

Write-Host ""
Write-Host "== Python packages =="
$modules = @(
  "discord",
  "nacl",
  "audioop",
  "yt_dlp",
  "edge_tts",
  "gtts",
  "aiohttp",
  "mcrcon",
  "PIL",
  "pytesseract",
  "pypdf"
)

foreach ($module in $modules) {
  python -c "import importlib.util as u; import sys; sys.exit(0 if u.find_spec('$module') else 1)"
  if ($LASTEXITCODE -eq 0) {
    Write-Host "$module : OK"
  } else {
    Write-Host "$module : MISSING"
  }
}

Write-Host ""
Write-Host "== Ollama =="
if (Get-Command ollama -ErrorAction SilentlyContinue) {
  ollama --version
  try {
    $tags = Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/tags" -TimeoutSec 5
    $tags.models | Select-Object name, size, modified_at | Format-Table -AutoSize
  } catch {
    Write-Host "Ollama API is not reachable at http://127.0.0.1:11434"
    Write-Host $_.Exception.Message
  }
} else {
  Write-Host "Ollama CLI not found."
}

Write-Host ""
Write-Host "== Local files =="
$files = @(
  "token.txt",
  "requirements.txt",
  "bootstrap_puang.py",
  "ai_models.example.json",
  "run_puang.cmd",
  "install_python_deps.cmd",
  "pull_ollama_models.cmd"
)

foreach ($file in $files) {
  if (Test-Path $file) {
    Write-Host "$file : OK"
  } else {
    Write-Host "$file : MISSING"
  }
}
