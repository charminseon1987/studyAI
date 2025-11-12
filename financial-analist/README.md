# Financial Analyst - 기본 세팅 및 ADK 웹 실행 가이드

## 목차
1. [프로젝트 개요](#프로젝트-개요)
2. [사전 요구사항](#사전-요구사항)
3. [기본 세팅](#기본-세팅)
4. [환경 변수 설정](#환경-변수-설정)
5. [ADK 웹 실행](#adk-웹-실행)
6. [문제 해결](#문제-해결)

---

## 프로젝트 개요

이 프로젝트는 Google ADK(Agent Development Kit)를 사용하여 금융 분석 에이전트를 개발하는 프로젝트입니다.

### 프로젝트 구조
```
financial-analist/
├── financial_advisor/
│   ├── __init__.py
│   └── agent.py          # 에이전트 정의
├── main.py               # 메인 실행 파일
├── tools.py              # 도구 함수 정의
├── pyproject.toml        # 프로젝트 의존성
└── README.md            # 이 파일
```

---

## 사전 요구사항

- Python 3.13 이상
- pip 또는 uv (패키지 관리자)
- Git

---

## 기본 세팅

### 1단계: 프로젝트 클론 및 이동

```bash
# 프로젝트 디렉토리로 이동
cd financial-analist
```

### 2단계: 가상환경 생성 및 활성화

#### macOS/Linux:
```bash
# 가상환경 생성
python3 -m venv .venv

# 가상환경 활성화
source .venv/bin/activate
```

#### Windows:
```bash
# 가상환경 생성
python -m venv .venv

# 가상환경 활성화
.venv\Scripts\activate
```

### 3단계: 의존성 설치

#### pip 사용 시:
```bash
pip install -e .
```

#### uv 사용 시:
```bash
# uv가 설치되어 있다면
uv pip install -e .
```

### 4단계: 설치 확인

```bash
# ADK가 제대로 설치되었는지 확인
python -c "import google.adk; print('ADK 설치 완료!')"
```

---

## 환경 변수 설정

프로젝트에서 사용하는 API 키를 설정해야 합니다.

### 1단계: .env 파일 생성

프로젝트 루트 디렉토리에 `.env` 파일을 생성합니다:

```bash
touch .env
```

### 2단계: 환경 변수 추가

`.env` 파일에 다음 내용을 추가합니다:

```env
# Firecrawl API 키 (웹 검색 도구용)
FIRECRAWL_API_KEY=your_firecrawl_api_key_here

# OpenAI API 키 (LiteLLM 사용 시)
OPENAI_API_KEY=your_openai_api_key_here
```

**주의**: `.env` 파일은 Git에 커밋되지 않도록 `.gitignore`에 포함되어 있습니다.

---

## ADK 웹 실행

### 1단계: 에이전트 확인

`financial_advisor/agent.py` 파일에서 `root_agent`가 올바르게 정의되어 있는지 확인합니다:

```python
from google.adk.agent import Agent
from google.adk.models.lite_llm import LiteLLM

MODEL = LiteLLM("openai/gpt-4o")

weather_agent = Agent(
    name="WeatherAgent",
    instruction="you help the user with weather related questions",
    model=MODEL,
)
root_agent = weather_agent
```

### 2단계: ADK 웹 서버 실행

터미널에서 다음 명령어를 실행합니다:

```bash
adk web
```

또는 Python 모듈로 직접 실행:

```bash
python -m google.adk.web
```

### 3단계: 웹 인터페이스 접속

명령어 실행 후 터미널에 표시되는 URL로 접속합니다. 일반적으로:

```
http://localhost:8000
```

또는

```
http://127.0.0.1:8000
```

브라우저에서 해당 주소로 접속하면 ADK 웹 인터페이스를 사용할 수 있습니다.

### 4단계: 에이전트 테스트

웹 인터페이스에서:
1. 에이전트와 대화를 시작합니다
2. 에이전트가 올바르게 응답하는지 확인합니다
3. 도구(tools)가 정상적으로 작동하는지 테스트합니다

---

## 문제 해결

### 문제 1: `adk: command not found`

**해결 방법:**
```bash
# 가상환경이 활성화되어 있는지 확인
which python

# ADK가 설치되어 있는지 확인
pip list | grep google-adk

# 재설치
pip install --upgrade google-adk
```

### 문제 2: 포트가 이미 사용 중입니다

**해결 방법:**
```bash
# 다른 포트로 실행
adk web --port 8001

# 또는 기존 프로세스 종료
lsof -ti:8000 | xargs kill -9
```

### 문제 3: API 키 오류

**해결 방법:**
1. `.env` 파일이 프로젝트 루트에 있는지 확인
2. 환경 변수 이름이 정확한지 확인
3. API 키가 유효한지 확인
4. 가상환경을 재활성화

### 문제 4: 모듈을 찾을 수 없습니다

**해결 방법:**
```bash
# 의존성 재설치
pip install -e .

# Python 경로 확인
python -c "import sys; print('\n'.join(sys.path))"
```

---

## 추가 정보

### 개발 모드 실행

파일 변경 시 자동으로 재로드되도록 하려면:

```bash
# 개발 의존성 설치
pip install -e ".[dev]"

# 웹 서버 실행 (자동 리로드)
adk web --reload
```

### 프로젝트 의존성

주요 의존성:
- `google-adk`: Google Agent Development Kit
- `google-genai`: Google Generative AI
- `litellm`: LiteLLM 모델 통합
- `firecrawl-py`: 웹 크롤링 도구
- `yfinance`: 금융 데이터 수집
- `python-dotenv`: 환경 변수 관리

---

## 다음 단계

1. `financial_advisor/agent.py`에서 에이전트 커스터마이징
2. `tools.py`에 새로운 도구 추가
3. 에이전트에 도구 연결
4. 웹 인터페이스에서 테스트

---

## 참고 자료

- [Google ADK 공식 문서](https://github.com/google/adk)
- [LiteLLM 문서](https://docs.litellm.ai/)
- [Firecrawl 문서](https://docs.firecrawl.dev/)

