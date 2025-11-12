"""
=============================================================================
음성 기반 고객 지원 에이전트 메인 애플리케이션
=============================================================================

이 파일은 Streamlit을 사용하여 음성 입력을 받고, 음성 파이프라인을 통해
고객 지원 에이전트와 상호작용하는 메인 애플리케이션입니다.

주요 기능:
1. 음성 입력 수신 및 변환
2. 음성 파이프라인 실행
3. 에이전트 응답을 음성으로 출력
4. 세션 관리 및 메모리 관리

=============================================================================
전체 파이프라인 흐름 (Pipeline Flow)
=============================================================================

[사용자 음성 입력]
        ↓
[Streamlit audio_input 위젯]
        ↓
[convert_audio() 함수]
    - WAV 파일 → numpy 배열 변환
        ↓
[AudioInput 객체 생성]
        ↓
[VoicePipeline 실행]
    ├─ 1단계: STT (Speech-to-Text)
    │   - 음성 → 텍스트 변환
    │   - OpenAI Whisper API 사용
    │
    ├─ 2단계: CustomWorkflow.run()
    │   ├─ Runner.run_streamed() 실행
    │   │   ├─ triage_agent (초기)
    │   │   │   ├─ Input Guardrail 검사
    │   │   │   ├─ 이슈 분류
    │   │   │   └─ 필요시 handoff (에이전트 전환)
    │   │   │       ├─ billing_agent (결제 관련)
    │   │   │       ├─ technical_agent (기술 지원)
    │   │   │       ├─ order_agent (주문 관리)
    │   │   │       └─ account_agent (계정 관리)
    │   │   │
    │   │   └─ 에이전트가 도구(tools) 호출
    │   │       - lookup_billing_history()
    │   │       - process_refund_request()
    │   │       - run_diagnostic_check()
    │   │       - 등등...
    │   │
    │   └─ 텍스트 응답 스트리밍
    │       - VoiceWorkflowHelper.stream_text_from()
    │       - 청크 단위로 yield
    │
    └─ 3단계: TTS (Text-to-Speech)
        - 텍스트 → 음성 변환
        - OpenAI TTS API 사용
        - 실시간 스트리밍
        ↓
[오디오 출력]
    - sounddevice를 통해 스피커로 재생
    - 사용자가 음성 응답을 듣게 됨

=============================================================================
주요 컴포넌트 설명
=============================================================================

1. VoicePipeline
   - 음성 입력을 받아서 전체 파이프라인을 관리
   - STT → Workflow → TTS 순서로 처리
   - 비동기로 실행되어 실시간 스트리밍 지원

2. CustomWorkflow
   - VoiceWorkflowBase를 상속
   - 텍스트 입력을 받아서 에이전트 실행
   - 텍스트 응답을 스트리밍으로 반환

3. triage_agent
   - 초기 라우팅 에이전트
   - 사용자 요청을 분석하여 적절한 전문 에이전트로 전환
   - Input Guardrail로 부적절한 요청 필터링

4. 전문 에이전트들
   - billing_agent: 결제 및 구독 관련
   - technical_agent: 기술 지원 및 문제 해결
   - order_agent: 주문 및 배송 관리
   - account_agent: 계정 및 보안 관리

5. 세션 관리
   - SQLiteSession: 대화 기록을 데이터베이스에 저장
   - 세션 상태를 통해 에이전트 전환 추적
   - 컨텍스트 유지로 연속적인 대화 지원

=============================================================================
비동기 처리 (Async Processing)
=============================================================================

이 애플리케이션은 비동기 처리를 사용합니다:

- async def run_agent(): 비동기 함수로 정의
- await pipeline.run(): 파이프라인 비동기 실행
- async for event in result.stream(): 스트림 이벤트 비동기 처리
- asyncio.run(): Streamlit에서 비동기 함수 호출

비동기 처리를 사용하는 이유:
1. 음성 스트리밍: 실시간으로 오디오 청크를 받아서 재생
2. 응답성 향상: 전체 응답을 기다리지 않고 즉시 시작
3. 리소스 효율: I/O 대기 시간 동안 다른 작업 처리 가능

=============================================================================
"""

# =============================================================================
# 환경 변수 및 기본 라이브러리 Import
# =============================================================================

import dotenv
dotenv.load_dotenv()  # .env 파일에서 환경 변수 로드 (API 키 등)

# OpenAI 클라이언트: 음성 인식 및 생성에 사용
from openai import OpenAI

# asyncio: 비동기 함수 실행을 위한 라이브러리
# 음성 파이프라인은 비동기로 실행되므로 필요
import asyncio

# Streamlit: 웹 기반 UI 프레임워크
# 음성 입력 위젯과 채팅 인터페이스를 제공
import streamlit as st

# =============================================================================
# Agents 프레임워크 Import
# =============================================================================

from agents import (
    Runner,  # 에이전트 실행을 담당하는 클래스
    SQLiteSession,  # SQLite 데이터베이스를 사용한 세션 관리
    InputGuardrailTripwireTriggered,  # 입력 가드레일 위반 예외
    OutputGuardrailTripwireTriggered,  # 출력 가드레일 위반 예외
)

# 음성 처리 관련 클래스들
from agents.voice import (
    AudioInput,  # 음성 입력을 처리하는 클래스
    VoicePipeline,  # 음성 파이프라인: 음성 입력 → 텍스트 → 에이전트 → 음성 출력
)

# =============================================================================
# 프로젝트 내부 모듈 Import
# =============================================================================

from models import UserAccountContext  # 사용자 계정 컨텍스트 모델
from my_agents.triage_agent import triage_agent  # 트리아지 에이전트 (초기 라우팅)
from workflow import CustomWorkflow  # 커스텀 워크플로우 (에이전트 실행 로직)

# =============================================================================
# 오디오 처리 라이브러리 Import
# =============================================================================

import numpy as np  # 수치 연산 (오디오 데이터 배열 처리)
import wave  # WAV 파일 읽기/쓰기
import io  # 바이트 스트림 처리
import sounddevice as sd  # 오디오 출력 (스피커로 재생)

# =============================================================================
# 초기화
# =============================================================================

# OpenAI 클라이언트 인스턴스 생성
# 환경 변수에서 OPENAI_API_KEY를 자동으로 읽어옴
client = OpenAI()

# 사용자 계정 컨텍스트 생성
# 실제 애플리케이션에서는 로그인한 사용자 정보를 사용
user_account_ctx = UserAccountContext(
    customer_id=1,  # 고객 ID
    name="hyeseon",  # 고객 이름
    tier="basic",  # 등급 (basic, premium, enterprise)
    email="nico@gmail.com"  # 이메일 주소
)


# =============================================================================
# Streamlit 세션 상태 관리
# =============================================================================

# Streamlit은 페이지 새로고침 시 코드가 다시 실행되므로,
# session_state를 사용하여 상태를 유지합니다.

# 세션 관리자 초기화
# SQLiteSession: 대화 기록을 SQLite 데이터베이스에 저장
if "session" not in st.session_state:
    st.session_state["session"] = SQLiteSession(
        "chat-history",  # 세션 이름
        "customer-support-memory.db",  # 데이터베이스 파일 경로
    )
session = st.session_state["session"]

# 현재 활성화된 에이전트 초기화
# 처음에는 triage_agent로 시작하고, 필요에 따라 다른 에이전트로 전환됨
if "agent" not in st.session_state:
    st.session_state["agent"] = triage_agent


# =============================================================================
# 오디오 변환 함수
# =============================================================================

def convert_audio(audio_input):
    """
    Streamlit의 audio_input 위젯에서 받은 오디오 데이터를
    numpy 배열로 변환하는 함수입니다.
    
    Args:
        audio_input: Streamlit의 st.audio_input()에서 반환된 오디오 객체
        
    Returns:
        np.ndarray: int16 타입의 오디오 샘플 배열
    """
    # Streamlit 오디오 입력에서 바이트 데이터 추출
    audio_data = audio_input.getvalue()

    # WAV 파일을 바이트 스트림으로 열기
    # io.BytesIO: 메모리 내 바이트 데이터를 파일처럼 다룰 수 있게 해줌
    with wave.open(io.BytesIO(audio_data), "rb") as wav_file:
        # 모든 프레임 읽기 (-1은 전체 프레임을 의미)
        audio_frames = wav_file.readframes(-1)

    # 바이트 데이터를 numpy 배열로 변환
    # dtype=np.int16: 16비트 정수형 (일반적인 오디오 포맷)
    return np.frombuffer(
        audio_frames,
        dtype=np.int16,
    )


# =============================================================================
# 에이전트 실행 함수 (비동기)
# =============================================================================

async def run_agent(audio_input):
    """
    음성 입력을 받아서 에이전트를 실행하고 음성 응답을 출력하는 메인 함수입니다.
    
    파이프라인 흐름:
    1. 음성 입력 → 오디오 배열 변환
    2. AudioInput 객체 생성
    3. CustomWorkflow 생성 (에이전트 실행 로직 포함)
    4. VoicePipeline 생성 및 실행
    5. 음성 응답 스트리밍 및 재생
    
    Args:
        audio_input: Streamlit의 st.audio_input()에서 반환된 오디오 객체
    """
    # AI 메시지 컨테이너 생성 (채팅 UI에서 AI 응답 표시)
    with st.chat_message("ai"):
        # 처리 상태 표시 (로딩 인디케이터)
        status_container = st.status("⏳ Processing voice message...")
        
        try:
            # =================================================================
            # 1단계: 오디오 데이터 변환
            # =================================================================
            # Streamlit 오디오 입력을 numpy 배열로 변환
            audio_array = convert_audio(audio_input)

            # AudioInput 객체 생성
            # agents.voice.AudioInput: 음성 파이프라인이 처리할 수 있는 형식으로 래핑
            audio = AudioInput(buffer=audio_array)

            # =================================================================
            # 2단계: 워크플로우 및 파이프라인 설정
            # =================================================================
            # CustomWorkflow 생성
            # 이 워크플로우는 음성 입력을 텍스트로 변환하고,
            # 에이전트를 실행하여 응답을 생성하는 로직을 포함합니다.
            workflow = CustomWorkflow(context=user_account_ctx)

            # VoicePipeline 생성
            # VoicePipeline은 다음을 자동으로 처리합니다:
            # - 음성 → 텍스트 변환 (STT: Speech-to-Text)
            # - 워크플로우 실행 (에이전트 처리)
            # - 텍스트 → 음성 변환 (TTS: Text-to-Speech)
            pipeline = VoicePipeline(workflow=workflow)

            # 상태 업데이트
            status_container.update(label="Running workflow", state="running")

            # =================================================================
            # 3단계: 파이프라인 실행
            # =================================================================
            # 비동기로 파이프라인 실행
            # result는 음성 스트림을 포함한 결과 객체입니다.
            result = await pipeline.run(audio)

            # =================================================================
            # 4단계: 오디오 출력 설정
            # =================================================================
            # sounddevice를 사용하여 오디오 출력 스트림 생성
            player = sd.OutputStream(
                samplerate=24000,  # 샘플레이트: 초당 24000개 샘플 (24kHz)
                channels=1,  # 모노 채널 (1채널)
                dtype=np.int16,  # 16비트 정수형
            )
            player.start()  # 오디오 출력 시작

            # 상태 완료 표시
            status_container.update(state="complete")

            # =================================================================
            # 5단계: 음성 응답 스트리밍 및 재생
            # =================================================================
            # 결과 스트림에서 이벤트를 비동기로 받아서 처리
            async for event in result.stream():
                # 음성 오디오 이벤트인 경우
                if event.type == "voice_stream_event_audio":
                    # 오디오 데이터를 스피커로 출력
                    # 실시간으로 스트리밍되어 사용자가 즉시 응답을 들을 수 있음
                    player.write(event.data)

        # =====================================================================
        # 예외 처리
        # =====================================================================
        except InputGuardrailTripwireTriggered:
            # 입력 가드레일 위반: 부적절한 입력 감지
            # 예: 주제와 관련 없는 요청
            st.write("I can't help you with that.")

        except OutputGuardrailTripwireTriggered:
            # 출력 가드레일 위반: 부적절한 출력 감지
            # 예: 민감한 정보 포함 응답
            st.write("Cant show you that answer.")


# =============================================================================
# Streamlit UI 구성
# =============================================================================

# 음성 입력 위젯
# 사용자가 마이크로 음성을 녹음할 수 있는 버튼 제공
audio_input = st.audio_input(
    "Record your message",  # 버튼에 표시될 텍스트
)

# 음성 입력이 있는 경우 처리
if audio_input:
    # 사용자 메시지 표시 (채팅 UI)
    with st.chat_message("human"):
        # 녹음된 오디오를 재생할 수 있는 플레이어 표시
        st.audio(audio_input)
    
    # 에이전트 실행
    # asyncio.run(): 비동기 함수를 동기적으로 실행
    # Streamlit은 동기 함수만 직접 지원하므로 필요
    asyncio.run(run_agent(audio_input))


# =============================================================================
# 사이드바: 세션 관리 및 디버깅
# =============================================================================

with st.sidebar:
    # 메모리 리셋 버튼
    # 대화 기록을 모두 삭제하고 새로 시작
    reset = st.button("Reset memory")
    if reset:
        # 세션 클리어 (비동기 함수)
        asyncio.run(session.clear_session())
    
    # 현재 세션의 대화 항목 표시 (디버깅용)
    # 실제 대화 기록을 확인할 수 있음
    st.write(asyncio.run(session.get_items()))
