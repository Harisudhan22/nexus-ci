from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class RawMentionResponse(BaseModel):
    id: str
    caseId: str
    evidenceId: str
    surface: str
    type: str
    resolvedTo: Optional[str] = None

    class Config:
        from_attributes = True

class CanonicalEntityResponse(BaseModel):
    id: str
    type: str
    label: str
    subtitle: Optional[str] = None
    caseIds: List[str]
    aliases: List[str]
    relevance: int
    attributes: Dict[str, Any]
    cluster: Optional[str] = None
    x: float
    y: float

    class Config:
        from_attributes = True

class MatchSignal(BaseModel):
    label: str
    matched: bool

class ResolutionCandidateResponse(BaseModel):
    id: str
    caseId: str
    canonicalId: str
    canonicalLabel: str
    type: str
    mentions: List[str]
    confidence: int
    signals: List[MatchSignal]
    status: str

    class Config:
        from_attributes = True

class ResolutionReviewRequest(BaseModel):
    candidate_id: str
    decision: str  # "accepted" or "rejected"

class CrossCaseLinkResponse(BaseModel):
    id: str
    canonicalId: str
    label: str
    type: str
    confidence: int
    caseIds: List[str]
    reasons: List[str]
