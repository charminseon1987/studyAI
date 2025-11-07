from pydantic import BaseModel


class UserAccountContext(BaseModel):
    customer_id: int
    name : str
    tier : str = "basic"   # 등급 : premium , enterprise    
    email: str 

class InputGuardRailOuput(BaseModel):
    is_off_topic : bool
    reason: str