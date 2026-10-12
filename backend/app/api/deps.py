import os
from typing import Optional
from fastapi import Depends, HTTPException, Header, Query, Request, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.user import User
from app.core.security import decode_access_token

# Explicit allowlist of non-production environments that permit test/dev identity fallback
ALLOWED_FALLBACK_ENVS = {"test", "testing", "development"}


def is_unauthenticated_fallback_allowed() -> bool:
    """
    Fail-closed environment check.
    Authentication is strictly required by default.
    Only explicit, normalized values in ('test', 'testing', 'development') allow fallback.
    Missing, unknown, or production values (e.g., 'production', 'prod', 'staging', unset)
    strictly fail-closed and enforce JWT authentication.
    """
    raw_env = os.getenv("ENVIRONMENT")
    if not raw_env:
        return False
    normalized = raw_env.strip().lower()
    return normalized in ALLOWED_FALLBACK_ENVS


def get_current_user(
    request: Request,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """
    Extract and verify the current authenticated User from the Authorization header.
    Fail-closed: If not running in an explicitly allowed test/dev environment,
    missing or invalid tokens immediately raise HTTP 401.
    """
    token = None
    if authorization:
        parts = authorization.strip().split(" ")
        if len(parts) == 2 and parts[0].lower() == "bearer":
            token = parts[1].strip()

    if token:
        try:
            payload = decode_access_token(token)
            user_id = payload.get("sub")
            if not user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token subject payload.",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authenticated user no longer exists.",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            return user
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid or expired authentication token: {exc}",
                headers={"WWW-Authenticate": "Bearer"},
            )

    # Fail-closed check: if unauthenticated fallback is NOT explicitly allowed, reject with 401
    if not is_unauthenticated_fallback_allowed():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return None


def get_current_student_id(
    request: Request,
    authorization: Optional[str] = Header(None),
    student_id: Optional[str] = Query(None, description="Legacy/dev fallback student identifier"),
    learner_id: Optional[str] = Query(None, description="Legacy/dev fallback learner identifier"),
    db: Session = Depends(get_db),
) -> str:
    """
    Resolve the verified student identity for learner-sensitive routes.
    - If a valid Bearer token is provided: derives student_id directly from the verified token sub.
    - If unauthenticated: fails closed (raises HTTP 401) unless explicitly in an allowed test/dev environment.
    - In allowed test/dev environments: falls back to query/request identity or 'default_student'.
    """
    user = get_current_user(request=request, authorization=authorization, db=db)
    if user:
        return user.id

    if not is_unauthenticated_fallback_allowed():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required for learner endpoints.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Non-production fallback for regression testing
    return student_id or learner_id or "default_student"
