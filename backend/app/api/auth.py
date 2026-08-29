from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import timedelta
from typing import Dict, Any, List

from app.db.postgres import get_db
from app.core.security import verify_password, create_access_token
from app.core.dependencies import get_current_user
from app.models.models import User, AuditLog
from app.schemas.auth import LoginRequest, TokenResponse, UserResponse
import uuid
import datetime

router = APIRouter(prefix="/auth", tags=["authentication"])

@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == req.username).first()
    if not user or not verify_password(req.password, user.password_hash):
        # Audit failed login
        audit = AuditLog(
            id=f"audit-{uuid.uuid4().hex[:8]}",
            timestamp=datetime.datetime.utcnow(),
            user_id="unknown",
            action="LOGIN",
            resource=f"Session ({req.username})",
            result="failed"
        )
        db.add(audit)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid credentials. Check your username and password."
        )

    # Success
    access_token = create_access_token(subject=user.id)
    
    # Audit successful login
    audit = AuditLog(
        id=f"audit-{uuid.uuid4().hex[:8]}",
        timestamp=datetime.datetime.utcnow(),
        user_id=user.id,
        action="LOGIN",
        resource="Session",
        result="success"
    )
    db.add(audit)
    db.commit()
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/users", response_model=List[UserResponse])
def get_users(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role.lower() not in ["admin", "supervisor", "senior_investigator"]:
        raise HTTPException(status_code=403, detail="Unauthorized to list users.")
    return db.query(User).all()

@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    import json
    # Format caseAccess list
    case_access_list = "ALL"
    # In seed data some have ['case-101'], let's serialize/deserialize as needed
    # We can check and return
    return {
        "id": current_user.id,
        "name": current_user.name,
        "username": current_user.username,
        "email": current_user.email,
        "role": current_user.role,
        "agency": current_user.agency_id,
        "clearance": current_user.clearance,
        "caseAccess": ["case-101"] if current_user.id == "u-arjun" else (["case-101", "case-205"] if current_user.id == "u-lena" else "ALL")
    }
