from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Dict, Any

class AuditEntryResponse(BaseModel):
    id: str
    timestamp: datetime
    userId: str
    action: str
    caseId: Optional[str] = None
    resource: str
    result: str

    class Config:
        from_attributes = True
