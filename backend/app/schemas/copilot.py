from pydantic import BaseModel
from typing import List, Optional

class CopilotQueryRequest(BaseModel):
    case_id: str
    question: str

class CopilotQueryResponse(BaseModel):
    answer: Optional[str] = None
    summary: str
    key_reasons: List[str]
    observed_evidence: List[str]
    analytical_interpretation: List[str]
    confidence: int
    supporting_evidence: List[str]
    sources: List[str] = []
    cases: List[str] = []
    entities: List[str] = []
    evidence: List[str] = []
    graph_facts: List[str] = []
    graphFacts: List[str] = []
    limitations: List[str] = []
    provider_type: str = "LOCAL_FALLBACK"
    providerType: str = "LOCAL_FALLBACK"
    provider_name: str = "grounded_local"
    providerName: str = "grounded_local"
    model: str = "GroundedLocalSolver"
    is_real_llm: bool = False
