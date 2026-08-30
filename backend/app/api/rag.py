from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from app.db.postgres import get_db
from app.core.dependencies import get_current_user, verify_case_access
from app.models.models import User
from app.services.rag.rag_service import RAGService

router = APIRouter(prefix="/rag", tags=["rag"])

class RAGQueryRequest(BaseModel):
    question: str
    case_id: Optional[str] = None
    entity_ids: Optional[List[str]] = None
    top_k: Optional[int] = 5

@router.post("/query")
def query_rag_endpoint(
    req: RAGQueryRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieves evidence-grounded document chunks matching user query within scope."""
    if req.case_id and not verify_case_access(current_user, req.case_id, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    rag_svc = RAGService(db)
    result = rag_svc.query_rag(
        question=req.question,
        case_id=req.case_id,
        user_accessible_cases=[c.id for c in current_user.cases] if current_user.role != "admin" else None,
        top_k=req.top_k or 5
    )
    return result
