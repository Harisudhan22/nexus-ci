from pydantic import BaseModel
from typing import Optional, List

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserResponse(BaseModel):
    id: str
    name: str
    username: str
    email: str
    role: str
    agency: Optional[str] = None
    clearance: str
    caseAccess: Union[List[str], str] = "ALL"

    class Config:
        from_attributes = True

# We import Union at runtime
from typing import Union
