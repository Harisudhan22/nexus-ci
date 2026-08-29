from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional

class FindingResponse(BaseModel):
    id: str
    caseId: str
    title: str
    category: str
    severity: str
    confidence: int
    why: str
    entityIds: List[str]
    evidenceIds: List[str]
    status: str
    createdAt: datetime

    class Config:
        from_attributes = True

class FindingAcknowledgeRequest(BaseModel):
    status: str  # e.g. "acknowledged" or "investigating"
