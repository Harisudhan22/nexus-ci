from pydantic import BaseModel
from typing import List

class TimelineEventResponse(BaseModel):
    id: str
    caseId: str
    timestamp: str
    type: str
    title: str
    entityIds: List[str]
    evidenceId: str

    class Config:
        from_attributes = True
