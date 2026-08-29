from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class GraphTimeframe(BaseModel):
    from_date: Optional[str] = None
    to_date: Optional[str] = None

class GraphEdgeResponse(BaseModel):
    id: str
    source: str
    target: str
    type: str
    confidence: int
    occurrences: int
    timeframe: Dict[str, str]
    evidenceIds: List[str]
    createdByPipeline: str
    suspicious: Optional[bool] = False
    rationale: str

class GraphResponse(BaseModel):
    nodes: List[Dict[str, Any]]
    edges: List[GraphEdgeResponse]

class PathResponse(BaseModel):
    nodeIds: List[str]
    edges: List[GraphEdgeResponse]
    totalConfidence: int
    hops: int
