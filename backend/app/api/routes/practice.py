from typing import Optional
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.api.deps import get_current_student_id, get_current_user
from app.models.user import User
from app.schemas.practice import (
    PracticeGenerateRequest,
    PracticeSessionResponse,
    PracticeConfigOptions,
)
from app.services import practice_service

router = APIRouter(
    prefix="/courses/{course_id}/practice",
    tags=["Practice"],
)


@router.post(
    "/generate",
    response_model=PracticeSessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Dynamically generate and launch an adaptive practice session",
)
def generate_practice(
    course_id: str,
    payload: PracticeGenerateRequest,
    current_user: Optional[User] = Depends(get_current_user),
    student_id: str = Depends(get_current_student_id),
    db: Session = Depends(get_db),
):
    """
    Generates a course-grounded practice session matching the requested mode
    (adaptive, quick, or mock_test), persists questions into the Assessment engine,
    initiates an active student attempt, and returns student-safe questions.
    """
    if current_user:
        payload.student_id = current_user.id
    elif payload.student_id:
        pass
    else:
        payload.student_id = student_id or "default_student"
    return practice_service.generate_practice_session(
        db=db,
        course_id=course_id,
        request=payload,
    )



@router.get(
    "/options",
    response_model=PracticeConfigOptions,
    status_code=status.HTTP_200_OK,
    summary="Get practice configuration options and recommended focus",
)
def get_practice_options(
    course_id: str,
    db: Session = Depends(get_db),
):
    """
    Returns available course topics, question types, difficulty options,
    and the highest-leverage concept recommended by the study planner.
    """
    return practice_service.get_practice_options(
        db=db,
        course_id=course_id,
    )

