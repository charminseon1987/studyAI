from pydantic import BaseModel


class UserAccountContext(BaseModel): #BaseModel : 자동으로 데이터 검증 기능
    customer_id: int
    name : str
    tier : str = "basic"   # 등급 : premium , enterprise    
    email: str 

class InputGuardRailOutput(BaseModel):
    is_off_topic : bool
    reason: str