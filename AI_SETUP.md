# PuangBOT 로컬 AI 준비 절차

이 문서는 Ollama와 모델을 설치한 뒤 PuangBOT의 Discord AI 기능을 바로 켜기 위한 운영 절차다.

## 현재 코드 상태

- AI 기본 주소: `http://127.0.0.1:11434`
- 기본 텍스트 모델: `qwen2.5:1.5b`
- 텍스트 백업 모델: `qwen2.5:0.5b`
- 기본 백업 정책: `safe_degrade`
- 이미지 직접 분석은 `capabilities`에 `image`가 있는 모델에서만 사용한다.
- 이미지 직접 분석 실패 시 OCR/이미지 메타데이터 기반 텍스트 대체 분석으로 내려간다.
- 채널별 설정 파일: `ai_settings.json`
- 모델 프로필 파일: `ai_models.json`
- 단기 기억 파일: `ai_short_memory.json`
- 장기 기억 파일: `ai_long_memory.json`

위 JSON 파일들은 런타임 설정/기억 파일이라 `.gitignore`에 포함되어 있다.

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
```

## 4. 모델 프로필 커스터마이징

기본 내장 프로필만으로도 동작한다. 직접 바꾸려면 `ai_models.example.json`을 `ai_models.json`으로 복사한 뒤 수정한다.

프로필 형식:

```json
{
  "profiles": {
    "model-name": {
      "label": "표시 이름",
      "api": "ollama",
      "base_url": "http://127.0.0.1:11434",
      "capabilities": ["text", "image"],
      "context": 4096,
      "timeout": 120,
      "note": "운영 메모"
    }
  }
}
```

`api`는 `ollama` 또는 `openai`를 쓸 수 있다. Ollama는 `/api/chat`, OpenAI 호환 서버는 `/v1/chat/completions`로 호출한다.

## 5. Discord에서 켜는 순서

봇을 재시작한 뒤 아래 순서로 확인한다.

```text
/ai모델목록
/ai켜기 채널:#ai 모드:멘션할 때만 답변 모델:qwen2.5:1.5b 주소:http://127.0.0.1:11434 텍스트백업모델:qwen2.5:0.5b 비전백업모델:moondream 백업정책:안전 백업
/ai진단 채널:#ai
/ai상태 채널:#ai
```

상시 대화 채널로 운영할 때만 `/ai켜기`의 모드를 `상시 대화`로 설정한다. 일반 채널 전체를 상시 대화로 켜면 모든 메시지가 단기/장기 기억에 들어가고 답변 요청도 늘어난다.

## 6. 진단

로컬에서 전체 준비 상태를 확인한다.

```powershell
powershell -ExecutionPolicy Bypass -File .\diagnose_puang.ps1
```

점검 항목:

- Python 버전
- `Puang.py` 문법
- 필수 Python 패키지
- Ollama CLI 설치 여부
- Ollama API 응답 여부
- 로컬 운영 파일 존재 여부

## 7. 이미지와 문서 처리

- 이미지: 모델이 `image` 기능을 지원하면 Discord 첨부 이미지를 다운로드해 base64로 직접 전달한다.
- 이미지 fallback: 직접 분석 실패 시 Pillow 이미지 정보와 가능하면 Tesseract OCR 결과를 텍스트로 넘긴다.
- TXT/MD/JSON/CSV/log 등: 텍스트로 추출해 프롬프트에 포함한다.
- PDF: `pypdf` 또는 `PyPDF2`로 앞쪽 최대 8페이지를 추출한다.
- DOCX: 내부 `word/document.xml`에서 텍스트를 추출한다.

OCR까지 제대로 쓰려면 Python 패키지 `pytesseract` 외에 Windows용 Tesseract 프로그램도 별도로 설치해야 한다.
