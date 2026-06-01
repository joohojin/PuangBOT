@echo off
setlocal

echo Testing SearXNG JSON API...
powershell -NoProfile -Command "$ErrorActionPreference='Stop'; $r = Invoke-RestMethod -Uri 'http://127.0.0.1:8080/search?q=ollama&format=json&language=ko-KR' -TimeoutSec 20; if (-not $r.results) { throw 'No results array returned.' }; 'OK: ' + $r.results.Count + ' result(s)'"

endlocal
