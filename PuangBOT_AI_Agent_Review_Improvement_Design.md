# PuangBOT AI Agent Review Improvement Design

작성일: 2026-06-02  
대상 프로젝트: PuangBOT  
대상 파일 기준: `Puang.py`, `ai_tools.json`, `ai_tools.example.json`, `AI_SETUP.md`

## 1. 목적

이 문서는 현재 PuangBOT의 AI 에이전트, 검색 도구, 기억 시스템, 첨부 처리, 운영 보안 구조를 코드 리뷰 결과에 맞춰 개선하기 위한 설계서다.

현재 봇은 Discord 음악/TTS/마인크래프트 서버 관리 기능 위에 Ollama 기반 로컬 LLM, 채널 기억, 문서/이미지 처리, SearXNG 기반 검색 기능이 추가된 상태다. 기능 범위는 넓어졌지만 단일 파일 중심 구조와 런타임 JSON 설정 의존도가 높아졌기 때문에, 다음 단계에서는 안정성, 보안성, 관측성, 장기 운영성을 우선으로 개선한다.

## 2. 현재 상태 요약

### 2.1 이미 구현된 기능

- Ollama native `/api/chat` 연동
- OpenAI compatible API provider 구조
- Discord 명령어 기반 AI 켜기/끄기/상태/패널
- 모델 프로필 선택
- 텍스트/이미지/문서 fallback 라우팅
- 긴 AI 답변 텍스트 파일 첨부 전송
- 채널별 단기/장기 기억 파일
- SQLite 기반 채널 기록 인덱싱/검색
- SearXNG/Brave/Google CSE/SerpAPI Lens provider 설계
- `/ai검색`, `/ai검색설정`, `/ai도구상태`
- 검색 결과 URL 본문 발췌 기반 상세검색
- 모르는 답변 감지 후 자동 검색 재시도
- 음악/TTS 믹싱과 ducking
- 음악 QueueView, 선택 삭제, 확인 View

### 2.2 핵심 리뷰 결과

- RCON 비밀번호가 코드에 직접 들어가 있다.
- 실제 런타임 `ai_tools.json`이 새 `search.providers` 구조를 아직 명시적으로 따르지 않는다.
- AI 기억 JSON 파일은 동시 쓰기와 무한 증가에 약하다.
- `on_ready`에서 백그라운드 task 중복 시작 가능성이 있다.
- 자동 검색 트리거와 불확실성 판정이 과하게 넓다.
- 검색 결과 정규화에서 일반 URL이 이미지 URL로 들어갈 수 있다.
- PDF 처리 예외가 전체 AI 응답 실패로 번질 수 있다.
- AI/검색/첨부 처리 코드가 `Puang.py`에 집중되어 회귀 위험이 높다.

## 3. 개선 원칙

1. 기존 기능을 유지한다.
2. 서버 운영자가 직접 관리해야 하는 값은 Discord 명령어보다 서버 설정 파일과 환경변수에 둔다.
3. Discord 사용자가 바꿔도 되는 값은 명령어와 UI에서 제공한다.
4. 로컬 모델과 외부 API provider는 같은 추상 구조로 다룬다.
5. AI가 도구를 사용할 때는 근거, 출처, 실패 원인을 남긴다.
6. 오래 걸리는 작업은 큐, 취소, 상태 조회가 가능해야 한다.
7. 런타임 데이터는 JSON 파일보다 SQLite 중심으로 옮긴다.
8. 자동 검색은 "많이 검색"보다 "필요할 때 정확히 검색"하는 방향으로 조정한다.

## 4. 우선순위 로드맵

### Phase 1. 운영 보안과 설정 정리

목표: 지금 서버에 바로 적용해도 위험하지 않도록 비밀값과 런타임 설정을 분리한다.

작업:

- `RCON_PASSWORD`를 코드에서 제거한다.
- `server_settings.json` 또는 환경변수 `PUANG_RCON_PASSWORD`를 도입한다.
- `ai_tools.json`을 새 스키마로 마이그레이션하는 함수 또는 명령을 추가한다.
- `/ai도구상태`에서 현재 설정 파일이 구형인지 경고한다.
- `run_puang.cmd` 시작 시 설정 검증을 수행한다.

예상 파일:

- `Puang.py`
- `server_settings.example.json`
- `ai_tools.example.json`
- `AI_SETUP.md`

완료 기준:

- 코드에 RCON 비밀번호가 남아 있지 않다.
- `ai_tools.json`이 구형 구조여도 봇이 새 구조로 안전하게 병합한다.
- 운영자는 API key/provider URL을 Discord 명령어가 아니라 서버 파일에서 관리한다.

### Phase 2. AI 기억 저장소 안정화

목표: 채널별 기억을 장기 운영 가능한 구조로 바꾼다.

현재 문제:

- `ai_short_memory.json`, `ai_long_memory.json`은 파일 전체 read/write 방식이다.
- 동시 AI 응답이 겹치면 기록 누락 가능성이 있다.
- 장기 기억은 무한히 커질 수 있다.
- 대화 기억과 채널 기록 검색 DB가 분리되어 중복된다.

설계:

- `ai_memory.sqlite3` 또는 기존 `ai_history.sqlite3`에 memory table을 추가한다.
- 단기 기억은 최근 N개를 SQL로 조회한다.
- 장기 기억은 원문 로그와 요약 메모를 분리한다.
- 채널별, 유저별, 주제별 memory scope를 둔다.

권장 테이블:

```sql
CREATE TABLE IF NOT EXISTS ai_memory_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  guild_id TEXT NOT NULL,
  channel_id TEXT NOT NULL,
  message_id TEXT,
  role TEXT NOT NULL,
  author_id TEXT,
  author_name TEXT,
  content TEXT,
  attachment_summary TEXT,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS ai_memory_summaries (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  guild_id TEXT NOT NULL,
  channel_id TEXT NOT NULL,
  scope TEXT NOT NULL,
  summary TEXT NOT NULL,
  source_start_at TEXT,
  source_end_at TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
```

추가 명령:

- `/ai기억상태`
- `/ai기억요약`
- `/ai기억삭제`
- `/ai기억내보내기`

완료 기준:

- JSON 기억 파일 없이도 최근 대화 기억이 동작한다.
- 장기 기억은 일정 개수 또는 기간마다 요약된다.
- 채널별 기억 삭제가 가능하다.

### Phase 3. 검색 에이전트 품질 개선

목표: 검색이 가능한 상태를 넘어, 검색 근거를 읽고 요약하는 에이전트로 개선한다.

현재 구조:

1. 사용자가 명시적으로 `/ai검색` 또는 `검색 ...`을 요청한다.
2. 자동검색이 켜져 있으면 키워드로 검색 필요성을 감지한다.
3. 답변이 불확실하면 한 번 검색 후 재답변한다.
4. 상세검색이면 검색 결과 URL 본문 일부를 가져와 prompt에 붙인다.

문제:

- 키워드 기반 검색 판정은 오탐이 많다.
- "검색", "인터넷" 같은 단어가 답변에 포함되면 불필요한 재검색이 발생할 수 있다.
- 검색 결과의 신뢰도와 출처 사용 여부가 사용자에게 충분히 드러나지 않는다.
- 검색 결과 본문 발췌가 HTML noise를 포함할 수 있다.

개선 설계:

#### 3.1 Tool Planner 추가

AI 응답 전에 가벼운 planner를 실행한다. planner는 실제 답변을 하지 않고 도구 사용 계획만 JSON으로 반환한다.

예시:

```json
{
  "need_search": true,
  "search_type": "web",
  "query": "Ollama SearXNG Discord bot integration",
  "need_history": false,
  "need_attachment_read": true,
  "reason": "최신 설정과 첨부 문서 내용이 필요함"
}
```

적용 방식:

- 기본은 현재 키워드 감지를 유지한다.
- `search.planner_enabled=true`이면 planner를 우선 사용한다.
- planner 실패 시 기존 키워드 방식으로 fallback한다.

#### 3.2 검색 결과 Evidence 객체 도입

검색 결과를 단순 문자열이 아니라 evidence list로 관리한다.

```json
{
  "title": "문서 제목",
  "url": "https://example.com",
  "provider": "searxng-local",
  "snippet": "검색 요약",
  "page_excerpt": "본문 발췌",
  "fetched_at": "2026-06-02T15:00:00+09:00",
  "used_in_answer": false,
  "trust_hint": "official|community|unknown"
}
```

답변 후에는 사용한 출처를 Embed footer 또는 별도 field로 표시한다.

#### 3.3 상세검색 캐시

같은 URL 본문을 반복 fetch하지 않도록 캐시한다.

권장 테이블:

```sql
CREATE TABLE IF NOT EXISTS ai_search_cache (
  url TEXT PRIMARY KEY,
  title TEXT,
  content TEXT,
  content_hash TEXT,
  fetched_at TEXT NOT NULL,
  expires_at TEXT NOT NULL
);
```

기본 TTL:

- 일반 웹: 24시간
- 뉴스: 2시간
- 공식 문서: 7일
- 실패 결과: 10분

#### 3.4 자동 검색 판정 정밀화

기존 `is_ai_answer_uncertain()`을 두 단계로 나눈다.

- `detect_uncertainty(answer)`: 답변이 불확실한지 판단
- `detect_search_need(user_text, answer)`: 검색으로 해결 가능한지 판단

재검색을 유발하는 표현에서 `"검색"`, `"인터넷"` 단독 매칭은 제거한다. 대신 다음과 같은 패턴을 사용한다.

- "최신 정보가 필요"
- "현재 기준"
- "확인할 수 없다"
- "공식 문서 확인 필요"
- "실시간 정보"
- "가격/일정/버전/정책"

완료 기준:

- 명시 검색은 그대로 동작한다.
- 자동검색은 오탐이 줄어든다.
- 상세검색 결과에는 출처와 본문 발췌 여부가 표시된다.

### Phase 4. 첨부 파일 처리 안정화

목표: PDF/DOCX/TXT/이미지 처리 실패가 전체 AI 응답 실패로 이어지지 않게 한다.

개선 대상:

- PDF 암호화/스캔본/손상 파일 예외 처리
- PDF OCR fallback
- DOCX 표/문단 구조 보존
- 긴 텍스트 chunking
- 첨부 파일 처리 결과 요약 Embed

설계:

```python
{
  "filename": "...",
  "kind": "pdf",
  "status": "ok|partial|failed",
  "text": "...",
  "warnings": ["스캔 PDF라 OCR fallback 사용"],
  "token_estimate": 3200
}
```

처리 흐름:

1. 파일 크기와 MIME 확인
2. 확장자별 parser 선택
3. 실패 시 fallback parser 실행
4. 그래도 실패하면 파일명/크기/오류만 AI에 전달
5. AI 답변에는 처리 성공/부분 성공/실패를 명시

추가 의존성 후보:

- OCR: Tesseract + `pytesseract`
- PDF 이미지 변환: `pymupdf` 또는 `pdf2image`
- 표 추출은 후순위

완료 기준:

- PDF 추출 실패가 AI 명령 전체 실패로 이어지지 않는다.
- 스캔 PDF는 "텍스트 추출 불가"와 OCR 필요 여부를 알려준다.

### Phase 5. AI 작업 큐와 중단 기능

목표: Ollama 응답이 길거나 모델이 느릴 때 Discord UX가 멈춘 것처럼 보이지 않게 한다.

추가 기능:

- `/ai작업상태`
- `/ai중단`
- `/ai큐`
- AI 응답 timeout 안내
- 채널별 동시 작업 제한

설계:

```python
class AiJob:
    id: str
    guild_id: int
    channel_id: int
    user_id: int
    status: queued|running|done|failed|cancelled
    started_at: datetime
    task: asyncio.Task
```

정책:

- 채널당 기본 동시 실행 1개
- 서버 전체 동시 실행 2개
- 새 요청은 큐에 넣거나 "이미 처리 중" 안내
- `/ai중단`은 본인 요청 또는 관리자만 가능

완료 기준:

- 긴 응답 중에도 작업 상태를 볼 수 있다.
- 잘못 보낸 요청을 사용자가 중단할 수 있다.

### Phase 6. 관측성과 운영 진단

목표: 서버 운영자가 봇 상태를 Discord와 콘솔에서 바로 확인할 수 있게 한다.

추가 명령:

- `/ai로그 최근개수`
- `/ai사용량`
- `/ai검색로그`
- `/ai모델상태 상세`
- `/봇진단`

수집 항목:

- 모델별 성공/실패 횟수
- 평균 응답 시간
- timeout 횟수
- 검색 provider별 성공/실패
- 상세검색 fetch 실패 URL
- 첨부 처리 실패 사유
- 긴 답변 파일 첨부 횟수

로그 파일:

- 기존 `ai_usage_log.jsonl` 유지
- 검색 로그 `ai_search_log.jsonl` 추가
- 오류 로그 `puang_error.log` 추가

완료 기준:

- "왜 답변이 느린지", "왜 검색이 안 되는지", "어떤 모델이 실패했는지"를 명령어로 확인할 수 있다.

### Phase 7. 코드 구조 분리

목표: `Puang.py` 단일 파일에 쌓인 기능을 점진적으로 모듈화한다.

권장 구조:

```text
PuangBOT/
  Puang.py
  puangbot/
    __init__.py
    config.py
    embeds.py
    security.py
    ai/
      __init__.py
      models.py
      providers.py
      memory.py
      search.py
      attachments.py
      planner.py
      jobs.py
      responses.py
    music/
      __init__.py
      state.py
      views.py
      playback.py
      tts_mix.py
    server/
      __init__.py
      minecraft.py
      views.py
```

분리 순서:

1. `embeds.py`
2. `ai/search.py`
3. `ai/attachments.py`
4. `ai/memory.py`
5. `ai/providers.py`
6. `music/views.py`
7. `server/minecraft.py`

주의:

- 한 번에 대규모 이동하지 않는다.
- slash command 함수는 초반에는 `Puang.py`에 유지한다.
- 내부 helper만 먼저 분리한다.

완료 기준:

- `Puang.py`가 command wiring 중심으로 줄어든다.
- AI/검색/첨부 처리 함수는 독립 테스트가 가능해진다.

## 5. 설정 스키마 제안

### 5.1 `server_settings.example.json`

```json
{
  "minecraft": {
    "rcon_host": "127.0.0.1",
    "rcon_port": 25575,
    "rcon_password_env": "PUANG_RCON_PASSWORD",
    "mc_root_dir": "../server/mc",
    "playit_dir": "../server",
    "playit_link": "playit.gg.lnk"
  },
  "startup": {
    "auto_setup_ffmpeg": true,
    "auto_setup_edge_tts": false,
    "auto_start_searxng": true
  }
}
```

### 5.2 `ai_tools.json` 확장

```json
{
  "search": {
    "enabled": true,
    "auto_search": false,
    "search_on_uncertain": true,
    "planner_enabled": false,
    "default_provider": "searxng-local",
    "image_provider": "searxng-local",
    "lens_provider": "serpapi-lens",
    "max_results": 5,
    "timeout": 15,
    "fetch_pages": false,
    "fetch_pages_on_uncertain": true,
    "fetch_page_limit": 3,
    "page_max_chars": 2500,
    "context_max_chars": 16000,
    "cache_enabled": true,
    "cache_ttl_seconds": 86400
  },
  "memory": {
    "backend": "sqlite",
    "short_limit": 20,
    "long_summary_enabled": true,
    "summary_interval_messages": 100
  },
  "jobs": {
    "max_concurrent_per_channel": 1,
    "max_concurrent_per_guild": 2,
    "default_timeout_seconds": 300
  }
}
```

## 6. Discord 명령어 변경안

### 유지할 명령어

- `/ai켜기`
- `/ai끄기`
- `/ai상태`
- `/ai패널`
- `/ai검색`
- `/ai검색설정`
- `/ai도구상태`
- `/ai기록설정`
- `/ai기록인덱스`
- `/ai기록검색`
- `/ai모델목록`
- `/ai모델설정`
- `/ai진단`

### 추가할 명령어

- `/ai작업상태`: 현재 채널 AI 작업 상태
- `/ai중단`: 내 AI 요청 중단
- `/ai검색로그`: 최근 검색 provider 결과와 실패 원인
- `/ai기억상태`: 채널 기억 개수/요약 상태
- `/ai기억요약`: 현재 채널 기억 수동 요약
- `/ai기억삭제`: 현재 채널 기억 삭제, 관리자 전용
- `/봇진단`: FFmpeg, Ollama, SearXNG, RCON, 권한 상태 종합 점검

## 7. 운영 작업 체크리스트

서버에서 해야 할 작업:

1. `git pull` 또는 최신 파일 반영
2. `ai_tools.json`을 `ai_tools.example.json`의 새 구조와 맞추기
3. `PUANG_RCON_PASSWORD` 환경변수 등록
4. `server_settings.json` 생성
5. SearXNG 실행 확인
6. Ollama 모델 확인
7. Discord에서 `/ai진단`, `/ai도구상태`, `/봇진단` 실행

권장 테스트:

```text
/ai진단
/ai도구상태
/ai검색 검색어:Ollama SearXNG 연결 방법 종류:웹 provider:auto 상세검색:True
@푸앙봇 검색 오늘 Ollama 최신 소식
@푸앙봇 예전에 마인크래프트 서버 설정 이야기한 거 찾아줘
PDF 첨부 + @푸앙봇 이 문서 요약해줘
이미지 첨부 + @푸앙봇 이 이미지 설명해줘
```

## 8. 회귀 테스트 계획

### 8.1 정적 검증

```powershell
$env:PYTHONPYCACHEPREFIX="C:\tmp\puang_pycache"
python -m py_compile Puang.py
python -m json.tool ai_tools.example.json
python -m json.tool ai_models.example.json
python -m json.tool ai_providers.example.json
```

### 8.2 기능 검증

- Discord slash command sync 성공
- Ollama `/api/tags` 연결 성공
- 선택된 모델이 `/ai진단`에서 "설치됨"으로 표시
- SearXNG `/search?q=ollama&format=json` 응답 성공
- 긴 답변이 파일 첨부로 전송
- PDF 추출 실패 시에도 안내 답변 전송
- 이미지 모델 미지원 시 OCR/메타데이터 fallback
- 음악 재생 중 TTS가 음악을 끊지 않고 ducking
- QueueView 삭제 확인 View 정상 동작

## 9. 권장 구현 순서

1. RCON 비밀번호/서버 설정 분리
2. `ai_tools.json` 스키마 마이그레이션과 상태 경고
3. PDF 예외 처리와 첨부 처리 결과 객체화
4. 자동 검색 판정 개선
5. 검색 Evidence 객체와 출처 표시
6. 검색 캐시
7. AI 작업 큐와 `/ai중단`
8. AI 기억 SQLite 통합
9. Tool Planner
10. 코드 모듈 분리

이 순서는 운영 위험을 먼저 줄이고, 그 다음 검색 품질과 에이전트 기능을 강화하는 방향이다.

## 10. 최종 목표 상태

개선이 끝난 PuangBOT AI 에이전트는 다음 상태를 목표로 한다.

- 서버 비밀값이 코드에 남아 있지 않다.
- 로컬 Ollama와 외부 API를 같은 방식으로 선택하고 fallback한다.
- 검색 답변은 출처와 본문 근거를 표시한다.
- 모르는 내용은 자동으로 검색하되 불필요한 검색은 줄인다.
- 오래된 채널 기록과 최근 대화 기억을 안정적으로 관리한다.
- PDF/이미지/문서 처리 실패가 전체 AI 응답 실패로 이어지지 않는다.
- 긴 작업은 큐와 중단 명령으로 관리된다.
- 운영자는 Discord 명령어로 모델, 검색, 기억, 작업 상태를 진단할 수 있다.
- 코드는 점진적으로 모듈화되어 이후 기능 추가가 쉬워진다.
