# 네이버 뉴스 요약 프로젝트

CrewAI를 활용한 네이버 뉴스 자동 수집 및 요약 시스템입니다. 정치와 경제 분야의 최신 뉴스를 수집하고 AI 에이전트가 요약합니다.

## 프로젝트 개요

이 프로젝트는 CrewAI 프레임워크를 사용하여 두 개의 AI 에이전트가 협업하여 뉴스를 수집하고 요약하는 시스템입니다.

- **뉴스 수집 에이전트**: 네이버 뉴스에서 정치/경제 분야 뉴스를 수집
- **뉴스 요약 에이전트**: 수집된 뉴스를 읽고 핵심 내용을 요약

## 기술 스택

- **Python**: 3.13
- **CrewAI**: 멀티 에이전트 AI 프레임워크
- **BeautifulSoup4**: 웹 스크래핑
- **Requests**: HTTP 요청
- **PyYAML**: 설정 파일 관리

## 프로젝트 구조

```
news-summary/
├── main.py                 # 메인 애플리케이션 코드
├── config/
│   ├── agents.yaml         # 에이전트 설정
│   └── tasks.yaml          # 태스크 설정
├── pyproject.toml          # 프로젝트 의존성
├── uv.lock                 # 의존성 락 파일
└── README.md               # 프로젝트 문서
```

## 설치 및 설정

### 1. 필수 요구사항

- Python 3.13
- uv 패키지 관리자

### 2. 의존성 설치

```bash
# uv를 사용한 의존성 설치
uv sync
```

### 3. 환경 변수 설정

프로젝트 루트에 `.env` 파일을 생성하고 CrewAI API 키를 설정하세요:

```bash
# .env 파일
CREWAI_API_KEY=your_api_key_here
```

또는 `python-dotenv`를 사용하여 환경 변수를 로드합니다.

## 주요 Import 및 의존성

### Python 표준 라이브러리

```python
from pathlib import Path      # 파일 경로 처리
from typing import List, Dict  # 타입 힌트
```

### 외부 라이브러리

```python
import dotenv                  # 환경 변수 관리 (python-dotenv)
import yaml                    # YAML 설정 파일 파싱
import requests                # HTTP 요청 (웹 스크래핑)
from bs4 import BeautifulSoup  # HTML 파싱 (beautifulsoup4)
```

### CrewAI 프레임워크

```python
from crewai.tools import tool              # 커스텀 도구 데코레이터
from crewai import Crew, Agent, Task      # CrewAI 핵심 클래스
from crewai.project import (              # CrewAI 프로젝트 구조
    CrewBase,
    agent,
    task,
    crew
)
```

## 주요 의존성 패키지

`pyproject.toml`에 정의된 주요 패키지:

- **crewai** (>=0.80.0): 멀티 에이전트 AI 프레임워크
- **crewai-tools** (>=0.1.0): CrewAI 도구 라이브러리
- **python-dotenv** (>=1.0.0): 환경 변수 관리
- **requests** (>=2.31.0): HTTP 클라이언트
- **beautifulsoup4** (>=4.12.0): HTML/XML 파서
- **lxml** (>=5.0.0): XML/HTML 처리 엔진
- **firecrawl-py** (>=2.16.3): 웹 크롤링 도구

## 실행 방법

```bash
# 프로젝트 실행
uv run main.py
```

실행 후 `news_report_YYYYMMDD_HHMMSS.html` 파일이 생성됩니다.

### 실행 결과

프로그램 실행 시 다음 단계를 거칩니다:

1. **뉴스 수집**: 정치 뉴스 5개, 경제 뉴스 5개 수집
2. **요약 생성**: 각 카테고리별로 AI 에이전트가 요약 생성
3. **HTML 보고서 생성**: 수집된 뉴스와 요약을 HTML 형식으로 저장

생성된 HTML 파일을 브라우저에서 열어 확인할 수 있습니다.

## 주요 기능

### 1. 뉴스 수집 기능

- 네이버 뉴스에서 정치/경제 분야 뉴스 자동 수집 (각 5개)
- 동영상 기사 자동 필터링
- 최근 일주일 이내 기사만 수집
- 제목, 링크, 본문, 날짜 추출
- 중복 뉴스 제거
- 다양한 HTML 선택자로 안정적인 수집

### 2. 뉴스 요약 기능

- 수집된 뉴스의 핵심 내용 추출
- 3-5줄 간결한 요약 생성
- 카테고리별 독립적인 요약 (정치/경제 분리)
- AI 에이전트를 통한 지능형 요약

### 3. HTML 보고서 생성

- profileReport 스타일의 전문적인 보고서 디자인
- 정치/경제 뉴스를 분리하여 표시
- 각 뉴스 카드에 제목, 날짜, 본문 미리보기, 원문 링크 포함
- 반응형 디자인으로 모바일/데스크톱 지원
- 통계 대시보드 포함

### 4. 커스텀 도구

- `collect_naver_news`: 네이버 뉴스 수집 도구
- 동영상 기사 필터링 기능
- 일주일 이내 필터링 기능
- 다양한 HTML 선택자 지원

## 설정 파일

### agents.yaml

에이전트의 역할, 배경 스토리, 목표를 정의합니다.

```yaml
news_collector_agent:
  role: 네이버 뉴스 수집 전문가
  backstory: 네이버 뉴스에서 뉴스를 수집하는 전문가
  goal: 최신 뉴스를 정확하게 수집

news_summarizer_agent:
  role: 뉴스 요약 전문가
  backstory: 뉴스를 요약하는 전문가
  goal: 뉴스를 간결하게 요약
```

### tasks.yaml

각 태스크의 설명과 예상 출력을 정의합니다.

```yaml
collect_politics_news_task:
  description: 정치 뉴스 수집
  expected_output: 정치 뉴스 리스트
  agent: news_collector_agent
```

## 커스터마이징

### 뉴스 수집 개수 변경

`main.py`의 `num_articles` 변수를 수정하세요:

```python
num_articles = 5  # 수집할 뉴스 개수
```

### 카테고리 추가

`collect_naver_news` 함수의 `category_map`에 새로운 카테고리를 추가하세요:

```python
category_map = {
    '정치': '100',
    '경제': '101',
    '사회': '102',  # 예시
}
```

## 문제 해결

### Import 에러

가상 환경이 활성화되어 있는지 확인하세요:

```bash
source .venv/bin/activate  # Linux/Mac
# 또는
.venv\Scripts\activate     # Windows
```

### 뉴스 수집 실패

네이버 뉴스 페이지 구조가 변경되었을 수 있습니다. `collect_naver_news` 함수의 HTML 선택자를 업데이트해야 할 수 있습니다.

## 라이선스

이 프로젝트는 학습 목적으로 제작되었습니다.

## 문서

- [README.md](README.md) - 프로젝트 개요 및 기본 사용법
- [WORKFLOW.md](WORKFLOW.md) - 시스템 워크플로우 및 데이터 흐름
- [IMPLEMENTATION.md](IMPLEMENTATION.md) - 구현 상세 및 기술 설명

## 참고 자료

- [CrewAI 공식 문서](https://docs.crewai.com/)
- [BeautifulSoup 문서](https://www.crummy.com/software/BeautifulSoup/bs4/doc/)
