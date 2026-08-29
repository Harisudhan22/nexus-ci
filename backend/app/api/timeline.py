from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any

from app.db.postgres import get_db
from app.core.dependencies import get_current_user, verify_case_access
from app.models.models import Document, User, CanonicalEntity
from app.schemas.timeline import TimelineEventResponse

router = APIRouter(tags=["timeline"])

@router.get("/cases/{case_id}/timeline", response_model=List[TimelineEventResponse])
def get_case_timeline(
    case_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not verify_case_access(current_user, case_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    events = []

    # 1. Document Upload Events
    docs = db.query(Document).filter(Document.case_id == case_id).all()
    for doc in docs:
        events.append({
            "id": f"evt-doc-{doc.id}",
            "caseId": case_id,
            "timestamp": doc.uploaded_at.isoformat() + "Z",
            "type": "document",
            "title": f"Evidence ingested: {doc.filename} ({doc.source_type})",
            "entityIds": [],
            "evidenceId": doc.id
        })

    # 2. Extract CDR Calls from CDR logs
    # Retrieve phone entity mappings to link to entityIds
    phone_ents = {e.label: e.id for e in db.query(CanonicalEntity).filter(CanonicalEntity.type == "phone").all()}
    
    for doc in docs:
        if doc.source_type.upper() == "CDR" and doc.rows_data:
            for idx, row in enumerate(doc.rows_data):
                caller = str(row.get("caller") or row.get("Caller") or "")
                callee = str(row.get("callee") or row.get("Callee") or "")
                timestamp = str(row.get("timestamp") or row.get("Timestamp") or "")
                dur = str(row.get("duration") or row.get("Duration") or "")
                
                # Check entity ids
                ent_ids = []
                if caller in phone_ents:
                    ent_ids.append(phone_ents[caller])
                if callee in phone_ents:
                    ent_ids.append(phone_ents[callee])

                events.append({
                    "id": f"evt-cdr-{doc.id}-{idx}",
                    "caseId": case_id,
                    "timestamp": timestamp if "T" in timestamp else f"2026-08-20T{timestamp}Z" if timestamp else doc.uploaded_at.isoformat() + "Z",
                    "type": "call",
                    "title": f"Call: {caller} → {callee} ({dur}s)",
                    "entityIds": ent_ids,
                    "evidenceId": doc.id
                })

        # 3. Extract Transactions from Transaction records
        elif doc.source_type.upper() == "TRANSACTIONS" and doc.rows_data:
            account_ents = {e.label: e.id for e in db.query(CanonicalEntity).filter(CanonicalEntity.type == "account").all()}
            for idx, row in enumerate(doc.rows_data):
                sender = str(row.get("sender") or row.get("Sender") or "")
                receiver = str(row.get("receiver") or row.get("Receiver") or "")
                amount = str(row.get("amount") or row.get("Amount") or "")
                timestamp = str(row.get("timestamp") or row.get("Timestamp") or "")

                ent_ids = []
                if sender in account_ents:
                    ent_ids.append(account_ents[sender])
                if receiver in account_ents:
                    ent_ids.append(account_ents[receiver])

                events.append({
                    "id": f"evt-tx-{doc.id}-{idx}",
                    "caseId": case_id,
                    "timestamp": timestamp if "T" in timestamp else f"2026-08-20T{timestamp}Z" if timestamp else doc.uploaded_at.isoformat() + "Z",
                    "type": "transfer",
                    "title": f"Transfer: INR {amount} from {sender} to {receiver}",
                    "entityIds": ent_ids,
                    "evidenceId": doc.id
                })

    # Sort events chronologically by timestamp
    events.sort(key=lambda x: x["timestamp"])
    return events
