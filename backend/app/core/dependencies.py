from typing import List, Generator, Optional
from fastapi import Depends, HTTPException, status, Header, Cookie
from sqlalchemy.orm import Session
import jwt

from app.core.config import settings
from app.core.security import ALGORITHM
from app.db.postgres import get_db
from app.models.models import User, Case

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

# Per-user case access overrides (demo RBAC matrix)
_USER_CASE_ACCESS: dict[str, list[str] | str] = {
    "u-mira": "ALL",
    "u-dev": "ALL",
    "u-admin": "ALL",
    "u-arjun": ["case-101"],
    "u-lena": ["case-101", "case-205"],
}


def get_accessible_case_ids(user: User, db: Session) -> list[str] | None:
    """Return list of accessible case IDs, or None if user can access all cases."""
    role = user.role.lower()
    if role in ("admin", "supervisor", "senior_investigator"):
        return None

    override = _USER_CASE_ACCESS.get(user.id)
    if override == "ALL":
        return None
    if isinstance(override, list):
        return override

    assigned = db.query(Case.id).filter(Case.assigned_to == user.id).all()
    return [c.id for c in assigned]


def verify_case_access(user: User, case_id: str, db: Session | None = None) -> bool:
    """Checks if a user is authorized to access a specific case."""
    role = user.role.lower()
    if role in ("admin", "supervisor", "senior_investigator"):
        return True

    override = _USER_CASE_ACCESS.get(user.id)
    if override == "ALL":
        return True
    if isinstance(override, list):
        return case_id in override

    if db is not None:
        case = db.query(Case).filter(Case.id == case_id).first()
        if case and case.assigned_to == user.id:
            return True
    else:
        from app.db.postgres import SessionLocal
        temp_db = SessionLocal()
        try:
            case = temp_db.query(Case).filter(Case.id == case_id).first()
            if case and case.assigned_to == user.id:
                return True
        finally:
            temp_db.close()

    return False

def check_clearance(user_clearance: str, required_clearance: str) -> bool:
    levels = ["RESTRICTED", "CONFIDENTIAL", "SECRET"]
    try:
        user_idx = levels.index(user_clearance.upper())
        req_idx = levels.index(required_clearance.upper())
        return user_idx >= req_idx
    except ValueError:
        return False
