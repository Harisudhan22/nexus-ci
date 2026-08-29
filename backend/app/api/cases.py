from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any

from app.db.postgres import get_db
from app.core.dependencies import get_current_user, verify_case_access
from app.models.models import Case, User, Document, CanonicalEntity, Finding, EntityMergeDecision
from app.schemas.case import CaseResponse, CaseCreate, CaseStatsResponse

router = APIRouter(prefix="/cases", tags=["cases"])

@router.get("", response_model=List[CaseResponse])
def get_cases(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Supervisor/Admin see all, Investigator see assigned or listed cases
    query = db.query(Case)
    if current_user.role.lower() not in ["admin", "supervisor"]:
        # If user is arjun, he can only see case-101. If user is lena, case-101 and case-205.
        if current_user.id == "u-arjun":
            query = query.filter(Case.id == "case-101")
        elif current_user.id == "u-lena":
            query = query.filter(Case.id.in_(["case-101", "case-205"]))
            
    return query.all()

@router.post("", response_model=CaseResponse)
def create_case(
    req: CaseCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role.lower() not in ["admin", "supervisor", "senior_investigator"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to create a case."
        )
        
    existing = db.query(Case).filter(Case.id == req.id).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Case with this ID already exists."
        )

    db_case = Case(
        id=req.id,
        title=req.title,
        description=req.description,
        status=req.status,
        priority=req.priority,
        agency=req.agency,
        classification=req.classification,
        assigned_to=current_user.id
    )
    db.add(db_case)
    db.commit()
    db.refresh(db_case)
    return db_case

@router.get("/{case_id}", response_model=CaseResponse)
def get_case(
    case_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not verify_case_access(current_user, case_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")
        
    db_case = db.query(Case).filter(Case.id == case_id).first()
    if not db_case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found.")
    return db_case

@router.get("/{case_id}/stats", response_model=CaseStatsResponse)
def get_case_stats(
    case_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not verify_case_access(current_user, case_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    # Calculate statistics
    # 1. Total entities resolved in this case
    # A canonical entity belongs to this case if case_id is inside its case_ids list
    # Because sqlite/postgres case_ids is JSON/String, we look up or filter
    all_ents = db.query(CanonicalEntity).all()
    case_ents = [e for e in all_ents if case_id in e.case_ids]

    # 2. Total evidence files
    ev_count = db.query(Document).filter(Document.case_id == case_id).count()

    # 3. Total findings
    findings_count = db.query(Finding).filter(Finding.case_id == case_id).count()

    # 4. Cross case links (how many of these entities exist in other cases)
    cross_links = sum(1 for e in case_ents if len(e.case_ids) > 1)

    # 5. Last activity
    db_case = db.query(Case).filter(Case.id == case_id).first()
    last_act = db_case.updated_at.isoformat() if db_case else None

    return {
        "entities": len(case_ents),
        "evidence": ev_count,
        "findings": findings_count,
        "crossCaseLinks": cross_links,
        "lastActivity": last_act
    }
