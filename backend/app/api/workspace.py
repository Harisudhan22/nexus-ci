import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from app.db.postgres import get_db
from app.core.dependencies import get_current_user, verify_case_access
from app.models.models import User, WorkspaceState

router = APIRouter(prefix="/workspace", tags=["workspace"])

class SaveWorkspaceRequest(BaseModel):
    case_id: str
    title: Optional[str] = "Default Workspace"
    selected_entity_ids: Optional[List[str]] = []
    graph_filters: Optional[Dict[str, Any]] = {}
    bookmarks: Optional[List[str]] = []
    notes: Optional[str] = ""

@router.post("/save")
def save_workspace_state(
    req: SaveWorkspaceRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Persists investigator workspace state in PostgreSQL."""
    if not verify_case_access(current_user, req.case_id, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    ws = db.query(WorkspaceState).filter(
        WorkspaceState.case_id == req.case_id,
        WorkspaceState.user_id == current_user.id
    ).first()

    if not ws:
        ws = WorkspaceState(
            id=f"ws-{req.case_id}-{current_user.id}",
            case_id=req.case_id,
            user_id=current_user.id,
            title=req.title or "Default Workspace",
            selected_entity_ids=req.selected_entity_ids or [],
            graph_filters=req.graph_filters or {},
            bookmarks=req.bookmarks or [],
            notes=req.notes or "",
            updated_at=datetime.datetime.utcnow()
        )
        db.add(ws)
    else:
        ws.title = req.title or ws.title
        ws.selected_entity_ids = req.selected_entity_ids or []
        ws.graph_filters = req.graph_filters or {}
        ws.bookmarks = req.bookmarks or []
        ws.notes = req.notes or ""
        ws.updated_at = datetime.datetime.utcnow()

    db.commit()
    db.refresh(ws)

    return {
        "status": "success",
        "workspaceId": ws.id,
        "caseId": ws.case_id,
        "title": ws.title,
        "updatedAt": ws.updated_at.isoformat()
    }

@router.get("/{case_id}")
def get_workspace_state(
    case_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieves saved investigator workspace state."""
    if not verify_case_access(current_user, case_id, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    ws = db.query(WorkspaceState).filter(
        WorkspaceState.case_id == case_id,
        WorkspaceState.user_id == current_user.id
    ).first()

    if not ws:
        return {
            "caseId": case_id,
            "title": "Default Workspace",
            "selectedEntityIds": [],
            "graphFilters": {},
            "bookmarks": [],
            "notes": ""
        }

    return {
        "workspaceId": ws.id,
        "caseId": ws.case_id,
        "title": ws.title,
        "selectedEntityIds": ws.selected_entity_ids,
        "graphFilters": ws.graph_filters,
        "bookmarks": ws.bookmarks,
        "notes": ws.notes,
        "updatedAt": ws.updated_at.isoformat()
    }
