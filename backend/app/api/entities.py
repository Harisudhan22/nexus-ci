from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional

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

# NOTE: /entities/search MUST be declared BEFORE /entities/{id} to prevent
# FastAPI from capturing "search" as the {id} parameter.
@router.get("/entities/search")
def search_global_entities(
    q: str = Query("", description="Search term for names, phones, vehicles, accounts, etc."),
    entity_type: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Global search across the entire Historical Intelligence Database."""
    from app.models.models import EntityRelationship, Finding, Document, Case
    term = q.strip().lower()
    all_ents = db.query(CanonicalEntity).all()
    results = []
    for ent in all_ents:
        if entity_type and ent.type.lower() != entity_type.lower():
            continue
        match_score = 0
        reasons = []
        if term in ent.label.lower():
            match_score += 100
            reasons.append(f"Direct name match on '{ent.label}'")
        for alias in ent.aliases:
            if term and term in str(alias).lower():
                match_score += 80
                reasons.append(f"Alias match on '{alias}'")
        if ent.attributes:
            for k, v in ent.attributes.items():
                if term and term in str(v).lower():
                    match_score += 70
                    reasons.append(f"Attribute match on {k}: '{v}'")
        if not term:
            match_score = ent.relevance
        if match_score > 0:
            rels = db.query(EntityRelationship).filter(
                (EntityRelationship.source_id == ent.id) | (EntityRelationship.target_id == ent.id)
            ).all()
            linked_phones, linked_vehicles, linked_locations, linked_accounts, linked_orgs = [], [], [], [], []
            for r in rels:
                other_id = r.target_id if r.source_id == ent.id else r.source_id
                other_ent = db.query(CanonicalEntity).filter(CanonicalEntity.id == other_id).first()
                if other_ent:
                    if other_ent.type == "phone" and other_ent.label not in linked_phones:
                        linked_phones.append(other_ent.label)
                    elif other_ent.type == "vehicle" and other_ent.label not in linked_vehicles:
                        linked_vehicles.append(other_ent.label)
                    elif other_ent.type == "location" and other_ent.label not in linked_locations:
                        linked_locations.append(other_ent.label)
                    elif other_ent.type == "account" and other_ent.label not in linked_accounts:
                        linked_accounts.append(other_ent.label)
                    elif other_ent.type == "org" and other_ent.label not in linked_orgs:
                        linked_orgs.append(other_ent.label)
            case_objs = db.query(Case).filter(Case.id.in_(ent.case_ids)).all()
            case_summaries = [{"id": c.id, "title": c.title, "priority": c.priority} for c in case_objs]
            from sqlalchemy import cast, String
            findings_count = db.query(Finding).filter(
                cast(Finding.entity_ids, String).contains(ent.id)
            ).count()
            results.append({
                "id": ent.id, "label": ent.label, "type": ent.type,
                "subtitle": ent.subtitle, "aliases": ent.aliases,
                "caseIds": ent.case_ids, "cases": case_summaries,
                "relevance": ent.relevance, "attributes": ent.attributes,
                "phones": linked_phones, "vehicles": linked_vehicles,
                "locations": linked_locations, "accounts": linked_accounts,
                "organizations": linked_orgs, "relationshipsCount": len(rels),
                "findingsCount": findings_count, "matchReasons": reasons
            })
    results.sort(key=lambda x: (len(x["caseIds"]), x["relevance"]), reverse=True)
    return results

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



@router.get("/entities/{id}/cross-case-analysis")
def get_cross_case_analysis(
    id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Deep cross-case convergence analysis for an entity."""
    ent = db.query(CanonicalEntity).filter(CanonicalEntity.id == id).first()
    if not ent:
        raise HTTPException(status_code=404, detail="Entity not found.")

    from app.models.models import Case, EntityRelationship, Document, Finding

    cases = db.query(Case).filter(Case.id.in_(ent.case_ids)).all()
    rels = db.query(EntityRelationship).filter(
        (EntityRelationship.source_id == ent.id) | (EntityRelationship.target_id == ent.id)
    ).all()

    evidence_ids = set()
    for r in rels:
        if r.evidence_ids:
            evidence_ids.update(r.evidence_ids)

    from sqlalchemy import cast, String
    evidence_docs = db.query(Document).filter(Document.id.in_(list(evidence_ids))).all()
    findings = db.query(Finding).filter(cast(Finding.entity_ids, String).contains(ent.id)).all()

    convergence_factors = []
    if len(ent.case_ids) > 1:
        convergence_factors.append({
            "factor": "Multi-Case Overlap",
            "description": f"Entity observed across {len(ent.case_ids)} active/historical operations: {', '.join(ent.case_ids)}.",
            "confidence": 95
        })
    if len(ent.aliases) > 1:
        convergence_factors.append({
            "factor": "Alias Variant Alignment",
            "description": f"Resolved variants: {', '.join(ent.aliases)}.",
            "confidence": 90
        })
    if rels:
        convergence_factors.append({
            "factor": "Network Linkages",
            "description": f"{len(rels)} confirmed relational edges across phone, banking, and physical logistics.",
            "confidence": 88
        })

    return {
        "entity": {
            "id": ent.id,
            "label": ent.label,
            "type": ent.type,
            "aliases": ent.aliases,
            "attributes": ent.attributes,
            "caseIds": ent.case_ids
        },
        "cases": [{"id": c.id, "title": c.title, "status": c.status, "agency": c.agency} for c in cases],
        "relationships": [{"id": r.id, "source": r.source_id, "target": r.target_id, "type": r.rel_type, "confidence": r.confidence, "rationale": r.rationale} for r in rels],
        "evidence": [{"id": d.id, "filename": d.filename, "sourceType": d.source_type, "caseId": d.case_id} for d in evidence_docs],
        "findings": [{"id": f.id, "title": f.title, "severity": f.severity, "why": f.why} for f in findings],
        "convergenceFactors": convergence_factors
    }
