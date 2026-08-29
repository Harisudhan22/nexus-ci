from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List, Dict, Any

class EvidenceResponse(BaseModel):
    id: str
    caseId: str
    title: str
    sourceType: str
    fileName: str
    sha256: str
    uploadedAt: str
    uploadedBy: str
    sizeBytes: int
    status: str
    relevance: int
    extractedText: Optional[str] = None
    rows: Optional[List[Dict[str, Any]]] = None
    entityMentions: List[str] = []

    class Config:
        from_attributes = True

class IntegrityVerificationResponse(BaseModel):
    verified: bool
    message: str
    sha256: str
