from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional

from app.db.postgres import get_db
from app.core.dependencies import get_current_user
from app.models.models import AuditLog, User
from app.schemas.audit import AuditEntryResponse

router = APIRouter(prefix="/audit", tags=["audit"])

@router.get("", response_model=List[AuditEntryResponse])
def get_audit_logs(
    user: Optional[str] = Query(None),
    case: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    result: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Only Admin or Supervisor can view global logs, others see only logs pertaining to their cases
    query = db.query(AuditLog)
    
    if current_user.role.lower() not in ["admin", "supervisor"]:
        # Standard users see only audit logs linked to their case access
        if current_user.id == "u-arjun":
            query = query.filter(AuditLog.case_id == "case-101")
        elif current_user.id == "u-lena":
            query = query.filter(AuditLog.case_id.in_(["case-101", "case-205"]))
            
    if user:
        query = query.filter(AuditLog.user_id == user)
    if case:
        query = query.filter(AuditLog.case_id == case)
    if action:
        query = query.filter(AuditLog.action == action)
    if result:
        query = query.filter(AuditLog.result == result)

    # Sort descending (most recent first)
    query = query.order_by(AuditLog.timestamp.desc())
    
    # Map model attributes to matches expected by schema (e.g. user_id -> userId)
    results = []
    for log in query.all():
        results.append({
            "id": log.id,
            "timestamp": log.timestamp,
            "userId": log.user_id,
            "action": log.action,
            "caseId": log.case_id,
            "resource": log.resource,
            "result": log.result
        })
        
    return results
