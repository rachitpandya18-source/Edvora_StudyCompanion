from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.api.deps import get_current_student_id, get_current_user
from app.models.user import User
from app.schemas.assessment import (
    AssessmentCreate,
    AssessmentSummary,
    AssessmentResponse,
    StartAttemptRequest,
    SaveDraftRequest,
    SubmitAttemptRequest,
    AssessmentAttemptResponse,
)
from app.services import assessment_service

router = APIRouter(
    prefix="/courses/{course_id}/assessments",
    tags=["Assessments"],
)


# ============================================================================
# Assessment Definitions
# ============================================================================

@router.post(
    "",
    response_model=AssessmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new assessment for a course",
)
def create_course_assessment(
    course_id: str,
    payload: AssessmentCreate,
    db: Session = Depends(get_db),
):
    """
    Create a persistent assessment (quiz, mock test, or mixed test)
    containing structured questions for a course.
    """
    assessment = assessment_service.create_assessment(
        db=db,
        course_id=course_id,
        data=payload,
    )
    return assessment_service.format_assessment_for_student(assessment)


@router.get(
    "",
    response_model=List[AssessmentSummary],
    summary="List all assessments for a course",
)
def list_course_assessments(
    course_id: str,
    db: Session = Depends(get_db),
):
    """
    List all assessments available in the specified course.
    """
    return assessment_service.list_assessments(db=db, course_id=course_id)


@router.get(
    "/{assessment_id}",
    response_model=AssessmentResponse,
    summary="Get assessment details and questions",
)
def get_course_assessment(
    course_id: str,
    assessment_id: str,
    db: Session = Depends(get_db),
):
    """
    Retrieve assessment details and questions for taking the assessment.
    Correct answers and explanations are securely omitted before attempt submission.
    """
    assessment = assessment_service.get_assessment(
        db=db,
        course_id=course_id,
        assessment_id=assessment_id,
    )
    return assessment_service.format_assessment_for_student(assessment)


@router.delete(
    "/{assessment_id}",
    summary="Delete an assessment",
)
def delete_course_assessment(
    course_id: str,
    assessment_id: str,
    db: Session = Depends(get_db),
):
    """
    Delete an assessment and all associated questions and attempts.
    """
    assessment_service.delete_assessment(
        db=db,
        course_id=course_id,
        assessment_id=assessment_id,
    )
    return {"message": f"Assessment '{assessment_id}' deleted successfully."}


# ============================================================================
# Assessment Attempt Lifecycle
# ============================================================================

@router.post(
    "/{assessment_id}/attempts",
    response_model=AssessmentAttemptResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start a new assessment attempt",
)
def start_assessment_attempt(
    course_id: str,
    assessment_id: str,
    payload: Optional[StartAttemptRequest] = None,
    current_user: Optional[User] = Depends(get_current_user),
    student_id: str = Depends(get_current_student_id),
    db: Session = Depends(get_db),
):
    """
    Initiate a new attempt on the assessment in 'in_progress' state.
    Uses authenticated student ID (or payload student_id in dev/test mode if allowed).
    """
    if current_user:
        effective_student_id = current_user.id
    elif payload and payload.student_id:
        effective_student_id = payload.student_id
    else:
        effective_student_id = student_id
    attempt = assessment_service.start_attempt(
        db=db,
        course_id=course_id,
        assessment_id=assessment_id,
        student_id=effective_student_id,
    )
    return assessment_service.format_attempt_view(attempt)


@router.get(
    "/{assessment_id}/attempts",
    response_model=List[AssessmentAttemptResponse],
    summary="List past attempts for an assessment",
)
def list_assessment_attempts(
    course_id: str,
    assessment_id: str,
    student_id: Optional[str] = Depends(get_current_student_id),
    db: Session = Depends(get_db),
):
    """
    Retrieve past attempts on this assessment.
    """
    attempts = assessment_service.list_attempts(
        db=db,
        course_id=course_id,
        assessment_id=assessment_id,
        student_id=student_id,
    )
    return [assessment_service.format_attempt_view(att) for att in attempts]



@router.get(
    "/{assessment_id}/attempts/{attempt_id}",
    response_model=AssessmentAttemptResponse,
    summary="Get attempt details or evaluated results",
)
def get_assessment_attempt(
    course_id: str,
    assessment_id: str,
    attempt_id: str,
    student_id: str = Depends(get_current_student_id),
    db: Session = Depends(get_db),
):
    """
    Retrieve an attempt. If in progress, evaluation keys remain hidden.
    If submitted, full results including score, feedback, and explanations are returned.
    Only the owning student can access this attempt.
    """
    attempt = assessment_service.get_attempt(
        db=db,
        course_id=course_id,
        assessment_id=assessment_id,
        attempt_id=attempt_id,
    )
    if attempt.student_id != student_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Attempt '{attempt_id}' not found for assessment '{assessment_id}'."
        )
    return assessment_service.format_attempt_view(attempt)


@router.patch(
    "/{assessment_id}/attempts/{attempt_id}/draft",
    response_model=AssessmentAttemptResponse,
    summary="Save draft answers without submitting",
)
@router.put(
    "/{assessment_id}/attempts/{attempt_id}/draft",
    response_model=AssessmentAttemptResponse,
    summary="Save draft answers without submitting (PUT)",
)
def save_draft_attempt_answers(
    course_id: str,
    assessment_id: str,
    attempt_id: str,
    payload: SaveDraftRequest,
    student_id: str = Depends(get_current_student_id),
    db: Session = Depends(get_db),
):
    """
    Persist student answers in-progress. Does not evaluate or lock the attempt.
    Only the owning student can edit draft answers.
    """
    attempt = assessment_service.get_attempt(
        db=db,
        course_id=course_id,
        assessment_id=assessment_id,
        attempt_id=attempt_id,
    )
    if attempt.student_id != student_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Attempt '{attempt_id}' not found for assessment '{assessment_id}'."
        )
    attempt = assessment_service.save_draft_answers(
        db=db,
        course_id=course_id,
        assessment_id=assessment_id,
        attempt_id=attempt_id,
        draft_answers=payload.answers,
    )
    return assessment_service.format_attempt_view(attempt)


@router.post(
    "/{assessment_id}/attempts/{attempt_id}/submit",
    response_model=AssessmentAttemptResponse,
    summary="Submit attempt and trigger deterministic evaluation",
)
def submit_assessment_attempt(
    course_id: str,
    assessment_id: str,
    attempt_id: str,
    payload: Optional[SubmitAttemptRequest] = None,
    student_id: str = Depends(get_current_student_id),
    db: Session = Depends(get_db),
):
    """
    Submit the assessment attempt. Evaluates all questions deterministically,
    locks the attempt against further modification, and returns the complete
    score breakdown, question-level correctness, feedback, and explanations.
    Submitting an already submitted attempt is idempotent.
    Only the owning student can submit their attempt.
    """
    attempt = assessment_service.get_attempt(
        db=db,
        course_id=course_id,
        assessment_id=assessment_id,
        attempt_id=attempt_id,
    )
    if attempt.student_id != student_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Attempt '{attempt_id}' not found for assessment '{assessment_id}'."
        )
    final_answers = payload.answers if payload else None
    attempt = assessment_service.submit_attempt(
        db=db,
        course_id=course_id,
        assessment_id=assessment_id,
        attempt_id=attempt_id,
        final_answers=final_answers,
    )
    return assessment_service.format_attempt_view(attempt)

