from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any

from app.db.postgres import get_db
from app.db.neo4j_db import get_neo4j
from app.core.dependencies import get_current_user, verify_case_access
from app.models.models import User
from app.services.analytics.graph_analytics import GraphAnalyticsService

router = APIRouter(prefix="/analytics", tags=["analytics"])

@router.get("/centrality")
def get_graph_centrality(
    case_id: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    neo4j_sess = Depends(get_neo4j)
):
    """Returns Degree Centrality, Betweenness Centrality, PageRank, and Bridge entity classifications."""
    if case_id and not verify_case_access(current_user, case_id, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")
    
    svc = GraphAnalyticsService(db=db, neo4j_session=neo4j_sess)
    return svc.compute_centrality(case_id=case_id)

@router.get("/communities")
def get_graph_communities(
    case_id: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    neo4j_sess = Depends(get_neo4j)
):
    """Returns Louvain / Greedy Modularity detected network communities."""
    if case_id and not verify_case_access(current_user, case_id, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    svc = GraphAnalyticsService(db=db, neo4j_session=neo4j_sess)
    return svc.compute_communities(case_id=case_id)

@router.get("/path")
def get_shortest_path(
    from_id: str = Query(..., alias="from"),
    to_id: str = Query(..., alias="to"),
    mode: str = Query("shortest", description="shortest or strongest"),
    case_id: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    neo4j_sess = Depends(get_neo4j)
):
    """Computes shortest or highest-confidence path between two entities."""
    if case_id and not verify_case_access(current_user, case_id, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    svc = GraphAnalyticsService(db=db, neo4j_session=neo4j_sess)
    result = svc.find_shortest_path(from_id=from_id, to_id=to_id, case_id=case_id, mode=mode)
    if not result:
        raise HTTPException(status_code=404, detail=f"No graph connection path exists between '{from_id}' and '{to_id}' in case {case_id or 'all'}.")
    return result

@router.get("/network-dna")
def get_network_dna(
    case_id: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    neo4j_sess = Depends(get_neo4j)
):
    """Calculates Network DNA structural statistics."""
    if case_id and not verify_case_access(current_user, case_id, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    svc = GraphAnalyticsService(db=db, neo4j_session=neo4j_sess)
    return svc.get_network_dna(case_id=case_id)

@router.get("/temporal")
def get_temporal_analytics(
    case_id: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    neo4j_sess = Depends(get_neo4j)
):
    """Returns temporal progression statistics for network relationships."""
    if case_id and not verify_case_access(current_user, case_id, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    svc = GraphAnalyticsService(db=db, neo4j_session=neo4j_sess)
    return svc.get_temporal_stats(case_id=case_id)

@router.get("/summary")
def get_analytics_summary(
    case_id: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    neo4j_sess = Depends(get_neo4j)
):
    """Unified Graph Analytics Summary combining centrality, communities, and network DNA."""
    if case_id and not verify_case_access(current_user, case_id, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    svc = GraphAnalyticsService(db=db, neo4j_session=neo4j_sess)
    cent = svc.compute_centrality(case_id=case_id)
    comms = svc.compute_communities(case_id=case_id)
    dna = svc.get_network_dna(case_id=case_id)

    return {
        "networkDna": dna,
        "communities": comms,
        "topBridges": cent.get("topBridges", []),
        "topConnected": cent.get("topConnected", [])
    }
