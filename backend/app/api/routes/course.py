import os
import shutil
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_

from app.db.database import get_db
from app.api.deps import get_current_student_id, verify_course_owner
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
from app.services.ingestion_service import ingest_pdf_to_course, ingest_material_to_course

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
    student_id: str = Depends(get_current_student_id),
    db: Session = Depends(get_db)
):
    course = Course(
        title=course_in.title,
        description=course_in.description,
        owner_id=student_id,
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
    student_id: str = Depends(get_current_student_id),
    db: Session = Depends(get_db)
):
    query = (
        db.query(Course)
        .options(joinedload(Course.sources))
        .filter(or_(Course.owner_id == student_id, Course.owner_id.is_(None)))
    )
    total = query.count()
    courses = query.offset(skip).limit(limit).all()
    return CourseListResponse(items=courses, total=total)


@router.get(
    "/{course_id}",
    response_model=CourseResponse,
    summary="Get a course by ID"
)
def get_course(
    course: Course = Depends(verify_course_owner),
    db: Session = Depends(get_db)
):
    return course


@router.put(
    "/{course_id}",
    response_model=CourseResponse,
    summary="Update a course by ID"
)
def update_course(
    course_in: CourseUpdate,
    course: Course = Depends(verify_course_owner),
    db: Session = Depends(get_db)
):
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
    course: Course = Depends(verify_course_owner),
    db: Session = Depends(get_db)
):
    course_id = course.id
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
    course: Course = Depends(verify_course_owner),
    db: Session = Depends(get_db)
):
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
    course: Course = Depends(verify_course_owner),
    db: Session = Depends(get_db)
):
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
    course: Course = Depends(verify_course_owner),
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
    course: Course = Depends(verify_course_owner),
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

UPLOAD_BASE_DIR = Path(os.getenv("UPLOAD_DIR", "data/uploads"))


@router.post(
    "/{course_id}/materials/upload",
    response_model=MaterialUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a course material (PDF, PPTX, or Video) and index its content units"
)
def upload_course_material(
    course_id: str,
    file: UploadFile = File(...),
    course: Course = Depends(verify_course_owner),
    db: Session = Depends(get_db)
):
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename cannot be empty."
        )

    filename_lower = file.filename.lower()
    allowed_exts = {
        ".pdf": "pdf",
        ".pptx": "pptx",
        ".ppt": "pptx",
        ".mp4": "video",
        ".mov": "video",
        ".m4v": "video",
        ".webm": "video",
    }
    ext = Path(filename_lower).suffix
    if ext not in allowed_exts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Supported material formats: PDF (.pdf), Presentation (.pptx, .ppt), Video (.mp4, .mov, .m4v, .webm)."
        )

    source_type = allowed_exts[ext]

    # Collision-safe directory path per course
    course_upload_dir = UPLOAD_BASE_DIR / course_id
    course_upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = course_upload_dir / file.filename

    # Save uploaded bytes to disk
    try:
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save uploaded file: {exc}"
        )

    # Find or create Source record
    source = db.query(Source).filter(
        Source.course_id == course_id,
        Source.filename == file.filename
    ).first()

    if not source:
        source = Source(
            course_id=course_id,
            filename=file.filename,
            source_type=source_type,
            file_path=str(file_path),
            processing_status="processing"
        )
        db.add(source)
        db.commit()
        db.refresh(source)
    else:
        source.file_path = str(file_path)
        source.source_type = source_type
        source.processing_status = "processing"
        db.commit()
        db.refresh(source)

    # Run persistent ingestion pipeline
    try:
        result = ingest_material_to_course(
            db=db,
            course_id=course_id,
            source_id=source.id,
            file_path=str(file_path),
            source_type=source_type,
            replace_existing=True
        )

        return MaterialUploadResponse(
            message=f"{source_type.upper()} uploaded and indexed successfully into course.",
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
            detail=f"Failed to process and index material: {exc}"
        )


@router.get(
    "/{course_id}/materials/{source_id}/download",
    summary="Download or stream a course material file"
)
@router.get(
    "/{course_id}/materials/{source_id}/file",
    summary="Stream or view a course material file"
)
def download_course_material(
    course_id: str,
    source_id: str,
    course: Course = Depends(verify_course_owner),
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

    file_path = Path(source.file_path) if source.file_path else None
    if not file_path or not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Material file for '{source.filename}' was not found on server storage."
        )

    ext = file_path.suffix.lower()
    media_types = {
        ".pdf": "application/pdf",
        ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        ".ppt": "application/vnd.ms-powerpoint",
        ".mp4": "video/mp4",
        ".mov": "video/quicktime",
        ".webm": "video/webm",
        ".m4v": "video/x-m4v",
    }
    media_type = media_types.get(ext, "application/octet-stream")

    return FileResponse(
        path=str(file_path),
        filename=source.filename,
        media_type=media_type,
    )

