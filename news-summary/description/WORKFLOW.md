# 네이버 뉴스 요약 시스템 워크플로우

이 문서는 네이버 뉴스 요약 시스템의 전체 워크플로우와 코드 구조를 설명합니다.

## 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│                    NewsSummaryCrew                          │
│                  (CrewAI 기반 시스템)                        │
└─────────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┴───────────────────┐
        │                                       │
┌───────▼────────┐                    ┌───────▼────────┐
│  News Collector │                    │ News Summarizer│
│     Agent      │                    │     Agent      │
└───────┬────────┘                    └───────┬────────┘
        │                                       │
        │ collect_naver_news                    │
        │ (커스텀 도구)                         │
        │                                       │
┌───────▼────────┐                    ┌───────▼────────┐
│  Task 1:       │                    │  Task 3:       │
│  정치 뉴스 수집│                    │  정치 뉴스 요약│
│                │                    │                │
│  Task 2:       │                    │  Task 4:       │
│  경제 뉴스 수집│                    │  경제 뉴스 요약│
└────────────────┘                    └────────────────┘
```

## 워크플로우 단계

### 1단계: 초기화 및 설정 로드

```python
# main.py 시작 부분
import dotenv
dotenv.load_dotenv()  # 환경 변수 로드

# NewsSummaryCrew 클래스 초기화
class NewsSummaryCrew:
    def __init__(self):
        # YAML 설정 파일 로드
        config_path = Path(__file__).parent / "config"
        agents_config = yaml.safe_load(agents.yaml)
        tasks_config = yaml.safe_load(tasks.yaml)
```

**설정 파일 구조:**

- `config/agents.yaml`: 에이전트 역할 및 목표 정의
- `config/tasks.yaml`: 태스크 설명 및 예상 출력 정의

### 2단계: 에이전트 생성

#### 2.1 뉴스 수집 에이전트 (News Collector Agent)

```python
@agent
def news_collector_agent(self):
    return Agent(
        **self.agents_config["news_collector_agent"],
        tools=[collect_naver_news],  # 커스텀 도구 연결
        verbose=True
    )
```

**역할:**

- 네이버 뉴스에서 정치/경제 분야 뉴스 수집
- `collect_naver_news` 도구 사용
- 뉴스 제목, 링크, 본문 추출

#### 2.2 뉴스 요약 에이전트 (News Summarizer Agent)

```python
@agent
def news_summarizer_agent(self):
    return Agent(
        **self.agents_config["news_summarizer_agent"],
        verbose=True
    )
```

**역할:**

- 수집된 뉴스 읽기 및 분석
- 핵심 내용 추출
- 3-5줄 요약 생성

### 3단계: 태스크 정의

#### 3.1 정치 뉴스 수집 태스크

```python
@task
def collect_politics_news_task(self):
    return Task(
        description="정치 뉴스 수집",
        expected_output="정치 뉴스 리스트",
        agent=self.news_collector_agent()
    )
```

**실행 흐름:**

1. 에이전트가 `collect_naver_news("정치", num_articles)` 호출
2. 네이버 뉴스 정치 페이지 스크래핑
3. 뉴스 링크 추출 및 본문 수집
4. 구조화된 데이터 반환

#### 3.2 경제 뉴스 수집 태스크

```python
@task
def collect_economy_news_task(self):
    return Task(
        description="경제 뉴스 수집",
        expected_output="경제 뉴스 리스트",
        agent=self.news_collector_agent()
    )
```

#### 3.3 정치 뉴스 요약 태스크

```python
@task
def summarize_politics_news_task(self):
    return Task(
        description="정치 뉴스 요약",
        expected_output="정치 뉴스 요약 리스트",
        agent=self.news_summarizer_agent(),
        context=[self.collect_politics_news_task()]  # 이전 태스크 결과 사용
    )
```

**의존성:**

- `collect_politics_news_task` 완료 후 실행
- 수집된 정치 뉴스를 컨텍스트로 받아 요약

#### 3.4 경제 뉴스 요약 태스크

```python
@task
def summarize_economy_news_task(self):
    return Task(
        description="경제 뉴스 요약",
        expected_output="경제 뉴스 요약 리스트",
        agent=self.news_summarizer_agent(),
        context=[self.collect_economy_news_task()]
    )
```

### 4단계: 커스텀 도구 - 뉴스 수집

#### 4.1 동영상 기사 필터링 함수

```python
def is_video_article(title: str, link: str) -> bool:
    """동영상 기사인지 확인"""
    video_keywords = ['동영상', '영상', 'video', 'tv', '방송']
    # 제목 또는 링크에 동영상 키워드가 있으면 True 반환
```

**필터링 기준:**

- 제목에 동영상 관련 키워드 포함 여부
- 링크에 동영상 관련 키워드 포함 여부

#### 4.2 네이버 뉴스 수집 도구

```python
@tool("네이버 뉴스 수집 도구")
def collect_naver_news(category: str, num_articles: int = 5):
    """
    네이버 뉴스 수집 프로세스:

    1. 카테고리 매핑 (정치: 100, 경제: 101)
    2. 네이버 뉴스 리스트 페이지 요청
    3. HTML 파싱 및 뉴스 링크 추출
       - 방법 1: ul.type06 내 dt > a 태그
       - 방법 2: 전체 페이지 dt 태그
       - 방법 3: li._item 내 a 태그
    4. 동영상 기사 필터링
    5. 각 뉴스 본문 수집
    6. 구조화된 데이터 반환
    """
```

**뉴스 링크 추출 프로세스:**

```
네이버 뉴스 페이지
    │
    ├─→ HTML 파싱 (BeautifulSoup)
    │
    ├─→ 선택자 1: ul.type06 > dt > a
    │   └─→ 제목, 링크 추출
    │
    ├─→ 선택자 2: dt > a (전체)
    │   └─→ 제목, 링크 추출
    │
    └─→ 선택자 3: li._item > a
        └─→ 제목, 링크 추출
            │
            ├─→ 동영상 기사 필터링
            │   └─→ is_video_article() 체크
            │
            └─→ 중복 제거
                └─→ 최종 뉴스 리스트
```

**본문 추출 프로세스:**

```
뉴스 기사 페이지
    │
    ├─→ HTTP 요청 (requests)
    │
    ├─→ HTML 파싱
    │
    ├─→ 본문 선택자 시도 (우선순위 순)
    │   ├─→ div#articleBodyContents
    │   ├─→ div#newsEndContents
    │   ├─→ div#articeBody
    │   ├─→ article#dic_area
    │   └─→ 기타 선택자들
    │
    ├─→ 불필요한 요소 제거
    │   ├─→ script, style, iframe
    │   ├─→ 광고, 추천 기사
    │   └─→ 버튼 등
    │
    └─→ 텍스트 추출 및 정리
        └─→ 최대 1000자로 제한
```

### 5단계: Crew 조립 및 실행

```python
@crew
def assemble_crew(self):
    return Crew(
        agents=[
            self.news_collector_agent(),
            self.news_summarizer_agent()
        ],
        tasks=[
            self.collect_politics_news_task(),
            self.collect_economy_news_task(),
            self.summarize_politics_news_task(),
            self.summarize_economy_news_task()
        ],
        verbose=True
    )
```

**실행 순서:**

```
1. collect_politics_news_task 실행
   └─→ News Collector Agent가 정치 뉴스 수집
       └─→ 결과 저장

2. collect_economy_news_task 실행
   └─→ News Collector Agent가 경제 뉴스 수집
       └─→ 결과 저장

3. summarize_politics_news_task 실행
   └─→ News Summarizer Agent가 정치 뉴스 요약
       └─→ 이전 태스크 결과(정치 뉴스) 사용

4. summarize_economy_news_task 실행
   └─→ News Summarizer Agent가 경제 뉴스 요약
       └─→ 이전 태스크 결과(경제 뉴스) 사용
```

### 6단계: 메인 실행

```python
if __name__ == "__main__":
    num_articles = 5  # 수집할 뉴스 개수

    # 1. 직접 뉴스 수집 (태스크 실행 전에 데이터 확보)
    politics_news = _collect_naver_news_impl("정치", num_articles)
    economy_news = _collect_naver_news_impl("경제", num_articles)

    # 2. 각 카테고리별로 별도의 Crew 실행하여 요약 생성
    crew = NewsSummaryCrew()

    # 정치 뉴스 요약
    politics_crew = Crew(
        agents=[crew.news_collector_agent(), crew.news_summarizer_agent()],
        tasks=[crew.collect_politics_news_task(), crew.summarize_politics_news_task()],
        verbose=False
    )
    politics_result = politics_crew.kickoff(inputs={"num_articles": num_articles})
    politics_summary = str(politics_result)

    # 경제 뉴스 요약
    economy_crew = Crew(
        agents=[crew.news_collector_agent(), crew.news_summarizer_agent()],
        tasks=[crew.collect_economy_news_task(), crew.summarize_economy_news_task()],
        verbose=False
    )
    economy_result = economy_crew.kickoff(inputs={"num_articles": num_articles})
    economy_summary = str(economy_result)

    # 3. HTML 보고서 생성
    html_report = generate_html_report(
        politics_summary=politics_summary,
        economy_summary=economy_summary,
        politics_news=politics_news[:5],
        economy_news=economy_news[:5]
    )

    # 4. 파일 저장
    output_file = f"news_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_report)
```

## 데이터 흐름

```
사용자 입력 (num_articles = 5)
    │
    ├─→ 직접 뉴스 수집 (병렬 가능)
    │   │
    │   ├─→ 정치 뉴스 수집
    │   │   └─→ _collect_naver_news_impl("정치", 5)
    │   │       ├─→ 네이버 뉴스 페이지 요청
    │   │       ├─→ HTML 파싱
    │   │       ├─→ 뉴스 링크 추출 (다중 선택자)
    │   │       ├─→ 동영상 필터링
    │   │       ├─→ 일주일 이내 필터링
    │   │       ├─→ 본문 수집
    │   │       └─→ [뉴스1~5] 반환
    │   │
    │   └─→ 경제 뉴스 수집
    │       └─→ _collect_naver_news_impl("경제", 5)
    │           └─→ [뉴스1~5] 반환
    │
    ├─→ 정치 뉴스 요약 생성 (별도 Crew)
    │   │
    │   └─→ Politics Crew.kickoff()
    │       ├─→ Task 1: 정치 뉴스 수집
    │       └─→ Task 2: 정치 뉴스 요약
    │           └─→ News Summarizer Agent
    │               └─→ 요약 텍스트 반환
    │
    ├─→ 경제 뉴스 요약 생성 (별도 Crew)
    │   │
    │   └─→ Economy Crew.kickoff()
    │       ├─→ Task 1: 경제 뉴스 수집
    │       └─→ Task 2: 경제 뉴스 요약
    │           └─→ News Summarizer Agent
    │               └─→ 요약 텍스트 반환
    │
    └─→ HTML 보고서 생성
        ├─→ 정치 요약 + 정치 뉴스 5개
        ├─→ 경제 요약 + 경제 뉴스 5개
        ├─→ HTML 템플릿에 삽입
        └─→ 파일 저장 (news_report_YYYYMMDD_HHMMSS.html)
            │
            ▼
        브라우저에서 확인 가능한 HTML 파일
```

## 에러 처리

### 뉴스 수집 실패 시

```python
try:
    # 뉴스 수집 로직
except Exception as e:
    return [{'error': f'뉴스 수집 중 오류 발생: {str(e)}'}]
```

### 본문 추출 실패 시

```python
try:
    # 본문 추출 로직
except Exception as e:
    content = f"본문을 가져오는 중 오류 발생: {str(e)}"
```

## 성능 최적화

1. **중복 제거**: `seen_links` 세트를 사용하여 중복 뉴스 제거
2. **조기 종료**: 필요한 개수만큼 수집되면 즉시 종료
3. **선택자 우선순위**: 가장 정확한 선택자부터 시도
4. **본문 길이 제한**: 1000자로 제한하여 토큰 사용량 최적화

## 확장 가능성

### 새로운 카테고리 추가

1. `category_map`에 새 카테고리 추가
2. `tasks.yaml`에 새 태스크 추가
3. `NewsSummaryCrew` 클래스에 새 태스크 메서드 추가
4. HTML 보고서 생성 함수에 새 섹션 추가

### 새로운 도구 추가

1. `@tool` 데코레이터로 새 함수 정의
2. 해당 에이전트의 `tools` 리스트에 추가

### 다른 뉴스 소스 추가

1. 새로운 수집 함수 생성 (예: `collect_daum_news`)
2. 에이전트에 도구로 추가
3. 태스크에서 사용

### 보고서 형식 확장

1. PDF 보고서 생성 기능 추가
2. 이메일 자동 발송 기능
3. 대시보드 웹 애플리케이션 구축
4. 데이터베이스 저장 기능

## 디버깅 팁

1. **verbose=True**: 각 에이전트와 태스크의 실행 과정 확인
2. **중간 결과 확인**: 각 태스크의 반환값을 로그로 출력
3. **HTML 구조 확인**: 네이버 뉴스 페이지 구조 변경 시 선택자 업데이트 필요
