from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.learner_mastery import (
    LearnerMasteryInitRequest,
    LearnerConceptMasteryResponse,
    LearnerCourseMasteryListResponse,
)
from app.services import bkt_service

router = APIRouter(
    prefix="/courses/{course_id}/mastery",
    tags=["Learner Mastery"],
)


@router.get(
    "",
    response_model=LearnerCourseMasteryListResponse,
    summary="Get learner mastery across all concepts in a course",
)
def get_course_mastery(
    course_id: str,
    student_id: str = Query(default="default_student", description="Student identifier"),
    db: Session = Depends(get_db),
):
    """
    Retrieve current BKT-estimated mastery probabilities across all concepts
    in the specified course for the learner. If a concept has not yet been practiced,
    returns default initial prior knowledge state.
    """
    masteries = bkt_service.get_course_learner_masteries(
        db=db,
        course_id=course_id,
        student_id=student_id,
    )
    return {
        "course_id": course_id,
        "student_id": student_id,
        "masteries": masteries,
    }


@router.get(
    "/{concept_id}",
    response_model=LearnerConceptMasteryResponse,
    summary="Get learner mastery for a specific concept in a course",
)
def get_concept_mastery(
    course_id: str,
    concept_id: str,
    student_id: str = Query(default="default_student", description="Student identifier"),
    db: Session = Depends(get_db),
):
    """
    Retrieve current BKT-estimated mastery for a specific concept.
    Enforces course scoping: validates that the concept belongs to the specified course.
    """
    return bkt_service.get_concept_learner_mastery(
        db=db,
        course_id=course_id,
        concept_id=concept_id,
        student_id=student_id,
    )


@router.post(
    "/{concept_id}/initialize",
    response_model=LearnerConceptMasteryResponse,
    status_code=status.HTTP_200_OK,
    summary="Initialize or reset learner state for a concept",
)
def initialize_concept_mastery_state(
    course_id: str,
    concept_id: str,
    payload: Optional[LearnerMasteryInitRequest] = None,
    db: Session = Depends(get_db),
):
    """
    Explicitly initialize or reset learner state for a specific concept with default
    or custom BKT parameters.
    """
    student_id = payload.student_id if payload and payload.student_id else "default_student"
    p_l0 = payload.p_l0 if payload else None
    p_t = payload.p_t if payload else None
    p_g = payload.p_g if payload else None
    p_s = payload.p_s if payload else None

    return bkt_service.initialize_concept_mastery(
        db=db,
        course_id=course_id,
        concept_id=concept_id,
        student_id=student_id,
        p_l0=p_l0,
        p_t=p_t,
        p_g=p_g,
        p_s=p_s,
    )

