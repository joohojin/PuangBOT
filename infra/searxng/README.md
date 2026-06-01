# PuangBOT SearXNG

This folder contains the local SearXNG service used by PuangBOT's `/ai검색`
and mention-based `검색 ...` AI tool.

PuangBOT expects this endpoint by default:

```text
http://127.0.0.1:8080/search?q=ollama&format=json&language=ko-KR
```

## Files

- `docker-compose.yml`: local-only SearXNG container bound to `127.0.0.1:8080`.
- `searxng/settings.example.yml`: committed template with JSON output enabled.
- `searxng/settings.yml`: generated on the server by `setup_searxng.cmd`; not committed.
- `setup_searxng.cmd`: creates `settings.yml`, pulls the image, and starts SearXNG.
- `start_searxng.cmd`: starts the container.
- `stop_searxng.cmd`: stops the container.
- `test_searxng.cmd`: checks the JSON API that PuangBOT uses.

## First Run

Run from the repository root:

```bat
setup_searxng.cmd
test_searxng.cmd
```

Then enable the tool in Discord:

```text
/ai검색설정 사용:True 자동검색:False 결과개수:5
/ai도구상태
/ai검색 검색어:Ollama SearXNG 연결 방법
```

## Notes

- The compose file binds the service to `127.0.0.1`, so it is not exposed to
  the public network.
- Do not commit `searxng/settings.yml`; it contains the generated secret key.
- If port `8080` is already in use, change both `docker-compose.yml` and
  `ai_tools.json` to the same new port.
