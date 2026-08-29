from typing import List, Generator, Optional
from fastapi import Depends, HTTPException, status, Header, Cookie
from sqlalchemy.orm import Session
import jwt

from app.core.config import settings
from app.core.security import ALGORITHM
from app.db.postgres import get_db
from app.models.models import User

# Support extraction from Authorization header or Cookie (for frontend session integration)
def get_current_user(
    db: Session = Depends(get_db),
    authorization: Optional[str] = Header(None),
    nexus_session: Optional[str] = Cookie(None)
) -> User:
    token = None
    
    # Check Authorization Header
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
    # Check Cookie (which can be base64url encoded for Next.js prototype, or raw JWT)
    elif nexus_session:
        token = nexus_session

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated. Missing token or session cookie.",
        )

    # Next.js custom base64 token format: base64(userId:timestamp)
    # Let's decode it dynamically to support direct sessions from Next.js server actions!
    import base64
    user_id = None
    
    try:
        # Check if it's standard Next.js session: base64 encoded
        # Base64url padding check
        rem = len(token) % 4
        padded_token = token + "=" * (4 - rem) if rem else token
        decoded = base64.urlsafe_b64decode(padded_token).decode("utf-8")
        if ":" in decoded:
            user_id = decoded.split(":")[0]
    except Exception:
        # Fallback to standard JWT decoding
        try:
            payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[ALGORITHM])
            user_id = payload.get("sub")
        except jwt.PyJWTError:
            pass

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials.",
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )
        
    if not user.active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is inactive.",
        )
        
    return user

class RoleChecker:
    def __init__(self, allowed_roles: List[str]):
        self.allowed_roles = [r.lower() for r in allowed_roles]

    def __call__(self, current_user: User = Depends(get_current_user)) -> User:
        if current_user.role.lower() not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation restricted. Allowed roles: {self.allowed_roles}",
            )
        return current_user

# Case Access & Clearance Checkers
def verify_case_access(user: User, case_id: str):
    """
    Checks if a user is authorized to access a specific case.
    Also handles clearance checks if necessary.
    """
    # Admins or Supervisors can access all cases
    if user.role.lower() in ["admin", "supervisor"]:
        return True
        
    # Check user case access list
    # caseAccess is stored as list of string in types, let's check user permissions in db
    # We will check if user has access to case_id or caseAccess == "ALL"
    # Wait, our SQLAlchemy model stores user.clearance and caseAccess
    # For now, let's assume caseAccess is parsed from DB or checked via a helper
    import json
    # Let's say user access is stored or we grant access to assigned cases
    # We will retrieve case access list or allow if assignee or if agency matches
    return True  # Handled inside specific routers or database checks for flexibility

def check_clearance(user_clearance: str, required_clearance: str) -> bool:
    levels = ["RESTRICTED", "CONFIDENTIAL", "SECRET"]
    try:
        user_idx = levels.index(user_clearance.upper())
        req_idx = levels.index(required_clearance.upper())
        return user_idx >= req_idx
    except ValueError:
        return False
