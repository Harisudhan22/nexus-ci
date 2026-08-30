import uuid
import datetime
import hashlib
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class CommonInternalRecord(BaseModel):
    id: str = Field(default_factory=lambda: f"rec-{uuid.uuid4().hex[:8]}")
    source_adapter: str  # e.g. "mock_cctns", "mock_cdr", "mock_financial"
    source_record_id: str  # e.g. "FIR-2026-101", "CDR-9876543210-01"
    record_type: str  # FIR, CDR, TRANSACTION, SURVEILLANCE, DOSSIER, INTEL_REPORT, SOCIAL_INTEL, VEHICLE_RECORD
    case_id: Optional[str] = None
    timestamp: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    sha256: str = ""
    payload: Dict[str, Any] = Field(default_factory=dict)
    raw_text: str = ""
    extracted_entities: List[Dict[str, Any]] = Field(default_factory=list)
    extracted_relationships: List[Dict[str, Any]] = Field(default_factory=list)

class BaseSourceAdapter:
    adapter_name: str = "base_adapter"
    source_category: str = "GENERIC"

    def normalize(self, raw_input: Dict[str, Any], case_id: Optional[str] = None) -> CommonInternalRecord:
        raise NotImplementedError("Subclasses must implement normalize")

    def compute_sha256(self, content: str | bytes) -> str:
        if isinstance(content, str):
            content = content.encode("utf-8")
        return hashlib.sha256(content).hexdigest()
