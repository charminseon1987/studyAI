# 구현 상세 문서

이 문서는 네이버 뉴스 요약 시스템의 구현 상세 내용을 설명합니다.

## 목차

1. [Import 및 의존성](#import-및-의존성)
2. [핵심 로직 구현](#핵심-로직-구현)
3. [뉴스 수집 로직](#뉴스-수집-로직)
4. [필터링 로직](#필터링-로직)
5. [요약 생성 로직](#요약-생성-로직)
6. [HTML 보고서 생성](#html-보고서-생성)

---

## Import 및 의존성

### 표준 라이브러리

```python
import dotenv
dotenv.load_dotenv()
```
**필요 이유**: 환경 변수 관리
- CrewAI API 키 등 민감한 정보를 `.env` 파일에서 안전하게 로드
- `python-dotenv` 패키지를 통해 환경 변수를 자동으로 로드

```python
import yaml
from pathlib import Path
```
**필요 이유**: 설정 파일 관리
- `yaml`: 에이전트와 태스크 설정을 YAML 형식으로 관리 (`config/agents.yaml`, `config/tasks.yaml`)
- `Path`: 크로스 플랫폼 파일 경로 처리

```python
import re
from datetime import datetime, timedelta
```
**필요 이유**: 날짜 및 문자열 처리
- `re`: 정규식을 사용한 날짜 형식 파싱 및 문자열 패턴 매칭
- `datetime`, `timedelta`: 날짜 비교 및 일주일 이내 필터링

```python
from typing import List, Dict, Optional
```
**필요 이유**: 타입 힌트
- 코드 가독성 향상 및 IDE 자동완성 지원
- 함수 시그니처 명확화

### 외부 라이브러리

```python
import requests
from bs4 import BeautifulSoup
```
**필요 이유**: 웹 스크래핑
- `requests`: HTTP 요청으로 네이버 뉴스 페이지 가져오기
- `BeautifulSoup`: HTML 파싱하여 뉴스 제목, 링크, 본문, 날짜 추출

### CrewAI 프레임워크

```python
from crewai.tools import tool
from crewai import Crew, Agent, Task
from crewai.project import CrewBase, agent, task, crew
```
**필요 이유**: 멀티 에이전트 AI 시스템 구축
- `tool`: 커스텀 도구 데코레이터 (뉴스 수집 도구)
- `Crew`: 여러 에이전트와 태스크를 조율하는 메인 클래스
- `Agent`: AI 에이전트 정의 (뉴스 수집 에이전트, 요약 에이전트)
- `Task`: 각 에이전트가 수행할 작업 정의
- `CrewBase`, `agent`, `task`, `crew`: CrewAI 프로젝트 구조 데코레이터

---

## 핵심 로직 구현

### 1. 뉴스 수집 함수 구조

```python
def _collect_naver_news_impl(category: str, num_articles: int = 5) -> List[Dict]:
    """실제 뉴스 수집 로직 구현"""
    # 구현 내용...
    
@tool("네이버 뉴스 수집 도구")
def collect_naver_news(category: str, num_articles: int = 5) -> List[Dict]:
    """CrewAI Tool 래퍼"""
    return _collect_naver_news_impl(category, num_articles)
```

**구현 이유**:
- `@tool` 데코레이터는 함수를 Tool 객체로 변환하여 CrewAI에서 사용 가능하게 함
- 하지만 Tool 객체는 직접 호출할 수 없으므로, 실제 구현은 `_collect_naver_news_impl`에 분리
- CrewAI 에이전트는 `collect_naver_news`를 사용하고, 직접 호출 시에는 `_collect_naver_news_impl` 사용

### 2. 뉴스 수집 프로세스

#### 단계 1: 페이지 요청 및 파싱

```python
url = f"https://news.naver.com/main/list.naver?mode=LSD&mid=sec&sid1={sid}"
headers = {
    'User-Agent': 'Mozilla/5.0...',
    'Accept': 'text/html...',
    'Accept-Language': 'ko-KR...'
}
response = requests.get(url, headers=headers, timeout=10)
soup = BeautifulSoup(response.content, 'html.parser')
```

**구현 이유**:
- `User-Agent` 헤더: 봇 차단 방지를 위해 일반 브라우저로 위장
- `Accept-Language`: 한국어 콘텐츠 우선 요청
- `timeout=10`: 네트워크 지연 시 무한 대기 방지

#### 단계 2: 뉴스 링크 추출 (다중 선택자 전략)

```python
# 방법 1: ul.type06_headline 또는 ul.type06 안의 dt > a 찾기
for ul in soup.find_all('ul', class_=lambda x: x and ('type06' in x or 'headline' in x)):
    for li in ul.find_all('li'):
        dt = li.find('dt')
        # 링크 추출...

# 방법 2: dt 태그의 a 링크 찾기 (전체 페이지)
for dt in soup.find_all('dt'):
    # 링크 추출...

# 방법 3: li._item의 a 태그 찾기
for li in soup.find_all('li', class_='_item'):
    # 링크 추출...
```

**구현 이유**:
- 네이버 뉴스 페이지 구조가 변경될 수 있으므로 여러 선택자 전략 사용
- 하나의 방법이 실패해도 다른 방법으로 뉴스 링크 확보
- 중복 제거를 위해 `seen_links` 세트 사용

#### 단계 3: 날짜 정보 추출

```python
# 리스트 페이지에서 날짜 추출
date_tag = li.find('span', class_=lambda x: x and ('date' in str(x).lower() or 'time' in str(x).lower()))
if date_tag:
    date = date_tag.get_text(strip=True)

# 기사 페이지에서 날짜 추출 (백업)
if not date:
    date_selectors = [
        ('span', {'class': 't11'}),
        ('span', {'class': '_article_date'}),
        # ... 여러 선택자 시도
    ]
```

**구현 이유**:
- 리스트 페이지에서 날짜를 먼저 추출 (빠름)
- 실패 시 기사 페이지에서 추출 (정확함)
- 여러 선택자를 시도하여 다양한 페이지 구조 대응

#### 단계 4: 본문 추출

```python
selectors = [
    ('div', {'id': 'articleBodyContents'}),
    ('div', {'id': 'newsEndContents'}),
    # ... 우선순위 순으로 선택자 정의
]

for tag, attrs in selectors:
    article_body = article_soup.find(tag, attrs)
    if article_body:
        break

# 불필요한 요소 제거
for element in article_body.find_all(['script', 'style', 'iframe', 'noscript', 'button']):
    element.decompose()
```

**구현 이유**:
- 네이버 뉴스 본문은 다양한 ID/클래스를 사용하므로 우선순위 기반 선택
- 스크립트, 광고 등 불필요한 요소 제거하여 깔끔한 본문 추출
- 본문 길이 제한 (1000자)으로 토큰 사용량 최적화

---

## 필터링 로직

### 1. 동영상 기사 필터링

```python
def is_video_article(title: str, link: str) -> bool:
    """동영상 기사인지 확인하는 함수"""
    video_keywords = ['동영상', '영상', 'video', 'tv', '방송']
    
    # 제목에 동영상 관련 키워드가 있는지 확인
    if any(keyword in title_lower for keyword in video_keywords):
        return True
    
    # 링크에 동영상 관련 키워드가 있는지 확인
    if any(keyword in link_lower for keyword in ['video', 'tv', 'broadcast']):
        return True
    
    return False
```

**구현 이유**:
- 텍스트 기사만 수집하기 위해 동영상 기사 제외
- 제목과 링크 모두 확인하여 정확도 향상
- 대소문자 구분 없이 검사 (`lower()` 사용)

### 2. 일주일 이내 필터링

#### 날짜 파싱 함수

```python
def parse_date(date_str: str) -> Optional[datetime]:
    """날짜 문자열을 datetime 객체로 변환"""
    
    # 상대적 시간 표현 처리 (예: "1시간 전", "2일 전", "방금")
    relative_patterns = [
        (r'(\d+)\s*분\s*전', 'minutes'),
        (r'(\d+)\s*시간\s*전', 'hours'),
        (r'(\d+)\s*일\s*전', 'days'),
        (r'방금', 'now'),
    ]
    
    for pattern, unit in relative_patterns:
        match = re.search(pattern, date_str)
        if match:
            now = datetime.now()
            if unit == 'days':
                days_ago = int(match.group(1))
                return now - timedelta(days=days_ago)
            # ...
    
    # 절대 날짜 형식 처리
    date_formats = [
        '%Y.%m.%d',           # 2024.01.15
        '%Y-%m-%d',           # 2024-01-15
        '%Y년 %m월 %d일',     # 2024년 1월 15일
        # ...
    ]
    
    for fmt in date_formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
```

**구현 이유**:
- 네이버 뉴스는 다양한 날짜 형식 사용 (상대적/절대적)
- 정규식으로 상대적 시간 표현 파싱
- 여러 날짜 형식 시도하여 호환성 확보

#### 일주일 이내 확인 함수

```python
def is_within_week(date_str: str) -> bool:
    """날짜가 최근 일주일 이내인지 확인"""
    parsed_date = parse_date(date_str)
    if parsed_date is None:
        return True  # 날짜를 파싱할 수 없으면 포함 (안전한 선택)
    
    now = datetime.now()
    week_ago = now - timedelta(days=7)
    
    return parsed_date >= week_ago
```

**구현 이유**:
- 최신 뉴스만 수집하기 위해 일주일 이내 필터링
- 날짜 파싱 실패 시 포함 (과도한 필터링 방지)
- `timedelta`로 정확한 날짜 비교

#### 필터링 적용 시점

```python
# 리스트 페이지 단계에서 필터링
filtered_news = []
for news_item in news_links:
    date = news_item.get('date', '')
    if not date or is_within_week(date):
        filtered_news.append(news_item)

# 기사 페이지 단계에서도 재확인
if is_within_week(date):
    news_list.append({...})
```

**구현 이유**:
- 리스트 페이지에서 먼저 필터링하여 불필요한 요청 감소
- 기사 페이지에서 날짜를 다시 확인하여 정확도 향상
- 두 단계 모두에서 필터링하여 안전성 확보

---

## 요약 생성 로직

### 1. 개별 Crew 실행 전략

```python
# 정치 뉴스 요약 생성
politics_collect_task = crew.collect_politics_news_task()
politics_summarize_task = crew.summarize_politics_news_task()

politics_crew = Crew(
    agents=[crew.news_collector_agent(), crew.news_summarizer_agent()],
    tasks=[politics_collect_task, politics_summarize_task],
    verbose=False
)
politics_result = politics_crew.kickoff(inputs={"num_articles": num_articles})
politics_summary = str(politics_result)

# 경제 뉴스 요약 생성 (동일한 방식)
```

**구현 이유**:
- 정치와 경제 요약을 분리하여 중복 방지
- 각 카테고리별로 독립적인 Crew 실행
- `verbose=False`로 불필요한 로그 출력 최소화

### 2. 요약 결과 정리

```python
# "Final Answer:" 이후 부분만 추출
if "Final Answer" in politics_summary:
    final_answer_idx = politics_summary.find("Final Answer")
    if final_answer_idx >= 0:
        politics_summary = politics_summary[final_answer_idx:].split("Final Answer")[-1].strip()
        # 앞뒤 불필요한 문자 제거
        politics_summary = re.sub(r'^[:\-\s]*', '', politics_summary)
        politics_summary = re.sub(r'[:\-\s]*$', '', politics_summary)
```

**구현 이유**:
- CrewAI 결과에는 "Final Answer:" 같은 메타데이터 포함
- 실제 요약 내용만 추출하여 HTML 보고서에 표시
- 정규식으로 불필요한 문자 제거

---

## HTML 보고서 생성

### 1. HTML 이스케이프 처리

```python
def escape_html(text: str) -> str:
    """HTML 특수문자 이스케이프"""
    return (text
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;')
            .replace("'", '&#39;'))
```

**구현 이유**:
- XSS 공격 방지
- HTML 태그가 텍스트로 잘못 해석되는 것 방지
- 모든 사용자 입력에 적용

### 2. HTML 템플릿 생성

```python
def generate_html_report(politics_summary: str, economy_summary: str, 
                         politics_news: List[Dict], economy_news: List[Dict]) -> str:
    """HTML 보고서 생성 (profileReport 스타일)"""
    
    # 정치 뉴스 카드 HTML 생성
    politics_cards = ""
    for i, news in enumerate(politics_news[:5], 1):
        title = escape_html(news.get('title', '제목 없음'))
        content = escape_html(news.get('content', '본문 없음')[:200])
        date = escape_html(news.get('date', '날짜 없음'))
        link = escape_html(news.get('link', '#'))
        
        politics_cards += f"""
        <div class="news-card">
            <div class="news-header">
                <span class="news-number">#{i}</span>
                <span class="news-date">{date}</span>
            </div>
            <h3 class="news-title">{title}</h3>
            <p class="news-content">{content}...</p>
            <a href="{link}" target="_blank" class="news-link">원문 보기 →</a>
        </div>
        """
    # ... 경제 뉴스 카드도 동일하게 생성
    
    # HTML 템플릿에 삽입
    html_template = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <!-- CSS 스타일 정의 -->
    <!-- 헤더, 통계, 섹션 등 구조화된 HTML -->
    """
```

**구현 이유**:
- profileReport 스타일의 전문적인 보고서 디자인
- 반응형 레이아웃으로 모바일/데스크톱 모두 지원
- 각 뉴스를 카드 형태로 표시하여 가독성 향상

### 3. CSS 스타일링

```css
/* 그라데이션 배경 */
body {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

/* 카드 호버 효과 */
.news-card:hover {
    transform: translateY(-5px);
    box-shadow: 0 10px 25px rgba(0, 0, 0, 0.15);
}

/* 반응형 그리드 */
.news-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: 20px;
}
```

**구현 이유**:
- 시각적으로 매력적인 디자인으로 사용자 경험 향상
- 호버 효과로 인터랙티브한 느낌 제공
- 반응형 디자인으로 다양한 화면 크기 지원

### 4. 파일 저장

```python
output_file = f"news_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
with open(output_file, 'w', encoding='utf-8') as f:
    f.write(html_report)
```

**구현 이유**:
- 타임스탬프를 포함한 고유한 파일명 생성
- UTF-8 인코딩으로 한글 정상 표시
- 브라우저에서 바로 열 수 있는 독립적인 HTML 파일

---

## 전체 실행 흐름

```
1. 환경 변수 로드 (.env)
   ↓
2. 정치 뉴스 수집 (5개)
   - 네이버 뉴스 페이지 요청
   - HTML 파싱 및 링크 추출
   - 동영상 기사 필터링
   - 일주일 이내 필터링
   - 본문 수집
   ↓
3. 경제 뉴스 수집 (5개)
   - 동일한 프로세스
   ↓
4. 정치 뉴스 요약 생성
   - CrewAI 에이전트 실행
   - 수집된 뉴스 분석 및 요약
   ↓
5. 경제 뉴스 요약 생성
   - CrewAI 에이전트 실행
   - 수집된 뉴스 분석 및 요약
   ↓
6. HTML 보고서 생성
   - 요약 및 뉴스 데이터를 HTML 템플릿에 삽입
   - CSS 스타일 적용
   - 파일 저장
   ↓
7. 완료
```

---

## 주요 설계 결정

### 1. 함수 분리 전략

- **실제 구현 함수** (`_collect_naver_news_impl`): 직접 호출 가능
- **Tool 래퍼 함수** (`collect_naver_news`): CrewAI에서 사용

**이유**: Tool 객체는 직접 호출 불가능하므로 분리 필요

### 2. 다중 선택자 전략

- 여러 HTML 선택자를 우선순위 순으로 시도
- 하나가 실패해도 다른 방법으로 데이터 확보

**이유**: 웹 페이지 구조 변경에 대응

### 3. 이중 필터링

- 리스트 페이지에서 1차 필터링
- 기사 페이지에서 2차 필터링

**이유**: 정확도와 효율성의 균형

### 4. 개별 Crew 실행

- 정치와 경제를 별도의 Crew로 실행
- 각각 독립적인 요약 생성

**이유**: 요약 중복 방지 및 명확한 분리

---

## 성능 최적화

1. **중복 제거**: `seen_links` 세트 사용
2. **조기 종료**: 필요한 개수만큼 수집되면 즉시 종료
3. **본문 길이 제한**: 1000자로 제한하여 토큰 사용량 최적화
4. **필터링 우선**: 리스트 페이지에서 먼저 필터링하여 불필요한 요청 감소
5. **병렬 처리 가능**: 정치/경제 수집을 병렬로 처리 가능 (향후 개선)

---

## 에러 처리

- 네트워크 오류: `try-except`로 처리하고 빈 리스트 반환
- HTML 파싱 실패: 여러 선택자 시도 후 실패 시 "본문 없음" 표시
- 날짜 파싱 실패: 포함 (안전한 선택)
- 요약 생성 실패: 기본 메시지 표시

---

## 확장 가능성

1. **다른 뉴스 소스 추가**: `collect_daum_news()` 같은 함수 추가
2. **다른 카테고리 추가**: `category_map`에 새 카테고리 추가
3. **PDF 보고서 생성**: HTML 외에 PDF 형식도 지원
4. **이메일 발송**: 생성된 보고서를 자동으로 이메일 발송
5. **스케줄링**: 정기적으로 보고서 생성 및 배포

