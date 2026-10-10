import shutil
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
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
from app.schemas.content_unit import MaterialUploadResponse
from app.services.ingestion_service import ingest_pdf_to_course

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


# =====================================================================
# Material Upload & Ingestion (Course-scoped)
# =====================================================================

UPLOAD_BASE_DIR = Path("data/uploads")


@router.post(
    "/{course_id}/materials/upload",
    response_model=MaterialUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a material PDF to a course and index its content units"
)
def upload_course_material(
    course_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    # 1. Verify course exists
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Course with ID '{course_id}' not found."
        )

    # 2. Validate PDF format
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are supported for material upload."
        )

    # 3. Collision-safe directory path per course
    course_upload_dir = UPLOAD_BASE_DIR / course_id
    course_upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = course_upload_dir / file.filename

    # 4. Save uploaded bytes to disk
    try:
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save uploaded file: {exc}"
        )

    # 5. Find or create Source record
    source = db.query(Source).filter(
        Source.course_id == course_id,
        Source.filename == file.filename
    ).first()

    if not source:
        source = Source(
            course_id=course_id,
            filename=file.filename,
            source_type="pdf",
            file_path=str(file_path),
            processing_status="processing"
        )
        db.add(source)
        db.commit()
        db.refresh(source)
    else:
        source.file_path = str(file_path)
        source.processing_status = "processing"
        db.commit()
        db.refresh(source)

    # 6. Run persistent ingestion pipeline
    try:
        result = ingest_pdf_to_course(
            db=db,
            course_id=course_id,
            source_id=source.id,
            file_path=str(file_path),
            replace_existing=True
        )

        return MaterialUploadResponse(
            message="PDF uploaded and indexed successfully into course.",
            course_id=course_id,
            source_id=source.id,
            filename=source.filename,
            processing_status="completed",
            content_units_count=result["content_units_count"],
            page_count=result["page_count"]
        )

    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err)
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process and index PDF: {exc}"
        )

