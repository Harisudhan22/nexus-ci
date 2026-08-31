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

@router.get("/status")
def get_rag_status_endpoint(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Returns runtime vector search status, active embedding model, dimension, and index counts."""
    from app.services.rag.vector_backend import get_vector_status
    return get_vector_status(db)


class ReindexRequest(BaseModel):
    case_id: Optional[str] = None


@router.post("/reindex")
def reindex_rag_endpoint(
    req: Optional[ReindexRequest] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Reindexes document chunk embeddings with the active vector model. Authenticated and auditable."""
    case_id = req.case_id if req else None
    if case_id and not verify_case_access(current_user, case_id, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    from app.services.rag.vector_backend import reindex_all_chunks
    result = reindex_all_chunks(db, case_id=case_id)

    # Log audit event
    import uuid, datetime
    from app.models.models import AuditLog
    audit = AuditLog(
        id=f"audit-{uuid.uuid4().hex[:8]}",
        timestamp=datetime.datetime.utcnow(),
        user_id=current_user.id,
        action="REINDEX",
        case_id=case_id,
        resource=f"RAG Vector Store Reindex ({result['processed']} chunks)",
        result="success" if result["failed"] == 0 else "partial"
    )
    db.add(audit)
    db.commit()

    return result


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

