from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any

from app.db.postgres import get_db
from app.db.neo4j_db import get_neo4j
from app.core.dependencies import get_current_user, verify_case_access
from app.models.models import User
from app.services.copilot.copilot_service import CopilotService
from app.schemas.copilot import CopilotQueryRequest, CopilotQueryResponse

router = APIRouter(prefix="/copilot", tags=["copilot"])

@router.post("/query", response_model=CopilotQueryResponse)
def query_copilot(
    req: CopilotQueryRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    neo4j_sess = Depends(get_neo4j)
):
    if not verify_case_access(current_user, req.case_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this case context."
        )

    from app.services.graph.graph_service import Neo4jGraphService
    graph_svc = Neo4jGraphService(session=neo4j_sess, db=db)
    service = CopilotService(db=db, graph_service=graph_svc)
    res = service.query(
        case_id=req.case_id,
        question=req.question,
        user_id=current_user.id
    )
    return res

@router.get("/status")
def get_copilot_status():
    """Returns current active LLM provider configuration and status without exposing credentials."""
    from app.services.copilot.llm_provider import get_provider_status
    return get_provider_status()
