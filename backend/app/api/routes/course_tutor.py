"""
FastAPI route endpoints for Course-Grounded Tutor.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.tutor import CourseTutorAskRequest, CourseTutorResponse
from app.services.course_tutor_service import (
    answer_course_question,
    CourseNotFoundError,
    SourceNotFoundError,
    SourceCourseMismatchError,
    TutorProviderError,
)

router = APIRouter(
    prefix="/courses",
    tags=["Course Tutor"]
)


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

