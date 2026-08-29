from pydantic import BaseModel
from typing import List, Optional

class CopilotQueryRequest(BaseModel):
    case_id: str
    question: str

class CopilotQueryResponse(BaseModel):
    summary: str
    key_reasons: List[str]
    observed_evidence: List[str]
    analytical_interpretation: List[str]
    confidence: int
    supporting_evidence: List[str]
