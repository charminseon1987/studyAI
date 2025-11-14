# news_nomade.py 참고 문서

## 📋 목차
1. [프로젝트 개요](#프로젝트-개요)
2. [파일 구조](#파일-구조)
3. [주요 개념 설명](#주요-개념-설명)
4. [코드 구조](#코드-구조)
5. [사용 방법](#사용-방법)

---

## 프로젝트 개요

`news_nomade.py`는 CrewAI를 사용하여 번역 작업을 수행하는 간단한 예제입니다. 영어 문장을 한국어와 그리스어로 번역하는 두 가지 태스크를 실행합니다.

### 주요 특징
- CrewAI의 `@CrewBase` 데코레이터 없이 직접 구현
- YAML 파일을 통한 설정 관리
- 여러 번역 태스크를 동시에 실행

---

## 파일 구조

```
news-summary/
├── news_nomade.py              # 메인 번역 크루 파일
├── config/
│   ├── translate_agents.yaml   # 번역 에이전트 설정
│   └── translate_tasks.yaml   # 번역 태스크 설정
└── news_nomade참고.md          # 이 문서
```

### Config 파일 설명

#### `config/translate_agents.yaml`
번역 에이전트의 역할, 목표, 배경 스토리를 정의합니다.

```yaml
translator_agent:
  role: translator to translate from English to Korean
  goal: To be a good and useful translator to avoid misunderstandings.
  backstory: You grew up between New York and South Korea...
```

#### `config/translate_tasks.yaml`
번역 태스크의 설명과 예상 출력을 정의합니다.

```yaml
translate_task:
  description: translate {sentence} from English to Korean
  expected_output: A well formatted translation...
  agent: translator_agent  # CrewAI 자동 매핑용 (코드에서 제거됨)

retranslate_task:
  description: translate {sentence} from English to Greek
  expected_output: A well formatted translation...
  agent: translator_agent
```

---

## 주요 개념 설명

### 1. `.copy()`를 사용하는 이유

#### 문제 상황
Python의 딕셔너리는 **mutable(변경 가능)** 객체입니다. `.copy()` 없이 직접 참조하면 원본 데이터가 변경됩니다.

#### 예시

```python
# ❌ 잘못된 방법
task_config = self.tasks_config["translate_task"]  # 원본 참조
task_config.pop("agent", None)  # 원본에서 "agent" 키가 제거됨!

# 다음 호출 시 문제 발생
# self.tasks_config["translate_task"]에 "agent" 키가 없어짐
```

```python
# ✅ 올바른 방법
task_config = self.tasks_config["translate_task"].copy()  # 복사본 생성
task_config.pop("agent", None)  # 복사본에서만 "agent" 제거

# 원본 self.tasks_config["translate_task"]는 그대로 유지됨
# 여러 번 호출해도 안전함
```

#### 이유
- **원본 데이터 보호**: `self.tasks_config`의 원본을 변경하지 않음
- **재사용성**: 같은 메서드를 여러 번 호출해도 안전
- **데이터 무결성**: Config 파일에서 읽은 원본 데이터 유지

---

### 2. `.pop("agent", None)`을 제거하는 이유

#### 문제 상황
YAML 파일에는 `agent: translator_agent` (문자열)가 있지만, 코드에서는 이미 `agent=self.translator_agent()` (Agent 객체)로 명시적으로 전달합니다.

#### 예시

```python
# YAML 파일 내용
translate_task:
  agent: translator_agent  # 문자열 값
  description: ...
  expected_output: ...

# 코드에서 Task 생성
return Task(
    **task_config,              # agent: "translator_agent" (문자열) 포함됨
    agent=self.translator_agent(),  # agent: Agent 객체 전달
    # ❌ TypeError: Task() got multiple values for argument 'agent'
)
```

```python
# ✅ 올바른 방법
task_config = self.tasks_config["translate_task"].copy()
task_config.pop("agent", None)  # YAML의 agent 필드 제거
# task_config = {"description": "...", "expected_output": "..."}

return Task(
    **task_config,              # description, expected_output만 언패킹
    agent=self.translator_agent(),  # Agent 객체로 명시적 전달
    verbose=True
)
```

#### 이유
- **파라미터 충돌 방지**: 같은 인자에 두 개의 값이 전달되는 것을 방지
- **명시적 제어**: Agent 객체를 코드에서 직접 제어
- **YAML의 agent 필드**: CrewAI 자동 매핑용이지만, 직접 구현에서는 불필요

---

## 코드 구조

### 1. Tool 정의

```python
@tool("번역 도구")
def translate_text(text: str) -> str:
    """영어 텍스트를 한국어로 번역합니다."""
    return f"[번역됨] {text}"
```

- CrewAI의 `@tool` 데코레이터로 도구 정의
- 에이전트가 사용할 수 있는 함수

### 2. TranslatorCrew 클래스

#### 초기화 (`__init__`)
```python
def __init__(self):
    config_path = Path(__file__).parent / "config"
    with open(config_path / "translate_agents.yaml") as f:
        self.agents_config = yaml.safe_load(f)
    with open(config_path / "translate_tasks.yaml") as f:
        self.tasks_config = yaml.safe_load(f)
```

- YAML 파일에서 설정 로드
- `agents_config`와 `tasks_config`에 저장

#### 에이전트 생성 (`translator_agent`)
```python
def translator_agent(self):
    return Agent(
        **self.agents_config["translator_agent"],
        verbose=True
    )
```

- YAML 설정을 언패킹하여 Agent 생성
- `verbose=True`: 디버깅 정보 출력

#### 태스크 생성 (`translate_task`, `retranslate_task`)
```python
def translate_task(self):
    task_config = self.tasks_config["translate_task"].copy()  # 복사본 생성
    task_config.pop("agent", None)  # agent 필드 제거
    return Task(
        **task_config,              # YAML의 나머지 필드 언패킹
        agent=self.translator_agent(),  # Agent 객체 명시적 전달
        verbose=True
    )
```

**핵심 포인트:**
1. `.copy()`: 원본 데이터 보호
2. `.pop("agent", None)`: 파라미터 충돌 방지
3. `**task_config`: 딕셔너리 언패킹
4. `agent=self.translator_agent()`: Agent 객체 명시적 전달

#### 크루 조합 (`assemble_crew`)
```python
def assemble_crew(self):
    return Crew(
        agents=[self.translator_agent()],
        tasks=[self.translate_task(), self.retranslate_task()],
        verbose=True
    )
```

- Agent와 Task를 조합하여 Crew 생성
- 여러 태스크를 동시에 실행 가능

---

## 사용 방법

### 기본 실행

```python
if __name__ == "__main__":
    crew_instance = TranslatorCrew()
    result = crew_instance.assemble_crew().kickoff(
        inputs={"sentence": "I'm S, I like to ride my bycicle in Napoli"}
    )
    print(result)
```

### 실행 흐름

1. **TranslatorCrew 인스턴스 생성**
   - Config 파일 로드
   - Agent와 Task 설정 준비

2. **Crew 조합**
   - `assemble_crew()` 호출
   - Agent와 Task를 조합한 Crew 반환

3. **워크플로우 실행**
   - `kickoff()` 메서드로 실행
   - `inputs` 파라미터로 입력 데이터 전달
   - 두 태스크(한국어, 그리스어 번역) 순차 실행

4. **결과 출력**
   - 번역 결과 반환 및 출력

---

## 주요 차이점: @CrewBase 사용 vs 직접 구현

### @CrewBase 사용 시 (main.py 방식)
```python
@CrewBase
class NewsSummaryCrew:
    @agent
    def news_collector_agent(self):
        ...
    
    @task
    def collect_politics_news_task(self):
        ...
```

**장점:**
- 자동 매핑 기능
- 코드가 간결함

**단점:**
- 모든 task를 자동으로 매핑하려고 시도
- Config 파일의 모든 task가 있어야 함
- 유연성 제한

### 직접 구현 시 (news_nomade.py 방식)
```python
class TranslatorCrew:
    def translator_agent(self):
        ...
    
    def translate_task(self):
        ...
```

**장점:**
- 완전한 제어 가능
- 필요한 task만 선택적으로 사용
- Config 파일 충돌 없음

**단점:**
- 더 많은 코드 작성 필요
- 수동으로 관리해야 함

---

## 주의사항

1. **Config 파일 경로**: `Path(__file__).parent / "config"`로 상대 경로 사용
2. **YAML 파일 형식**: 들여쓰기와 문법 정확히 지켜야 함
3. **Agent 객체**: 매번 새로 생성되므로 캐싱 고려 가능
4. **에러 처리**: 파일 읽기, YAML 파싱 등에 대한 예외 처리 추가 권장

---

## 확장 가능성

### 새로운 태스크 추가
1. `config/translate_tasks.yaml`에 새 태스크 추가
2. `TranslatorCrew` 클래스에 해당 메서드 추가
3. `assemble_crew()`의 `tasks` 리스트에 추가

### 새로운 에이전트 추가
1. `config/translate_agents.yaml`에 새 에이전트 추가
2. `TranslatorCrew` 클래스에 해당 메서드 추가
3. `assemble_crew()`의 `agents` 리스트에 추가

---

## 참고 자료

- [CrewAI 공식 문서](https://docs.crewai.com/)
- [Python 딕셔너리 copy() 메서드](https://docs.python.org/3/library/copy.html)
- [YAML 파일 형식](https://yaml.org/)

