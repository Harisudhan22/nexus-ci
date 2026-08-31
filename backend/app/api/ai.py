from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from app.db.postgres import get_db
from app.db.neo4j_db import get_neo4j
from app.core.dependencies import get_current_user, verify_case_access
from app.models.models import User, CanonicalEntity, EntityRelationship
from app.services.graph.graph_service import Neo4jGraphService

router = APIRouter(prefix="/ai", tags=["ai"])

def sanitize_cypher_input(raw_input: str) -> bool:
    """Rejects raw inputs containing dangerous write/delete Cypher statements."""
    forbidden = ["delete", "detach", "drop", "create", "merge", "set", "remove"]
    words = raw_input.lower().split()
    return not any(f in words for f in forbidden)

class GraphQueryRequest(BaseModel):
    prompt: str
    case_id: Optional[str] = None
    max_depth: Optional[int] = 2

@router.post("/graph-query")
def safe_nl_graph_query(
    req: GraphQueryRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    neo4j_sess = Depends(get_neo4j)
):
    """Executes safe Natural Language Graph Queries via allowlisted parameterised templates."""
    if req.case_id and not verify_case_access(current_user, req.case_id, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    p_lower = req.prompt.lower()
    all_entities = db.query(CanonicalEntity).all()

    matched_ent = None
    for ent in all_entities:
        if ent.label.lower() in p_lower or any(str(a).lower() in p_lower for a in ent.aliases):
            matched_ent = ent
            break

    graph_svc = Neo4jGraphService(session=neo4j_sess, db=db)

    # Template 1: Neighborhood Traversal around matched entity
    if matched_ent:
        subg = graph_svc.get_subgraph(
            case_id=req.case_id or (matched_ent.case_ids[0] if matched_ent.case_ids else "case-101"),
            filters={"selected_entity": matched_ent.id}
        )
        return {
            "templateUsed": "ALLOWLISTED_NEIGHBORHOOD_TRAVERSAL",
            "matchedEntity": {"id": matched_ent.id, "label": matched_ent.label, "type": matched_ent.type},
            "explanation": f"Executed 2-degree neighborhood query centered on entity '{matched_ent.label}'.",
            "nodes": subg.get("nodes", []),
            "edges": subg.get("edges", []),
            "count": len(subg.get("nodes", []))
        }

    # Template 2: Full Case Graph Traversal
    subg = graph_svc.get_subgraph(case_id=req.case_id or "case-101")
    return {
        "templateUsed": "ALLOWLISTED_CASE_GRAPH_QUERY",
        "matchedEntity": None,
        "explanation": f"Executed full case network graph query for case '{req.case_id or 'case-101'}'.",
        "nodes": subg.get("nodes", []),
        "edges": subg.get("edges", []),
        "count": len(subg.get("nodes", []))
    }
