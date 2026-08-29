from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any

from app.db.postgres import get_db
from app.db.neo4j import get_neo4j
from app.core.dependencies import get_current_user, verify_case_access
from app.models.models import EntityMergeDecision, User
from app.services.entity_resolution.resolution_service import EntityResolutionService
from app.schemas.entity import ResolutionCandidateResponse, ResolutionReviewRequest

router = APIRouter(prefix="/entity-resolution", tags=["entity-resolution"])

@router.get("/candidates", response_model=List[ResolutionCandidateResponse])
def get_resolution_candidates(
    case_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not verify_case_access(current_user, case_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    return db.query(EntityMergeDecision).filter(
        EntityMergeDecision.case_id == case_id,
        EntityMergeDecision.status == "pending"
    ).all()

@router.post("/review")
def review_resolution_candidate(
    req: ResolutionReviewRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    neo4j_sess = Depends(get_neo4j)
):
    # Find candidate
    cand = db.query(EntityMergeDecision).filter(EntityMergeDecision.id == req.candidate_id).first()
    if not cand:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resolution candidate not found.")
        
    if not verify_case_access(current_user, cand.case_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    service = EntityResolutionService(db, neo4j_sess)
    success = service.apply_merge(
        decision_id=req.candidate_id,
        accept=(req.decision.lower() == "accepted"),
        user_id=current_user.id
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to apply merge decision. Review check status or database constraints."
        )

    return {"status": "success", "message": f"Merge candidate decision '{req.decision}' recorded successfully."}
