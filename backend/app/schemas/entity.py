from pydantic import BaseModel, Field
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
    caseIds: List[str] = Field(default_factory=list, validation_alias="case_ids")
    aliases: List[str] = Field(default_factory=list)
    relevance: int = 50
    attributes: Dict[str, Any] = Field(default_factory=dict)
    cluster: Optional[str] = None
    x: float = 0.0
    y: float = 0.0

    class Config:
        from_attributes = True
        populate_by_name = True

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
