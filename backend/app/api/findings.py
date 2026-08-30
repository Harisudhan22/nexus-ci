from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any

from app.db.postgres import get_db
from app.core.dependencies import get_current_user, verify_case_access
from app.models.models import Finding, User, AuditLog
from app.schemas.finding import FindingResponse, FindingAcknowledgeRequest
import uuid
import datetime

router = APIRouter(tags=["findings"])

@router.get("/cases/{case_id}/findings", response_model=List[FindingResponse])
def get_case_findings(
    case_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not verify_case_access(current_user, case_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")
    return db.query(Finding).filter(Finding.case_id == case_id).all()

@router.post("/findings/{id}/acknowledge", response_model=FindingResponse)
def acknowledge_finding(
    id: str,
    req: FindingAcknowledgeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    finding = db.query(Finding).filter(Finding.id == id).first()
    if not finding:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Finding not found.")
        
    if not verify_case_access(current_user, finding.case_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    old_status = finding.status
    finding.status = req.status
    db.commit()

    # Log audit entry
    audit = AuditLog(
        id=f"audit-{uuid.uuid4().hex[:8]}",
        timestamp=datetime.datetime.utcnow(),
        user_id=current_user.id,
        action="FINDING_ACKNOWLEDGE",
        case_id=finding.case_id,
        resource=f"Finding {finding.title} (Status changed from {old_status} to {req.status})",
        result="success"
    )
    db.add(audit)
    db.commit()
    db.refresh(finding)

    return finding

@router.get("/findings/{id}/explanation")
def get_finding_explanation(
    id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Provides full analytical explanation, signals, and evidence citations for a finding."""
    from app.services.analytics.pattern_engine import SuspiciousPatternEngine
    engine = SuspiciousPatternEngine(db)
    return engine.get_finding_explanation(id)
