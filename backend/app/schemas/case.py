from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class CaseBase(BaseModel):
    title: str
    description: Optional[str] = None
    status: str = "active"
    priority: str = "medium"
    agency: str
    classification: str = "RESTRICTED"

class CaseCreate(CaseBase):
    id: str

class CaseUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    classification: Optional[str] = None
    assigned_to: Optional[str] = None

class CaseResponse(CaseBase):
    id: str
    assigned_to: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class CaseStatsResponse(BaseModel):
    entities: int
    evidence: int
    findings: int
    crossCaseLinks: int
    lastActivity: Optional[str] = None
