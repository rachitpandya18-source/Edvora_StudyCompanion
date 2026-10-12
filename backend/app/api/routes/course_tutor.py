"""
FastAPI route endpoints for Course-Grounded Tutor and Multi-Turn Persistent Tutor Sessions.
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.api.deps import get_current_student_id, get_current_user
from app.models.user import User
from app.schemas.tutor import CourseTutorAskRequest, CourseTutorResponse
from app.schemas.tutor_session import (
    TutorThreadCreate,
    TutorMessageCreate,
    TutorThreadSummary,
    TutorThreadDetail,
    TutorMessageResponse,
)
from app.services.course_tutor_service import (
    answer_course_question,
    CourseNotFoundError,
    SourceNotFoundError,
    SourceCourseMismatchError,
    TutorProviderError,
)
from app.services import tutor_session_service

router = APIRouter(
    prefix="/courses",
    tags=["Course Tutor"]
)


# =====================================================================
# Single-Turn Endpoint (Preserved exactly for backward compatibility)
# =====================================================================

@router.post(
    "/{course_id}/tutor/ask",
    response_model=CourseTutorResponse,
    status_code=status.HTTP_200_OK,
    summary="Ask a grounded question in a specific course"
)
def ask_course_tutor(
    course_id: str,
    request: CourseTutorAskRequest,
    db: Session = Depends(get_db)
):
    """
    Ask a question grounded in the course's persistent materials.

    - Scopes evidence retrieval strictly to the course.
    - Synthesizes multi-source evidence when needed.
    - Supports optional source filtering.
    - Returns verified citations with actual provenance metadata.
    - Follows outside-material contract (answered, insufficient_evidence, out_of_scope, no_course_material).
    """
    try:
        response_data = answer_course_question(
            db=db,
            course_id=course_id,
            question=request.question,
            source_id=request.source_id,
            top_k=request.top_k,
        )
        return response_data
    except CourseNotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(err)
        )
    except SourceNotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(err)
        )
    except SourceCourseMismatchError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(err)
        )
    except TutorProviderError as err:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI Tutor service is temporarily unavailable. Please try again later."
        )
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(err)
        )


# =====================================================================
# Multi-Turn Persistent Tutor Thread Endpoints (Milestone B10)
# =====================================================================

@router.post(
    "/{course_id}/tutor/threads",
    response_model=TutorThreadSummary,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new persistent conversation thread with the AI Tutor",
)
def create_tutor_thread(
    course_id: str,
    payload: TutorThreadCreate,
    current_user: Optional[User] = Depends(get_current_user),
    student_id: str = Depends(get_current_student_id),
    db: Session = Depends(get_db),
):
    """
    Creates a new conversation thread scoped to the specified course and student.
    """
    if current_user:
        effective_student_id = current_user.id
    elif payload.student_id:
        effective_student_id = payload.student_id
    else:
        effective_student_id = student_id or "default_student"
    return tutor_session_service.create_tutor_thread(
        db=db,
        course_id=course_id,
        student_id=effective_student_id,
        title=payload.title,
    )


@router.get(
    "/{course_id}/tutor/threads",
    response_model=List[TutorThreadSummary],
    status_code=status.HTTP_200_OK,
    summary="List all persistent conversation threads for a student in this course",
)
def list_tutor_threads(
    course_id: str,
    student_id: Optional[str] = Depends(get_current_student_id),
    db: Session = Depends(get_db),
):
    """
    Returns all conversation threads owned by the student in chronological order.
    """
    effective_student_id = student_id or "default_student"
    return tutor_session_service.list_tutor_threads(
        db=db,
        course_id=course_id,
        student_id=effective_student_id,
    )


@router.get(
    "/{course_id}/tutor/threads/{thread_id}",
    response_model=TutorThreadDetail,
    status_code=status.HTTP_200_OK,
    summary="Get full message history of a persistent conversation thread",
)
def get_tutor_thread(
    course_id: str,
    thread_id: str,
    student_id: Optional[str] = Depends(get_current_student_id),
    db: Session = Depends(get_db),
):
    """
    Returns the thread metadata and full sequence of user and assistant messages with citations.
    """
    effective_student_id = student_id or "default_student"
    return tutor_session_service.get_tutor_thread(
        db=db,
        course_id=course_id,
        thread_id=thread_id,
        student_id=effective_student_id,
    )


@router.delete(
    "/{course_id}/tutor/threads/{thread_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a persistent conversation thread and all its messages",
)
def delete_tutor_thread(
    course_id: str,
    thread_id: str,
    student_id: Optional[str] = Depends(get_current_student_id),
    db: Session = Depends(get_db),
):
    """
    Permanently deletes the thread and cascades deletion to all contained messages.
    """
    effective_student_id = student_id or "default_student"
    tutor_session_service.delete_tutor_thread(
        db=db,
        course_id=course_id,
        thread_id=thread_id,
        student_id=effective_student_id,
    )
    return {
        "message": f"Tutor thread '{thread_id}' deleted successfully.",
        "thread_id": thread_id,
        "course_id": course_id,
    }


@router.post(
    "/{course_id}/tutor/threads/{thread_id}/messages",
    response_model=TutorMessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Post a question to a thread and generate a grounded assistant response",
)
def post_thread_message(
    course_id: str,
    thread_id: str,
    payload: TutorMessageCreate,
    current_user: Optional[User] = Depends(get_current_user),
    student_id: Optional[str] = Depends(get_current_student_id),
    db: Session = Depends(get_db),
):
    """
    Appends the student's question to the thread, performs contextual course retrieval
    using recent conversation history, generates a grounded response with authentic citations,
    persists both turns, and returns the assistant message.
    """
    if current_user:
        effective_student_id = current_user.id
    elif payload.student_id:
        effective_student_id = payload.student_id
    else:
        effective_student_id = student_id or "default_student"
    return tutor_session_service.post_thread_message(
        db=db,
        course_id=course_id,
        thread_id=thread_id,
        question=payload.question,
        student_id=effective_student_id,
        source_id=payload.source_id,
        top_k=payload.top_k,
    )

