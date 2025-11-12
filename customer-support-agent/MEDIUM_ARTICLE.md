# 🎙️ 주니어 개발자도 20분만에 이해하는 음성 기반 AI 에이전트 시스템

> Streamlit + OpenAI로 만드는 음성 고객 지원 챗봇의 핵심 원리

안녕하세요! 오늘은 **음성 입력을 받아서 AI 에이전트가 음성으로 응답하는** 고객 지원 시스템을 만들어봤습니다. 복잡해 보이지만, 실제로는 3단계 파이프라인으로 구성되어 있어요. 핵심만 간단히 설명해드릴게요!

---

## 🎯 전체 시스템 구조 (한눈에 보기)

```
┌─────────────────────────────────────────────────────────────┐
│                    사용자 음성 입력                          │
│              "결제가 안 돼요" (마이크로 녹음)                  │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  [STT 단계] Speech-to-Text                                  │
│  OpenAI Whisper API                                         │
│  음성 파일 → 텍스트 변환                                     │
│  "결제가 안 돼요"                                           │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  [CustomWorkflow] 에이전트 실행                              │
│  ┌──────────────────────────────────────────────┐          │
│  │  triage_agent (라우터)                        │          │
│  │  "결제 문제네요" → billing_agent로 전환        │          │
│  └──────────────────┬───────────────────────────┘          │
│                     │                                        │
│  ┌──────────────────▼───────────────────────────┐          │
│  │  billing_agent (전문 에이전트)                │          │
│  │  - lookup_billing_history() 도구 호출        │          │
│  │  - "결제 이력을 확인했습니다..." 응답 생성     │          │
│  └──────────────────┬───────────────────────────┘          │
└──────────────────────┼──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  [TTS 단계] Text-to-Speech                                  │
│  OpenAI TTS API                                             │
│  텍스트 → 음성 파일 변환                                     │
│  "결제 이력을 확인했습니다..." → 오디오 스트림               │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              사용자가 음성 응답을 듣게 됨                      │
│              (스피커로 재생)                                  │
└─────────────────────────────────────────────────────────────┘
```

이게 전부입니다! 이제 각 단계를 코드로 살펴볼게요.

---

## 📦 1단계: 음성 입력 받기 (main.py)

Streamlit의 `audio_input` 위젯으로 사용자의 음성을 받습니다.

### 기본 코드 구조

```python
# =============================================================================
# Import 문 설명
# =============================================================================

# Streamlit: 웹 기반 UI 프레임워크
# - st.audio_input(): 음성 입력 위젯 제공
# - st.chat_message(): 채팅 UI 메시지 표시
# - st.session_state: 세션 상태 관리
import streamlit as st

# NumPy: 수치 연산 라이브러리
# - 오디오 데이터를 배열로 처리하기 위해 사용
# - np.frombuffer(): 바이트 데이터를 numpy 배열로 변환
import numpy as np

# wave: WAV 파일 읽기/쓰기 모듈
# - 오디오 파일의 프레임 데이터를 읽기 위해 사용
# io: 바이트 스트림 처리 모듈
# - BytesIO: 메모리 내 바이트 데이터를 파일처럼 다룸
import wave, io

# sounddevice: 오디오 입출력 라이브러리
# - sd.OutputStream(): 스피커로 오디오 출력
# - 실시간 음성 스트리밍 재생에 사용
import sounddevice as sd

# agents.voice: Agents 프레임워크의 음성 처리 모듈
# - AudioInput: 음성 입력을 처리하는 클래스
# - VoicePipeline: 음성 파이프라인 (STT → Workflow → TTS)
from agents.voice import AudioInput, VoicePipeline

# workflow: 프로젝트 내 커스텀 워크플로우 모듈
# - CustomWorkflow: 에이전트 실행 로직을 담당하는 클래스
from workflow import CustomWorkflow

# models: 프로젝트 내 데이터 모델 모듈
# - UserAccountContext: 사용자 계정 정보를 담는 Pydantic 모델
from models import UserAccountContext

# asyncio: 비동기 프로그래밍 모듈
# - asyncio.run(): 비동기 함수를 동기적으로 실행
import asyncio

# 사용자 컨텍스트 설정
user_account_ctx = UserAccountContext(
    customer_id=1,
    name="hyeseon",
    tier="basic",
    email="nico@gmail.com"
)

# 음성 입력 위젯
audio_input = st.audio_input("Record your message")

if audio_input:
    # 사용자 메시지 표시
    with st.chat_message("human"):
        st.audio(audio_input)

    # 에이전트 실행
    asyncio.run(run_agent(audio_input))
```

### 오디오 변환 함수

```python
def convert_audio(audio_input):
    """
    Streamlit 오디오 입력을 numpy 배열로 변환
    """
    # 바이트 데이터 추출
    audio_data = audio_input.getvalue()

    # WAV 파일 읽기
    with wave.open(io.BytesIO(audio_data), "rb") as wav_file:
        audio_frames = wav_file.readframes(-1)

    # numpy 배열로 변환 (16비트 정수형)
    return np.frombuffer(audio_frames, dtype=np.int16)
```

### 메인 에이전트 실행 함수

```python
# 추가로 필요한 Import들
from agents import (
    InputGuardrailTripwireTriggered,  # 입력 가드레일 위반 예외
    OutputGuardrailTripwireTriggered,  # 출력 가드레일 위반 예외
)

async def run_agent(audio_input):
    with st.chat_message("ai"):
        status_container = st.status("⏳ Processing voice message...")

        try:
            # 1. 오디오 변환
            audio_array = convert_audio(audio_input)
            audio = AudioInput(buffer=audio_array)

            # 2. 워크플로우 및 파이프라인 생성
            workflow = CustomWorkflow(context=user_account_ctx)
            pipeline = VoicePipeline(workflow=workflow)

            status_container.update(label="Running workflow", state="running")

            # 3. 파이프라인 실행
            result = await pipeline.run(audio)

            # 4. 오디오 출력 설정 (24kHz, 모노)
            player = sd.OutputStream(
                samplerate=24000,
                channels=1,
                dtype=np.int16,
            )
            player.start()

            # 5. 음성 응답 스트리밍 및 재생
            async for event in result.stream():
                if event.type == "voice_stream_event_audio":
                    player.write(event.data)

        except InputGuardrailTripwireTriggered:
            st.write("I can't help you with that.")
        except OutputGuardrailTripwireTriggered:
            st.write("Can't show you that answer.")
```

**핵심 포인트:**

- `VoicePipeline`: 음성 처리의 전체 흐름을 관리하는 클래스
- `CustomWorkflow`: 에이전트 실행 로직을 담당하는 우리만의 클래스
- `sounddevice`: 실시간 오디오 스트리밍 재생

---

## 🔄 2단계: CustomWorkflow - 에이전트 실행 (workflow.py)

이게 가장 중요한 부분입니다! `VoicePipeline`이 음성을 텍스트로 변환한 후, 이 워크플로우가 호출됩니다.

```python
# =============================================================================
# Import 문 설명
# =============================================================================

# agents.voice: Agents 프레임워크의 음성 워크플로우 모듈
# - VoiceWorkflowBase: 음성 워크플로우의 기본 클래스
#                      이 클래스를 상속받아 커스텀 워크플로우 구현
# - VoiceWorkflowHelper: 음성 워크플로우 유틸리티 함수들
#                        stream_text_from(): 에이전트 응답을 텍스트 청크로 변환
from agents.voice import VoiceWorkflowBase, VoiceWorkflowHelper

# agents: Agents 프레임워크의 핵심 모듈
# - Runner: 에이전트를 실행하는 클래스
#           run_streamed(): 스트리밍 방식으로 에이전트 실행
from agents import Runner

# streamlit: 세션 상태에 접근하기 위해 필요
# - st.session_state: 현재 활성화된 에이전트를 저장하고 추적
import streamlit as st

class CustomWorkflow(VoiceWorkflowBase):
    def __init__(self, context):
        self.context = context  # 사용자 정보

    async def run(self, transcription):
        """
        transcription: 음성이 텍스트로 변환된 결과
        예: "안녕하세요, 주문 상태를 확인하고 싶습니다"
        """
        # 1. 에이전트 실행 (스트리밍 모드)
        result = Runner.run_streamed(
            agent=triage_agent,  # 초기 에이전트
            input=transcription,
            session=session,
            context=self.context
        )

        # 2. 텍스트 응답을 청크 단위로 스트리밍
        async for chunk in VoiceWorkflowHelper.stream_text_from(result):
            yield chunk  # VoicePipeline에 전달

        # 3. 에이전트 전환 추적
        st.session_state["agent"] = result.last_agent
```

**왜 스트리밍을 사용하나요?**

- 전체 응답을 기다리지 않고 즉시 시작할 수 있어요
- 사용자가 더 빠르게 응답을 받을 수 있습니다

---

## 🤖 3단계: 에이전트 구조 이해하기

에이전트는 **트리아지 에이전트**로 시작해서, 필요에 따라 전문 에이전트로 전환됩니다.

### 트리아지 에이전트 (라우터 역할)

```python
# =============================================================================
# Import 문 설명
# =============================================================================

# streamlit: 사이드바에 에이전트 전환 로그 표시
import streamlit as st

# agents: Agents 프레임워크의 핵심 모듈
# - Agent: 에이전트를 정의하는 클래스
# - input_guardrail: 입력 가드레일 데코레이터
#                     부적절한 입력을 필터링하는 함수에 사용
# - Runner: 에이전트 실행 클래스
# - GuardrailFunctionOutput: 가드레일 함수의 출력 타입
# - handoff: 에이전트 간 전환을 정의하는 함수
from agents import Agent, input_guardrail, Runner, GuardrailFunctionOutput, handoff

# agents.lifecycle: 에이전트 생명주기 관련 모듈
# - RunContextWrapper: 실행 컨텍스트 래퍼 (사용자 컨텍스트 포함)
from agents.lifecycle import RunContextWrapper

# models: 프로젝트 내 데이터 모델 모듈
# - UserAccountContext: 사용자 계정 정보 모델
# - InputGuardRailOutput: 입력 가드레일 검사 결과 모델
# - handoffData: 에이전트 전환 정보 모델 (HandoffContext의 별칭)
from models import UserAccountContext, InputGuardRailOutput, handoffData

# 프로젝트 내 전문 에이전트들
# - 각 전문 에이전트는 특정 도메인을 담당
from my_agents.account_agent import account_agent
from my_agents.technical_agent import technical_agent
from my_agents.billing_agent import billing_agent
from my_agents.order_agent import order_agent

# 동적 프롬프트 생성 함수
def dynamic_triage_agent_instructions(wrapper, agent):
    return f"""
    {RECOMMENDED_PROMPT_PREFIX}

    당신은 고객 지원 에이전트입니다.
    고객 이름: {wrapper.context.name}
    고객 이메일: {wrapper.context.email}
    고객 등급: {wrapper.context.tier}

    주요 업무: 고객의 이슈를 분류하고 적절한 전문가에게 연결하세요.

    이슈 분류 가이드:

    🔧 기술 지원 - 다음으로 전환:
    - 제품 오작동, 에러, 버그
    - 앱 크래시, 로딩 문제, 성능 문제
    - "앱이 안 열려요", "에러 메시지가 나와요"

    💰 결제 지원 - 다음으로 전환:
    - 결제 문제, 실패한 결제, 환불
    - 구독 질문, 요금제 변경, 취소
    - "결제가 안 돼요", "구독 취소하고 싶어요"

    📦 주문 관리 - 다음으로 전환:
    - 주문 상태, 배송, 배달 질문
    - 반품, 교환, 누락된 아이템
    - "주문 어디갔어요?", "반품하고 싶어요"

    👤 계정 관리 - 다음으로 전환:
    - 로그인 문제, 비밀번호 재설정
    - 프로필 업데이트, 이메일 변경
    - "로그인이 안 돼요", "비밀번호 바꾸고 싶어요"
    """

# Handoff 핸들러
def handle_handoff(wrapper, input_data: handoffData):
    with st.sidebar:
        st.write(f"""
        🔄 전환: {input_data.to_agent_name}
        이유: {input_data.reason}
        이슈 유형: {input_data.issue_type}
        설명: {input_data.issue_description}
        """)

def make_handoff(agent):
    return handoff(
        agent=agent,
        on_handoff=handle_handoff,
        input_type=handoffData,
    )

# 트리아지 에이전트 생성
triage_agent = Agent(
    name="Triage Agent",
    instructions=dynamic_triage_agent_instructions,
    input_guardrails=[off_topic_guardrail],
    handoffs=[
        make_handoff(billing_agent),
        make_handoff(technical_agent),
        make_handoff(order_agent),
        make_handoff(account_agent),
    ]
)
```

**핵심 개념:**

- **Input Guardrail**: 부적절한 입력을 필터링 (예: "오늘 날씨 어때요?")
- **Handoff**: 다른 에이전트로 전환하는 메커니즘
- **동적 프롬프트**: 사용자 정보를 포함한 맞춤형 지시사항

### Input Guardrail 구현

```python
# =============================================================================
# Import 문 설명 (위의 트리아지 에이전트 섹션과 동일)
# =============================================================================
# from agents import Agent, input_guardrail, Runner, GuardrailFunctionOutput
# from agents.lifecycle import RunContextWrapper
# from models import UserAccountContext, InputGuardRailOutput

# Guardrail 에이전트 정의
# 이 에이전트는 사용자 입력이 적절한지 검사하는 역할을 합니다
Input_guardrail_agent = Agent(
    name="Input Guardrail Agent",
    instructions="""
    사용자의 요청이 다음 중 하나와 관련이 있는지 확인하세요:
    - 사용자 계정 정보
    - 결제 문의
    - 주문 정보
    - 기술 지원 이슈

    관련 없는 요청인 경우, is_off_topic을 True로 설정하세요.
    초기 대화에서는 친절하게 응답하되, 명백히 관련 없는 요청만 필터링하세요.
    """,
    output_type=InputGuardRailOutput,
)

# Guardrail 함수
@input_guardrail
async def off_topic_guardrail(
    wrapper: RunContextWrapper[UserAccountContext],
    agent: Agent[UserAccountContext],
    input: str,
):
    # Guardrail 에이전트 실행
    result = await Runner.run(
        Input_guardrail_agent,
        input,
        context=wrapper.context,
    )

    # 결과 반환
    return GuardrailFunctionOutput(
        output_info=result.final_output,
        tripwire_triggered=result.final_output.is_off_topic
    )
```

만약 `tripwire_triggered=True`가 되면, 에이전트는 "I can't help you with that." 같은 메시지를 반환합니다.

### 전문 에이전트 예시: Billing Agent

```python
# =============================================================================
# Import 문 설명
# =============================================================================

# agents: Agents 프레임워크의 핵심 모듈
# - Agent: 에이전트를 정의하는 클래스
# - RunContextWrapper: 실행 컨텍스트 래퍼
#                      에이전트 함수에서 사용자 컨텍스트에 접근할 때 사용
from agents import Agent, RunContextWrapper

# agents.lifecycle: 에이전트 생명주기 관련 모듈
# - AgentHooks: 에이전트의 생명주기 이벤트를 처리하는 훅 클래스
from agents.lifecycle import AgentHooks

# tools: 프로젝트 내 도구(Tools) 모듈
# - @function_tool 데코레이터로 정의된 함수들
# - 에이전트가 실제 작업을 수행하기 위해 호출하는 함수들
# - lookup_billing_history: 결제 이력 조회
# - process_refund_request: 환불 요청 처리
# - update_payment_method: 결제 수단 업데이트
# - apply_billing_credit: 계정 크레딧 적용
from tools import (
    lookup_billing_history,
    process_refund_request,
    update_payment_method,
    apply_billing_credit,
    AgentToolUsageLoggingHooks  # 도구 사용 로깅 훅
)

# models: 프로젝트 내 데이터 모델 모듈
# - UserAccountContext: 사용자 계정 정보 모델
from models import UserAccountContext

def dynamic_billing_agent_instructions(wrapper, agent):
    return f"""
    당신은 결제 지원 전문가입니다. {wrapper.context.name}님을 도와드립니다.
    고객 등급: {wrapper.context.tier}
    {"(프리미엄 결제 지원)" if wrapper.context.tier != "basic" else ""}

    역할: 결제, 구독, 환불 문제를 해결합니다.

    결제 지원 프로세스:
    1. 계정 정보 및 결제 정보 확인
    2. 특정 결제 문제 식별
    3. 결제 이력 및 구독 상태 확인
    4. 명확한 해결책 및 다음 단계 제시
    5. 필요시 환불/조정 처리

    일반적인 결제 문제:
    - 실패한 결제 또는 거부된 카드
    - 예상치 못한 요금 또는 청구 분쟁
    - 구독 변경 또는 취소
    - 환불 요청
    - 청구서 질문
    """

billing_agent = Agent(
    name="Billing Support Agent",
    instructions=dynamic_billing_agent_instructions,
    tools=[
        lookup_billing_history,
        process_refund_request,
        update_payment_method,
        apply_billing_credit,
    ],
    hooks=AgentToolUsageLoggingHooks(),
)
```

---

## 🎨 실제 동작 흐름 예시

### 시나리오 1: 사용자가 "결제가 안 돼요"라고 말함

```
┌─────────────────────────────────────────────────────────┐
│ 1. [STT] 음성 → 텍스트 변환                              │
│    입력: 마이크 녹음 오디오                              │
│    출력: "결제가 안 돼요"                                │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│ 2. [CustomWorkflow] triage_agent 실행                   │
│    - Input Guardrail 검사 통과                          │
│    - 이슈 분류: "결제 문제"                               │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│ 3. [Handoff] billing_agent로 전환                       │
│    이유: "결제 전문 에이전트가 필요함"                    │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│ 4. [billing_agent] 도구 호출                            │
│    lookup_billing_history(months_back=6)                 │
│    → 결제 이력 데이터 반환                                │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│ 5. [billing_agent] 응답 생성                            │
│    "결제 이력을 확인했습니다. 최근 6개월간..."            │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│ 6. [TTS] 텍스트 → 음성 변환                              │
│    실시간 스트리밍으로 오디오 청크 생성                   │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│ 7. 사용자가 음성 응답을 듣게 됨                          │
│    sounddevice를 통해 스피커로 재생                      │
└─────────────────────────────────────────────────────────┘
```

### 시나리오 2: 부적절한 요청 (Guardrail 작동)

```
사용자: "오늘 날씨 어때요?"
    ↓
[Input Guardrail 검사]
    ↓
[off_topic_guardrail 실행]
    ↓
[Input_guardrail_agent 판단]
    - is_off_topic: True
    - reason: "요청이 고객 지원 범위를 벗어남"
    ↓
[tripwire_triggered = True]
    ↓
에이전트 응답: "I can't help you with that."
```

### 시나리오 3: 기술 지원 요청

```
사용자: "앱이 계속 크래시돼요"
    ↓
[triage_agent] → technical_agent로 handoff
    ↓
[technical_agent] run_diagnostic_check() 도구 호출
    ↓
[technical_agent] provide_troubleshooting_steps() 도구 호출
    ↓
응답: "진단 결과를 확인했습니다. 다음 단계를 시도해보세요..."
```

---

## 💡 핵심 포인트 정리

### 1. VoicePipeline의 역할

- **STT**: 음성 → 텍스트 (OpenAI Whisper)
- **Workflow**: 텍스트 → 에이전트 실행 → 텍스트 응답
- **TTS**: 텍스트 → 음성 (OpenAI TTS)

### 2. CustomWorkflow의 역할

- `VoiceWorkflowBase`를 상속받아 구현
- 에이전트 실행 및 텍스트 스트리밍 담당
- 에이전트 전환 상태 관리

### 3. 에이전트 구조

- **트리아지 에이전트**: 초기 라우팅
- **전문 에이전트들**: billing, technical, order, account
- **Handoff**: 에이전트 간 전환 메커니즘
- **Guardrail**: 부적절한 입력/출력 필터링

---

## 🚀 코드 실행하기

```bash
# 1. 환경 변수 설정 (.env 파일)
OPENAI_API_KEY=your_api_key_here

# 2. 의존성 설치
pip install streamlit agents openai sounddevice numpy

# 3. 실행
streamlit run main.py
```

---

## 📚 배운 점

1. **비동기 처리의 중요성**: `async/await`를 사용하여 실시간 스트리밍 구현
2. **에이전트 아키텍처**: 트리아지 → 전문 에이전트 구조로 확장성 확보
3. **Guardrail 패턴**: 입력/출력 검증으로 안전한 AI 시스템 구축
4. **상태 관리**: Streamlit의 `session_state`로 에이전트 전환 추적

---

## 🛠️ 도구(Tools) 추가하기

에이전트가 실제 작업을 수행하려면 도구가 필요합니다. `@function_tool` 데코레이터를 사용하면 쉽게 추가할 수 있어요.

### 도구 정의 예시

```python
# =============================================================================
# Import 문 설명
# =============================================================================

# streamlit: 사이드바에 도구 사용 로그 표시
import streamlit as st

# agents: Agents 프레임워크의 핵심 모듈
# - function_tool: 함수를 에이전트 도구로 변환하는 데코레이터
#                  이 데코레이터를 사용하면 함수가 에이전트가 호출할 수 있는 도구가 됨
# - AgentHooks: 에이전트 생명주기 훅
# - Agent: 에이전트 클래스
# - Tool: 도구 타입
# - RunContextWrapper: 실행 컨텍스트 래퍼
from agents import function_tool, AgentHooks, Agent, Tool, RunContextWrapper

# models: 프로젝트 내 데이터 모델 모듈
# - UserAccountContext: 사용자 계정 정보 모델
#                       모든 도구 함수의 첫 번째 매개변수로 전달됨
from models import UserAccountContext

# random: 랜덤 값 생성 (예시 데이터 생성용)
import random

# datetime: 날짜/시간 처리
# - datetime: 현재 날짜/시간
# - timedelta: 날짜/시간 차이 계산
from datetime import datetime, timedelta

@function_tool
def lookup_billing_history(
    context: UserAccountContext,
    months_back: int = 6
) -> str:
    """
    고객의 결제 이력을 조회합니다.

    Args:
        context: 사용자 계정 컨텍스트
        months_back: 조회할 개월 수 (기본값: 6개월)

    Returns:
        결제 이력 문자열
    """
    # 실제로는 데이터베이스에서 조회
    payments = [
        "• 2024년 1월: $29.99 - Paid",
        "• 2024년 2월: $29.99 - Paid",
        "• 2024년 3월: $29.99 - Failed"
    ]

    return f"💳 결제 이력 (최근 {months_back}개월):\n" + "\n".join(payments)

@function_tool
def run_diagnostic_check(
    context: UserAccountContext,
    product_name: str,
    issue_description: str
) -> str:
    """
    제품 진단을 실행합니다.
    """
    diagnostics = [
        "✅ 서버 연결: 정상",
        "✅ API 엔드포인트: 응답 중",
        "⚠️ 캐시 메모리: 85% 사용 중",
    ]

    return f"🔍 {product_name} 진단 결과:\n" + "\n".join(diagnostics)
```

### 에이전트에 도구 연결

```python
billing_agent = Agent(
    name="Billing Support Agent",
    instructions="결제 및 구독 관련 문제를 해결합니다.",
    tools=[
        lookup_billing_history,
        process_refund_request,
        update_payment_method,
    ],
    hooks=AgentToolUsageLoggingHooks(),
)
```

---

## 📸 실제 실행 결과 (스크린샷 설명)

### 1. 초기 화면

```
┌─────────────────────────────────────────────┐
│  🎙️ Record your message                     │
│  [마이크 버튼]                               │
│                                             │
│  ────────────────────────────────────────   │
│  Sidebar:                                   │
│  [Reset memory] 버튼                        │
│  대화 기록: (비어있음)                       │
└─────────────────────────────────────────────┘
```

### 2. 음성 입력 후 처리 중

```
┌─────────────────────────────────────────────┐
│  👤 사용자:                                  │
│  [오디오 플레이어] 🎵                        │
│                                             │
│  🤖 AI:                                      │
│  ⏳ Processing voice message...             │
│  → Running workflow                         │
└─────────────────────────────────────────────┘
```

### 3. 에이전트 전환 시 사이드바

```
┌─────────────────────────────────────────────┐
│  Sidebar:                                   │
│  🚀 Triage Agent activated                 │
│  🔄 Handoff: Triage Agent → Billing Agent  │
│  🔧 Billing Agent used tool:               │
│     lookup_billing_history                  │
│  💳 결제 이력 (최근 6개월):                 │
│     • 2024년 1월: $29.99 - Paid            │
└─────────────────────────────────────────────┘
```

### 4. 응답 완료

```
┌─────────────────────────────────────────────┐
│  👤 사용자:                                  │
│  "결제가 안 돼요"                            │
│                                             │
│  🤖 AI:                                      │
│  ✅ Complete                                │
│  [음성 응답 재생 중...] 🔊                  │
│                                             │
│  응답 내용:                                 │
│  "결제 이력을 확인했습니다. 최근 결제 실패가 │
│   보입니다. 결제 수단을 업데이트해드릴까요?" │
└─────────────────────────────────────────────┘
```

---

## 🐛 트러블슈팅 (Troubleshooting)

### 문제 1: "ModuleNotFoundError: No module named 'agents'"

**원인**: `agents` 패키지가 설치되지 않음

**해결책**:

```bash
pip install agents
# 또는
pip install -r requirements.txt
```

### 문제 2: "OPENAI_API_KEY not found"

**원인**: 환경 변수가 설정되지 않음

**해결책**:

```bash
# .env 파일 생성
echo "OPENAI_API_KEY=your_api_key_here" > .env

# 또는 직접 설정
export OPENAI_API_KEY=your_api_key_here
```

### 문제 3: "sounddevice 오디오 출력 오류"

**원인**: 오디오 장치 접근 권한 문제 또는 샘플레이트 불일치

**해결책**:

```python
# macOS의 경우
# 시스템 설정 > 보안 및 개인 정보 보호 > 마이크/스피커 권한 확인

# 샘플레이트 확인
import sounddevice as sd
print(sd.query_devices())  # 사용 가능한 장치 확인

# 샘플레이트 조정
player = sd.OutputStream(
    samplerate=22050,  # 24000 대신 22050 시도
    channels=1,
    dtype=np.int16,
)
```

### 문제 4: "비동기 함수 실행 오류"

**원인**: Streamlit에서 비동기 함수를 잘못 호출

**해결책**:

```python
# ❌ 잘못된 방법
await run_agent(audio_input)

# ✅ 올바른 방법
asyncio.run(run_agent(audio_input))
```

### 문제 5: "Guardrail이 항상 트리거됨"

**원인**: Input Guardrail 에이전트의 프롬프트가 너무 엄격함

**해결책**:

```python
Input_guardrail_agent = Agent(
    name="Input Guardrail Agent",
    instructions="""
    사용자의 요청이 고객 지원 범위 내인지 확인하세요.
    초기 대화에서는 친절하게 응답하되,
    명백히 관련 없는 요청만 필터링하세요.
    """,
    output_type=InputGuardRailOutput,
)
```

### 문제 6: "에이전트가 handoff하지 않음"

**원인**: triage_agent의 instructions가 명확하지 않음

**해결책**:

```python
def dynamic_triage_agent_instructions(wrapper, agent):
    return f"""
    사용자의 요청을 다음 4가지로 분류하세요:

    1. 결제/구독 문제 → billing_agent로 전환
    2. 기술 지원 문제 → technical_agent로 전환
    3. 주문/배송 문제 → order_agent로 전환
    4. 계정/보안 문제 → account_agent로 전환

    명확하게 분류할 수 없으면 질문을 통해 확인하세요.
    """
```

### 문제 7: "세션 상태가 유지되지 않음"

**원인**: Streamlit의 session_state 초기화 문제

**해결책**:

```python
# main.py 상단에 명시적으로 초기화
if "session" not in st.session_state:
    st.session_state["session"] = SQLiteSession(
        "chat-history",
        "customer-support-memory.db",
    )

if "agent" not in st.session_state:
    st.session_state["agent"] = triage_agent
```

### 문제 8: "오디오 입력이 인식되지 않음"

**원인**: 브라우저 마이크 권한 또는 오디오 포맷 문제

**해결책**:

```python
# 브라우저 콘솔에서 확인
# Chrome: 개발자 도구 > Console에서 오류 확인

# 오디오 포맷 확인
def convert_audio(audio_input):
    audio_data = audio_input.getvalue()
    print(f"Audio size: {len(audio_data)} bytes")  # 디버깅

    with wave.open(io.BytesIO(audio_data), "rb") as wav_file:
        print(f"Sample rate: {wav_file.getframerate()}")  # 디버깅
        print(f"Channels: {wav_file.getnchannels()}")  # 디버깅
        audio_frames = wav_file.readframes(-1)

    return np.frombuffer(audio_frames, dtype=np.int16)
```

---

## 🎓 다음 단계

- [x] 에이전트에 도구(Tools) 추가하기
- [x] 출력 가드레일 구현하기
- [ ] 세션 관리 개선하기 (Redis 등 사용)
- [ ] 에러 핸들링 강화하기
- [ ] 다국어 지원 추가하기
- [ ] 대화 기록 분석 기능 추가하기

---

## 📚 추가 학습 자료

### 추천 읽을 자료

1. **Agents 프레임워크 공식 문서**

   - Guardrail 패턴 이해
   - Handoff 메커니즘 심화 학습

2. **OpenAI API 문서**

   - Whisper API (STT)
   - TTS API
   - 최적의 프롬프트 작성법

3. **Streamlit 문서**
   - 세션 상태 관리
   - 비동기 처리

### 실전 팁

- **프롬프트 엔지니어링**: 에이전트 instructions를 명확하게 작성
- **도구 설계**: 각 도구는 단일 책임 원칙을 따르기
- **에러 처리**: 모든 예외 상황을 고려한 방어적 프로그래밍
- **로깅**: 사이드바에 에이전트 동작 로그 표시로 디버깅 용이

---

**마무리**

음성 기반 AI 에이전트 시스템은 복잡해 보이지만, 실제로는 **STT → 에이전트 → TTS**라는 단순한 3단계 구조입니다. 핵심은 `CustomWorkflow`에서 에이전트를 실행하고 스트리밍하는 부분이에요!

이제 여러분도 음성 기반 고객 지원 챗봇을 만들 수 있습니다! 🚀

궁금한 점이 있으시면 댓글로 남겨주세요!

---

_이 글은 실제 프로젝트 코드를 기반으로 작성되었습니다. 전체 코드는 [GitHub 링크]에서 확인하실 수 있어요._
