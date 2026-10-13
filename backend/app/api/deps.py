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


def is_course_mutation_request(request: Request) -> bool:
    """
    Determines if an HTTP request attempts to mutate or delete a course
    or its structural content (metadata, sources, curriculum topics/concepts, assessments).
    Student interactions (attempts, drafts, submissions) are learner-scoped interactions,
    not course-level structural modifications.
    """
    method = request.method.upper()
    path = request.url.path.lower()

    # Attempt-level endpoints are student learning interactions, not course structure mutations
    if "/attempts" in path:
        return False

    if method in ("PUT", "DELETE", "PATCH"):
        return True

    if method == "POST":
        mutation_segments = (
            "/sources",
            "/materials",
            "/topics",
            "/concepts",
            "/prerequisites",
            "/assessments",
        )
        for seg in mutation_segments:
            if seg in path:
                return True

    return False


def verify_course_owner(
    course_id: str,
    request: Request,
    student_id: str = Depends(get_current_student_id),
    db: Session = Depends(get_db),
):
    """
    Verify that the requested course exists and is authorized for the current student.
    - If course does not exist: raises HTTP 404
    - If course has an owner and owner_id != current student: raises HTTP 404 (prevent leaking existence)
    - If course has owner_id=None (unowned legacy course):
        * Read operations (GET) and student practice attempts are permitted.
        * Structural mutations (PUT, DELETE, adding topics/sources/assessments) are strictly
          denied (HTTP 403 Forbidden) for authenticated students until ownership is established.
    - Returns the verified Course model
    """
    from app.models.course import Course
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Course with ID '{course_id}' not found.",
        )
    if course.owner_id is not None and course.owner_id != student_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Course with ID '{course_id}' not found.",
        )
    if course.owner_id is None and is_course_mutation_request(request):
        # Prevent unauthorized modifications to unowned legacy courses
        if not is_unauthenticated_fallback_allowed() or student_id != "default_student":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Course '{course_id}' ownership is unassigned. Legacy unowned courses cannot be modified until ownership is established.",
            )
    return course
