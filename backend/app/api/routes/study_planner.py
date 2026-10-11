from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.study_planner import (
    StudyNextResponse,
    StudyPlanResponse,
)
from app.services import study_planner_service

router = APIRouter(
    prefix="/courses/{course_id}",
    tags=["Study Planner"],
)


@router.get(
    "/study-next",
    response_model=Optional[StudyNextResponse],
    summary="Get immediate highest-leverage recommendation",
)
def get_study_next(
    course_id: str,
    student_id: str = Query(default="default_student", description="Student identifier"),
    db: Session = Depends(get_db),
):
    """
    Returns the single highest-priority learning recommendation for the learner
    within the course. Evaluates prerequisite readiness, mastery deficits,
    blocker relationships, and retention decay.
    """
    plan_data = study_planner_service.calculate_study_plan_data(
        db=db,
        course_id=course_id,
        student_id=student_id,
    )
    return plan_data["top_recommendation"]


@router.get(
    "/study-plan",
    response_model=StudyPlanResponse,
    summary="Get complete prioritized course study plan",
)
def get_study_plan(
    course_id: str,
    student_id: str = Query(default="default_student", description="Student identifier"),
    db: Session = Depends(get_db),
):
    """
    Returns the full prioritized curriculum plan categorized into Focus Next,
    Ready to Learn, Blocked by Prerequisites, and Mastered concepts.
    """
    return study_planner_service.calculate_study_plan_data(
        db=db,
        course_id=course_id,
        student_id=student_id,
    )

