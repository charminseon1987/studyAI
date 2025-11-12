"""
=============================================================================
데이터 모델 정의
=============================================================================

이 파일은 Pydantic을 사용하여 데이터 모델을 정의합니다.
Pydantic은 자동으로 데이터 검증, 타입 변환, 직렬화/역직렬화를 제공합니다.

주요 모델:
1. UserAccountContext: 사용자 계정 정보
2. InputGuardRailOutput: 입력 가드레일 검사 결과
3. TechnicalOutputGuardRailOutput: 기술 지원 출력 가드레일 검사 결과
4. HandoffContext: 에이전트 전환 컨텍스트
"""

# =============================================================================
# Import
# =============================================================================

# BaseModel: Pydantic의 기본 모델 클래스
# 자동으로 데이터 검증, 타입 변환, JSON 직렬화/역직렬화 기능 제공
from pydantic import BaseModel


# =============================================================================
# 사용자 계정 컨텍스트 모델
# =============================================================================

class UserAccountContext(BaseModel):
    """
    사용자 계정 정보를 담는 컨텍스트 모델입니다.
    
    이 모델은 에이전트가 사용자 정보에 접근할 때 사용됩니다.
    모든 에이전트 함수의 첫 번째 매개변수로 전달되어
    사용자별 맞춤 서비스를 제공할 수 있게 합니다.
    
    Attributes:
        customer_id: 고객 고유 ID
        name: 고객 이름
        tier: 서비스 등급 (기본값: "basic")
              가능한 값: "basic", "premium", "enterprise"
        email: 고객 이메일 주소
    
    Example:
        >>> context = UserAccountContext(
        ...     customer_id=1,
        ...     name="홍길동",
        ...     tier="premium",
        ...     email="hong@example.com"
        ... )
    """
    customer_id: int  # 고객 고유 ID
    name: str  # 고객 이름
    tier: str = "basic"  # 등급: "basic", "premium", "enterprise"
    email: str  # 이메일 주소


# =============================================================================
# 입력 가드레일 출력 모델
# =============================================================================

class InputGuardRailOutput(BaseModel):
    """
    입력 가드레일 검사 결과를 담는 모델입니다.
    
    입력 가드레일은 사용자의 입력이 적절한지 검사합니다.
    예: 주제와 관련 없는 요청인지 확인
    
    Attributes:
        is_off_topic: 주제와 관련 없는 요청인지 여부
        reason: 검사 결과에 대한 이유 설명
    
    Example:
        >>> output = InputGuardRailOutput(
        ...     is_off_topic=True,
        ...     reason="요청이 고객 지원 범위를 벗어남"
        ... )
    """
    is_off_topic: bool  # 주제와 관련 없는 요청인지 여부
    reason: str  # 검사 결과에 대한 이유 설명


# =============================================================================
# 기술 지원 출력 가드레일 출력 모델
# =============================================================================

class TechnicalOutputGuardRailOutput(BaseModel):
    """
    기술 지원 에이전트의 출력 가드레일 검사 결과를 담는 모델입니다.
    
    출력 가드레일은 에이전트의 응답이 적절한지 검사합니다.
    예: 민감한 정보가 포함되어 있는지 확인
    
    Attributes:
        contains_off_topic: 주제와 관련 없는 내용 포함 여부
        contains_billing_data: 결제 정보 포함 여부
        contains_account_data: 계정 정보 포함 여부
        reason: 검사 결과에 대한 이유 설명
    
    Example:
        >>> output = TechnicalOutputGuardRailOutput(
        ...     contains_off_topic=False,
        ...     contains_billing_data=True,
        ...     contains_account_data=False,
        ...     reason="결제 정보가 포함되어 있어 출력 제한"
        ... )
    """
    contains_off_topic: bool  # 주제와 관련 없는 내용 포함 여부
    contains_billing_data: bool  # 결제 정보 포함 여부
    contains_account_data: bool  # 계정 정보 포함 여부
    reason: str  # 검사 결과에 대한 이유 설명


# =============================================================================
# 에이전트 전환 컨텍스트 모델
# =============================================================================

class HandoffContext(BaseModel):
    """
    에이전트 간 전환(handoff) 정보를 담는 모델입니다.
    
    트리아지 에이전트가 다른 전문 에이전트로 전환할 때
    이 모델을 사용하여 전환 정보를 전달합니다.
    
    Attributes:
        to_agent_name: 전환할 에이전트 이름
        issue_type: 이슈 유형 (예: "billing", "technical", "order", "account")
        issue_description: 이슈에 대한 설명
        reason: 전환 이유
    
    Example:
        >>> handoff = HandoffContext(
        ...     to_agent_name="Billing Support Agent",
        ...     issue_type="billing",
        ...     issue_description="결제 실패 문제",
        ...     reason="결제 전문 에이전트가 필요함"
        ... )
    """
    to_agent_name: str  # 전환할 에이전트 이름
    issue_type: str  # 이슈 유형
    issue_description: str  # 이슈 설명
    reason: str  # 전환 이유


# =============================================================================
# 별칭 (Alias)
# =============================================================================

# handoffData는 HandoffContext의 별칭입니다
# 코드의 가독성을 위해 짧은 이름을 사용
handoffData = HandoffContext