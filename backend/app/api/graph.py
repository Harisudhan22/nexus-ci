from fastapi import APIRouter, Depends, HTTPException, Query, Body, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional

from app.db.postgres import get_db
from app.db.neo4j_db import get_neo4j
from app.core.dependencies import get_current_user, verify_case_access
from app.models.models import User, CanonicalEntity, Document
from app.services.graph.graph_service import Neo4jGraphService
from app.services.graph.analytics import run_network_analytics
from app.services.graph.nl_graph_query import SafeNLGraphQueryEngine

router = APIRouter(tags=["graph"])

@router.get("/cases/{case_id}/graph")
def get_case_graph(
    case_id: str,
    entity_type: Optional[str] = Query(None),
    relationship_type: Optional[str] = Query(None),
    min_confidence: int = Query(0),
    suspicious_only: bool = Query(False),
    selected_entity: Optional[str] = Query(None),
    limit: int = Query(100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    neo4j_sess = Depends(get_neo4j)
):
    if not verify_case_access(current_user, case_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    filters = {
        "entity_type": entity_type,
        "relationship_type": relationship_type,
        "min_confidence": min_confidence,
        "suspicious_only": suspicious_only,
        "selected_entity": selected_entity,
        "limit": limit
    }
    service = Neo4jGraphService(neo4j_sess, db)
    subgraph = service.get_subgraph(case_id, filters)
    nodes = subgraph.get("nodes", [])
    edges = subgraph.get("edges", [])

    centrality_map = run_network_analytics(nodes, edges)

    return {
        "nodes": nodes,
        "edges": edges,
        "centrality": centrality_map,
        "graphSource": subgraph.get("graphSource", "none")
    }


@router.post("/cases/{case_id}/graph/query")
def natural_language_graph_query(
    case_id: str,
    payload: Dict[str, Any] = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    neo4j_sess = Depends(get_neo4j)
):
    """Executes safe natural language graph query using allowlisted Cypher templates."""
    if not verify_case_access(current_user, case_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    question = payload.get("question", "").strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question parameter is required.")

    engine = SafeNLGraphQueryEngine(db=db, neo4j_sess=neo4j_sess)

    try:
        res = engine.execute_nl_query(question=question, case_id=case_id, user=current_user)
        return res
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
