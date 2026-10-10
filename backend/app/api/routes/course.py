from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload

from app.db.database import get_db
from app.models.course import Course
from app.models.source import Source
from app.schemas.course import (
    CourseCreate,
    CourseUpdate,
    CourseResponse,
    CourseListResponse
)
from app.schemas.source import (
    SourceCreate,
    SourceUpdate,
    SourceResponse
)

router = APIRouter(
    prefix="/courses",
    tags=["Courses"]
)


# =====================================================================
# Course CRUD
# =====================================================================

@router.post(
    "",
    response_model=CourseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new course"
)
def create_course(
    course_in: CourseCreate,
    db: Session = Depends(get_db)
):
    course = Course(
        title=course_in.title,
        description=course_in.description
    )
    db.add(course)
    db.commit()
    db.refresh(course)
    return course


@router.get(
    "",
    response_model=CourseListResponse,
    summary="List all courses"
)
def list_courses(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: Session = Depends(get_db)
):
    query = db.query(Course).options(joinedload(Course.sources))
    total = query.count()
    courses = query.offset(skip).limit(limit).all()
    return CourseListResponse(items=courses, total=total)


@router.get(
    "/{course_id}",
    response_model=CourseResponse,
    summary="Get a course by ID"
)
def get_course(
    course_id: str,
    db: Session = Depends(get_db)
):
    course = db.query(Course).options(
        joinedload(Course.sources)
    ).filter(Course.id == course_id).first()

    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Course with ID '{course_id}' not found."
        )
    return course


@router.put(
    "/{course_id}",
    response_model=CourseResponse,
    summary="Update a course by ID"
)
def update_course(
    course_id: str,
    course_in: CourseUpdate,
    db: Session = Depends(get_db)
):
    course = db.query(Course).options(
        joinedload(Course.sources)
    ).filter(Course.id == course_id).first()

    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Course with ID '{course_id}' not found."
        )

    if course_in.title is not None:
        course.title = course_in.title
    if course_in.description is not None:
        course.description = course_in.description

    db.commit()
    db.refresh(course)
    return course


@router.delete(
    "/{course_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a course and all associated sources"
)
def delete_course(
    course_id: str,
    db: Session = Depends(get_db)
):
    course = db.query(Course).filter(Course.id == course_id).first()

    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Course with ID '{course_id}' not found."
        )

    db.delete(course)
    db.commit()
    return {
        "message": f"Course '{course_id}' and all associated sources deleted successfully.",
        "course_id": course_id
    }


# =====================================================================
# Source endpoints (Course-scoped)
# =====================================================================

@router.post(
    "/{course_id}/sources",
    response_model=SourceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a source under a course"
)
def create_course_source(
    course_id: str,
    source_in: SourceCreate,
    db: Session = Depends(get_db)
):
    # Verify course exists
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Course with ID '{course_id}' not found."
        )

    source = Source(
        course_id=course_id,
        filename=source_in.filename,
        source_type=source_in.source_type,
        file_path=source_in.file_path,
        processing_status=source_in.processing_status
    )
    db.add(source)
    db.commit()
    db.refresh(source)
    return source


@router.get(
    "/{course_id}/sources",
    response_model=List[SourceResponse],
    summary="List all sources under a course"
)
def list_course_sources(
    course_id: str,
    db: Session = Depends(get_db)
):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Course with ID '{course_id}' not found."
        )

    sources = db.query(Source).filter(Source.course_id == course_id).all()
    return sources


@router.get(
    "/{course_id}/sources/{source_id}",
    response_model=SourceResponse,
    summary="Get a source under a course"
)
def get_course_source(
    course_id: str,
    source_id: str,
    db: Session = Depends(get_db)
):
    source = db.query(Source).filter(
        Source.id == source_id,
        Source.course_id == course_id
    ).first()

    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Source with ID '{source_id}' not found in course '{course_id}'."
        )
    return source


@router.delete(
    "/{course_id}/sources/{source_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a source under a course"
)
def delete_course_source(
    course_id: str,
    source_id: str,
    db: Session = Depends(get_db)
):
    source = db.query(Source).filter(
        Source.id == source_id,
        Source.course_id == course_id
    ).first()

    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Source with ID '{source_id}' not found in course '{course_id}'."
        )

    db.delete(source)
    db.commit()
    return {
        "message": f"Source '{source_id}' deleted successfully.",
        "source_id": source_id,
        "course_id": course_id
    }

