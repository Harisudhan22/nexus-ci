from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any

from app.db.postgres import get_db
from app.core.dependencies import get_current_user, verify_case_access
from app.models.models import CanonicalEntity, User, Document, RawMention
from app.schemas.entity import CanonicalEntityResponse, CrossCaseLinkResponse

router = APIRouter(tags=["entities"])

@router.get("/cases/{case_id}/entities", response_model=List[CanonicalEntityResponse])
def get_case_entities(
    case_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not verify_case_access(current_user, case_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    all_ents = db.query(CanonicalEntity).all()
    # Filter canonical entities that are linked to this case
    case_ents = []
    for ent in all_ents:
        if case_id in ent.case_ids:
            case_ents.append(ent)
            
    return case_ents

@router.get("/entities/{id}", response_model=CanonicalEntityResponse)
def get_entity(
    id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    ent = db.query(CanonicalEntity).filter(CanonicalEntity.id == id).first()
    if not ent:
        raise HTTPException(status_code=404, detail="Entity not found.")
    return ent

@router.get("/entities/{id}/cases", response_model=CrossCaseLinkResponse)
def get_entity_cases(
    id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    entity = db.query(CanonicalEntity).filter(CanonicalEntity.id == id).first()
    if not entity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entity not found.")

    # Check case access for at least one case the entity belongs to
    has_access = False
    for c_id in entity.case_ids:
        if verify_case_access(current_user, c_id):
            has_access = True
            break
            
    if not has_access:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    reasons = [f"Direct mention in document records across {len(entity.case_ids)} cases."]
    if len(entity.case_ids) > 1:
        reasons.append("Identified as an recurring cross-case node.")

    return {
        "id": f"ccl-{entity.id}",
        "canonicalId": entity.id,
        "label": entity.label,
        "type": entity.type,
        "confidence": 90 if len(entity.case_ids) > 1 else 50,
        "caseIds": entity.case_ids,
        "reasons": reasons
    }

@router.get("/cases/{case_id}/cross-case-links", response_model=List[CrossCaseLinkResponse])
def get_cross_case_links(
    case_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not verify_case_access(current_user, case_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    all_ents = db.query(CanonicalEntity).all()
    links = []
    for ent in all_ents:
        # If it belongs to current case and at least one other case
        if case_id in ent.case_ids and len(ent.case_ids) > 1:
            links.append({
                "id": f"ccl-{ent.id}",
                "canonicalId": ent.id,
                "label": ent.label,
                "type": ent.type,
                "confidence": 90,
                "caseIds": ent.case_ids,
                "reasons": [f"Matches normalized entity '{ent.label}' in cases {', '.join(ent.case_ids)}."]
            })
    return links
