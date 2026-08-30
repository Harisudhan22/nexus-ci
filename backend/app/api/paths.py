from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
import math

from app.db.postgres import get_db
from app.db.neo4j_db import get_neo4j
from app.core.dependencies import get_current_user, verify_case_access
from app.models.models import User, CanonicalEntity
from app.services.graph.graph_service import Neo4jGraphService

router = APIRouter(prefix="/paths", tags=["paths"])

@router.get("")
def get_path(
    from_id: str = Query(..., alias="from"),
    to_id: str = Query(..., alias="to"),
    case_id: Optional[str] = Query(None),
    mode: str = Query("shortest"), # shortest or strongest
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    neo4j_sess = Depends(get_neo4j)
):
    if case_id and not verify_case_access(current_user, case_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to this case.")

    # 1. Try Neo4j graph search
    if neo4j_sess:
        try:
            service = Neo4jGraphService(neo4j_sess)
            path_result = service.get_path(from_id, to_id, mode, case_id)
            if path_result:
                return path_result
        except Exception as e:
            print(f"Neo4j path search error: {e}")

    # 2. Query canonical EntityRelationship table in PostgreSQL
    from app.models.models import EntityRelationship
    all_ents = db.query(CanonicalEntity).all()
    ent_map = {e.id: e for e in all_ents}
    if from_id not in ent_map or to_id not in ent_map:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source or target entity not found in case database."
        )

    rels = db.query(EntityRelationship).all()
    edges = []
    for r in rels:
        if not case_id or case_id in r.case_ids:
            edges.append({
                "id": r.id,
                "source": r.source_id,
                "target": r.target_id,
                "type": r.rel_type,
                "confidence": r.confidence,
                "occurrences": r.occurrences,
                "timeframe": {"from": r.time_from or "", "to": r.time_to or ""},
                "evidenceIds": r.evidence_ids or [],
                "source_file": r.source or "unknown",
                "createdByPipeline": r.created_by_pipeline,
                "suspicious": r.suspicious,
                "rationale": r.rationale or ""
            })

    # Solver
    nodes = [e for e in all_ents if not case_id or case_id in e.case_ids]
    adj = {}
    for n in nodes:
        adj[n.id] = []
    for e in edges:
        adj[e["source"]].append(e)
        # Undirected graph for routing convenience
        e_rev = e.copy()
        e_rev["source"], e_rev["target"] = e["target"], e["source"]
        adj[e["target"]].append(e_rev)

    if from_id not in adj or to_id not in adj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No evidence-supported path found in the current case data."
        )

    # Run BFS
    visited = {from_id: None}
    queue = [from_id]
    found = False
    
    while queue:
        curr = queue.pop(0)
        if curr == to_id:
            found = True
            break
        for edge in adj.get(curr, []):
            nxt = edge["target"]
            if nxt not in visited:
                visited[nxt] = (curr, edge)
                queue.append(nxt)

    if not found:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No evidence-supported path found in the current case data."
        )

    # Reconstruct path
    curr = to_id
    path_nodes = [to_id]
    path_edges = []
    
    while curr != from_id:
        step = visited[curr]
        if not step:
            break
        prev_node, edge = step
        path_edges.insert(0, edge)
        path_nodes.insert(0, prev_node)
        curr = prev_node

    total_conf = int(sum(e["confidence"] for e in path_edges) / len(path_edges)) if path_edges else 0

    return {
        "nodeIds": path_nodes,
        "edges": path_edges,
        "totalConfidence": total_conf,
        "hops": len(path_edges)
    }
