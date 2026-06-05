# PuangBOT 로컬 AI 준비 절차

이 문서는 Ollama와 모델을 설치한 뒤 PuangBOT의 Discord AI 기능을 바로 켜기 위한 운영 절차다.

## 현재 코드 상태

- AI 기본 주소: `http://127.0.0.1:11434`
- 기본 텍스트 프로필: `local-fast`
- 텍스트 백업 프로필: `local-tiny`
- Gemma 4 프로필: `local-gemma4` (`gemma4:latest`)
- 기본 백업 정책: `safe_degrade`
- 이미지 직접 분석은 `capabilities`에 `image`가 있는 모델에서만 사용한다.
- 이미지 직접 분석 실패 시 OCR/이미지 메타데이터 기반 텍스트 대체 분석으로 내려간다.
- 채널별 설정 파일: `ai_settings.json`
- 모델 프로필 파일: `ai_models.json`
- Provider 설정 파일: `ai_providers.json`
- AI 도구 설정 파일: `ai_tools.json`
- 서버/RCON 설정 파일: `server_settings.json`
- 채널 기록 검색 DB: `ai_history.sqlite3`
- 단기 기억 파일: `ai_short_memory.json`
- 장기 기억 파일: `ai_long_memory.json`

위 JSON 파일들은 런타임 설정/기억 파일이라 `.gitignore`에 포함되어 있다. 예시 파일은 `*.example.json`으로 제공된다.

## 0. 서버/RCON 설정

마인크래프트 RCON 비밀번호는 더 이상 `Puang.py`에 직접 넣지 않는다. 서버에서 환경변수로 설정하는 방식을 권장한다.

```bat
setx PUANG_RCON_PASSWORD "server.properties에 설정한 rcon.password"
```

현재 터미널에 바로 적용하려면 새 터미널을 열거나 아래처럼 임시 설정한다.

```bat
set PUANG_RCON_PASSWORD=server.properties에_설정한_rcon.password
```

서버 경로와 RCON 포트를 바꾸려면 `server_settings.example.json`을 `server_settings.json`으로 복사한 뒤 수정한다.

```json
{
  "minecraft": {
    "rcon_host": "127.0.0.1",
    "rcon_port": 25575,
    "rcon_password_env": "PUANG_RCON_PASSWORD",
    "mc_root_dir": "server/mc",
    "playit_dir": "server",
    "playit_link": "playit.gg.lnk"
  }
}
```

`server_settings.json`은 런타임 파일이라 git에 올리지 않는다.

## 1. Python 패키지 설치

```bat
install_python_deps.cmd
```

수동으로 설치할 때는 아래 명령을 사용한다.

```bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Python 3.13에서는 음성 기능 호환을 위해 `audioop-lts`가 같이 설치된다.

## 2. Ollama 설치

Windows용 Ollama를 설치한 뒤 아래 명령이 동작하는지 확인한다.

- 공식 다운로드: <https://ollama.com/download/windows>
- API 문서: <https://github.com/ollama/ollama/blob/main/docs/api.md>

```bat
ollama --version
curl http://127.0.0.1:11434/api/tags
```

Ollama 앱이 백그라운드에서 서버를 띄우지 않는 환경이면 별도 터미널에서 실행한다.

```bat
ollama serve
```

## 3. 권장 모델 설치

저사양 Windows/i5/내장 그래픽/8GB RAM 기준 기본 세트:

```bat
pull_ollama_models.cmd
```

수동 설치 명령:

```bat
ollama pull qwen2.5:1.5b
ollama pull qwen2.5:0.5b
ollama pull moondream
```

여유가 있으면 선택 설치:

```bat
ollama pull exaone3.5:2.4b
ollama pull gemma3:4b
ollama pull gemma4:latest
```

## 4. 로컬 웹 검색(SearXNG) 설치

PuangBOT의 `/ai검색`과 맨션 기반 `검색 ...` 도구는 로컬 SearXNG JSON API를 사용한다.
GitHub에는 실행 구성이 포함되어 있고, 서버별 비밀값이 들어가는 `settings.yml`은 서버에서 생성한다.

구성 위치:

```text
infra/searxng/
  docker-compose.yml
  searxng/settings.example.yml
  setup_searxng.cmd
  start_searxng.cmd
  stop_searxng.cmd
  test_searxng.cmd
```

서버에서 최초 1회 실행:

```bat
setup_searxng.cmd
test_searxng.cmd
```

`run_puang.cmd`는 봇 실행 전에 `setup_searxng.cmd`와 `test_searxng.cmd`를 자동으로 호출한다.
SearXNG 준비나 테스트가 실패해도 봇 자체는 계속 실행되며, 이 경우 AI 웹 검색만 사용할 수 없다.

정상이라면 아래 JSON API가 응답한다.

```text
http://127.0.0.1:8080/search?q=ollama&format=json&language=ko-KR
```

Discord에서 검색 도구를 켠다.

```text
/ai도구마이그레이션
/ai검색설정 사용:True 자동검색:False 모르면검색:True 기본provider:searxng-local 이미지provider:searxng-local 상세검색:False 결과개수:5
/ai도구상태
/ai검색 검색어:Ollama SearXNG 연결 방법 종류:웹 provider:auto
/ai검색 검색어:Ollama SearXNG 연결 방법 종류:웹 provider:auto 상세검색:True
/ai검색 검색어:Gemma4 종류:이미지 provider:searxng-local
/ai검색 검색어:오늘 AI 뉴스 종류:뉴스 provider:auto
```

맨션 뒤 수동 검색도 가능하다.

```text
@푸앙봇 검색 Gemma4 Ollama 사용법
@푸앙봇 /검색 마인크래프트 서버 최적화 최신 정보
@푸앙봇 뉴스검색 오늘 AI 뉴스
@푸앙봇 이미지검색 검은색 게이밍 키보드
@푸앙봇 영상검색 Ollama 튜토리얼
@푸앙봇 렌즈검색 이 이미지 원본 찾아줘 + 이미지 첨부
```

`ai_tools.json` 기본값은 안전하게 검색이 꺼져 있다. SearXNG 포트를 바꾸면 `ai_tools.json`의
`search.providers.searxng-local.base_url`도 같은 주소로 바꾼다.

검색 provider 구조:

```text
searxng-local: 로컬 SearXNG, web/news/image/video
duckduckgo-lite: Docker/API 키 없이 쓰는 DuckDuckGo Lite HTML 검색, web/news
brave-api: Brave Search API, web/news/image/video, BRAVE_SEARCH_API_KEY 필요
google-cse: Google Custom Search JSON API, web/image, GOOGLE_SEARCH_API_KEY와 GOOGLE_SEARCH_CX 필요
serpapi-lens: SerpAPI Google Lens, lens, SERPAPI_API_KEY 필요
```

Provider의 URL/API 키/활성화 여부는 Discord 명령어가 아니라 서버의 `ai_tools.json`에서 직접 관리한다.
Discord에서는 `/ai검색`의 `provider` 옵션으로 이미 등록된 provider ID만 선택한다.
Docker가 설치되어 있지 않거나 SearXNG가 아직 준비되지 않은 서버에서는 `duckduckgo-lite`를 기본 provider로 두면 즉시 웹 검색이 가능하다.
이 방식은 검색어가 DuckDuckGo로 전송되는 외부 검색이다. 완전 로컬 검색을 원하면 Docker/SearXNG를 준비한 뒤 기본 provider를 `searxng-local`로 되돌린다.

상세검색을 켜면 검색 결과의 상위 URL 본문 일부를 HTTP로 가져와 `본문 발췌` 블록으로 Ollama에 전달한다.
이 값은 `ai_tools.json`의 `search.fetch_pages`, `search.fetch_page_limit`, `search.page_max_chars`,
`search.context_max_chars`로 조절한다. 기본값은 빠른 검색을 위해 `fetch_pages: false`이고,
`/ai검색 상세검색:True`를 주면 해당 요청에서만 강제로 본문 발췌를 수행한다.
같은 URL 반복 접근을 줄이기 위해 프로세스 메모리 캐시가 적용되며, `search.cache_enabled`,
`search.cache_ttl_seconds`로 조절한다.

Ollama 전달 구조:

```text
[웹/뉴스/이미지/영상 검색 결과]
1. 제목
URL: ...
요약: ...
본문 발췌: ...  # 상세검색일 때만

[사용자 요청]
검색 결과를 바탕으로 답변...
```

`모르면검색`이 켜져 있으면 푸앙봇이 먼저 로컬 모델로 답변을 시도한 뒤, 답변에 "잘 모르겠다",
"확인할 수 없다", "최신 정보가 필요하다", "현재 기준 확인 필요" 같은 불확실 표현이 포함될 때 한 번만 등록된 검색 provider로 검색하고
검색 결과를 붙여 다시 답변한다. 이때 `search.fetch_pages_on_uncertain`이 true면 본문 발췌까지 추가한다.
명시적으로 `검색 ...` 또는 `/ai검색`을 사용한 경우에는 중복 검색하지 않는다.

## 5. 모델 프로필 커스터마이징

기본 내장 프로필만으로도 동작한다. 직접 바꾸려면 `ai_models.example.json`을 `ai_models.json`으로 복사한 뒤 수정한다.

프로필 형식:

```json
{
  "profiles": {
    "local-custom": {
      "label": "표시 이름",
      "provider": "local-ollama",
      "model": "gemma4:latest",
      "capabilities": ["text", "image"],
      "privacy": "local",
      "selectable": true,
      "visible": true,
      "group": "local",
      "context": 4096,
      "timeout": 120,
      "max_tokens": 2048,
      "fallbacks": ["local-fast"],
      "note": "운영 메모"
    }
  }
}
```

Provider/API 키/URL은 `ai_providers.json`에서만 관리한다. Discord에서는 등록된 프로필만 선택한다.

## 6. Discord에서 켜는 순서

봇을 재시작한 뒤 아래 순서로 확인한다.

```text
/ai모델목록
/ai켜기 채널:#ai 모드:멘션할 때만 답변 프로필:local-gemma4 이미지프로필:local-gemma4 문서프로필:local-gemma4 백업프로필:local-fast 백업정책:안전 백업
/ai진단 채널:#ai
/ai상태 채널:#ai
/ai응답설정 방식:자동 긴답변기준:1900 최대생성토큰:4096
```

상시 대화 채널로 운영할 때만 `/ai켜기`의 모드를 `상시 대화`로 설정한다. 일반 채널 전체를 상시 대화로 켜면 모든 메시지가 단기/장기 기억에 들어가고 답변 요청도 늘어난다.

## 7. 채널 기록 검색

채널 기록은 `ai_history.sqlite3`에 SQLite로 저장한다. 새 메시지는 봇 실행 중 자동 인덱싱되고,
오래된 메시지는 명령어로 백필한다.

```text
/ai기록설정 사용:True 자동참고:False 기본검색개수:8
/ai기록인덱스 채널:#대상채널 최대개수:5000
/ai기록검색 검색어:서버 설정 질문:예전에 이야기한 서버 설정을 정리해줘
```

몇 년 전 기록까지 찾으려면 기간을 나눠 여러 번 인덱싱한다.

```text
/ai기록인덱스 채널:#대상채널 시작일:2023-01-01 종료일:2023-12-31 최대개수:50000
```

봇에 `Read Message History`와 `Message Content Intent`가 필요하다.

## 8. 진단

로컬에서 전체 준비 상태를 확인한다.

```powershell
powershell -ExecutionPolicy Bypass -File .\diagnose_puang.ps1
test_searxng.cmd
```

## 9. 이미지와 문서 처리

- 이미지: 모델이 `image` 기능을 지원하면 Discord 첨부 이미지를 다운로드해 base64로 직접 전달한다.
- 이미지 fallback: 직접 분석 실패 시 Pillow 이미지 정보와 가능하면 Tesseract OCR 결과를 텍스트로 넘긴다.
- TXT/MD/JSON/CSV/log 등: 텍스트로 추출해 프롬프트에 포함한다.
- PDF: `pypdf` 또는 `PyPDF2`로 앞쪽 최대 8페이지를 추출한다.
- DOCX: 내부 `word/document.xml`에서 텍스트를 추출한다.

OCR까지 제대로 쓰려면 Python 패키지 `pytesseract` 외에 Windows용 Tesseract 프로그램도 별도로 설치해야 한다.
