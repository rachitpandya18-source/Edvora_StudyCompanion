import logging
from typing import Dict, Any, List
from sqlalchemy.orm import Session

from app.models.course import Course
from app.models.source import Source
from app.models.content_unit import ContentUnit
from app.services.pdf_service import extract_pdf_pages
from app.services.chunk_service import chunk_text
from app.services.embedding_service import (
    create_embeddings,
    serialize_embedding,
)

logger = logging.getLogger(__name__)


# =====================================================================
# Legacy Ingestion (Preserved for Phase 0 regression compatibility)
# =====================================================================

def ingest_pdf(file_path: str, filename: str) -> List[Dict[str, Any]]:
    """
    Extract a PDF page-by-page and convert it into
    chunks while preserving source information in memory.
    Preserved for Phase 0 test compatibility.
    """
    pages = extract_pdf_pages(file_path)
    chunks = []

    for page in pages:
        page_chunks = chunk_text(page["text"])
        for index, chunk in enumerate(page_chunks):
            chunks.append({
                "id": f"{filename}_page_{page['page_number']}_chunk_{index}",
                "text": chunk,
                "source": {
                    "type": "pdf",
                    "filename": filename,
                    "page": page["page_number"]
                }
            })

    return chunks


# =====================================================================
# Course-Aware Persistent Ingestion (Phase B2)
# =====================================================================

def ingest_pdf_to_course(
    db: Session,
    course_id: str,
    source_id: str,
    file_path: str,
    replace_existing: bool = True
) -> Dict[str, Any]:
    """
    Extract, chunk, embed, and persist a PDF's content units
    linked to an existing Course and Source.

    Transactional safety:
    - If extraction, embedding, or DB operations fail, previous
      content units are NOT deleted or corrupted.
    - On failure, source.processing_status is safely set to 'failed'.
    - On success, previous units for this source are cleanly replaced.
    """
    # 1. Validate Course and Source existence and alignment
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise ValueError(f"Course '{course_id}' not found.")

    source = db.query(Source).filter(Source.id == source_id).first()
    if not source:
        raise ValueError(f"Source '{source_id}' not found.")

    if source.course_id != course_id:
        raise ValueError(
            f"Source '{source_id}' belongs to course '{source.course_id}', "
            f"not requested course '{course_id}'."
        )

    # 2. Extract pages from PDF
    try:
        pages = extract_pdf_pages(file_path)
    except Exception as exc:
        logger.error(f"[INGESTION] Failed to extract PDF '{file_path}': {exc}")
        _mark_source_failed(db, source_id)
        raise ValueError(f"Failed to extract text from PDF: {exc}") from exc

    return _process_pages_to_course(
        db=db,
        course_id=course_id,
        source=source,
        pages=pages,
        file_path=file_path,
        replace_existing=replace_existing,
        media_type_label="PDF",
    )


def ingest_pptx_to_course(
    db: Session,
    course_id: str,
    source_id: str,
    file_path: str,
    replace_existing: bool = True
) -> Dict[str, Any]:
    """
    Extract, chunk, embed, and persist a PPTX presentation's slides
    linked to an existing Course and Source.
    """
    from app.services.pptx_service import extract_pptx_slides

    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise ValueError(f"Course '{course_id}' not found.")

    source = db.query(Source).filter(Source.id == source_id).first()
    if not source:
        raise ValueError(f"Source '{source_id}' not found.")

    if source.course_id != course_id:
        raise ValueError(
            f"Source '{source_id}' belongs to course '{source.course_id}', "
            f"not requested course '{course_id}'."
        )

    try:
        slides = extract_pptx_slides(file_path)
    except Exception as exc:
        logger.error(f"[INGESTION] Failed to extract slides from '{file_path}': {exc}")
        _mark_source_failed(db, source_id)
        raise ValueError(f"Failed to extract slides from presentation: {exc}") from exc

    return _process_pages_to_course(
        db=db,
        course_id=course_id,
        source=source,
        pages=slides,
        file_path=file_path,
        replace_existing=replace_existing,
        media_type_label="Presentation",
    )


def ingest_video_to_course(
    db: Session,
    course_id: str,
    source_id: str,
    file_path: str,
    replace_existing: bool = True
) -> Dict[str, Any]:
    """
    Extract, chunk, embed, and persist a video recording's segments or metadata
    linked to an existing Course and Source.
    """
    from app.services.video_service import extract_video_content

    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise ValueError(f"Course '{course_id}' not found.")

    source = db.query(Source).filter(Source.id == source_id).first()
    if not source:
        raise ValueError(f"Source '{source_id}' not found.")

    if source.course_id != course_id:
        raise ValueError(
            f"Source '{source_id}' belongs to course '{source.course_id}', "
            f"not requested course '{course_id}'."
        )

    try:
        segments = extract_video_content(file_path, source.filename)
    except Exception as exc:
        logger.error(f"[INGESTION] Failed to process video '{file_path}': {exc}")
        _mark_source_failed(db, source_id)
        raise ValueError(f"Failed to process video: {exc}") from exc

    return _process_pages_to_course(
        db=db,
        course_id=course_id,
        source=source,
        pages=segments,
        file_path=file_path,
        replace_existing=replace_existing,
        media_type_label="Video",
    )


def ingest_material_to_course(
    db: Session,
    course_id: str,
    source_id: str,
    file_path: str,
    source_type: str = "pdf",
    replace_existing: bool = True
) -> Dict[str, Any]:
    """Unified dispatcher for ingesting PDF, PPTX, or Video into a course."""
    st = source_type.lower()
    if st in ("ppt", "pptx"):
        return ingest_pptx_to_course(db, course_id, source_id, file_path, replace_existing)
    elif st in ("video", "mp4", "mov", "m4v", "webm"):
        return ingest_video_to_course(db, course_id, source_id, file_path, replace_existing)
    else:
        return ingest_pdf_to_course(db, course_id, source_id, file_path, replace_existing)


def _process_pages_to_course(
    db: Session,
    course_id: str,
    source: Source,
    pages: List[Dict[str, Any]],
    file_path: str,
    replace_existing: bool,
    media_type_label: str = "Document",
) -> Dict[str, Any]:
    source_id = source.id
    if not pages:
        logger.warning(f"[INGESTION] {media_type_label} '{file_path}' contained 0 readable pages/units.")
        _mark_source_failed(db, source_id)
        raise ValueError(f"{media_type_label} contained no readable pages or text.")

    prepared_units: List[Dict[str, Any]] = []
    unit_index = 0

    for page in pages:
        page_num = page["page_number"]
        page_text = page["text"]
        chunks = chunk_text(page_text)

        for chunk_str in chunks:
            if not chunk_str.strip():
                continue

            c_start = page_text.find(chunk_str) if page_text else None
            c_end = (c_start + len(chunk_str)) if (c_start is not None and c_start != -1) else None
            if c_start == -1:
                c_start, c_end = None, None

            prepared_units.append({
                "course_id": course_id,
                "source_id": source_id,
                "unit_index": unit_index,
                "content_type": "text",
                "text": chunk_str,
                "char_start": c_start,
                "char_end": c_end,
                "page_number": page_num,
                "metadata_json": {
                    "filename": source.filename,
                    "source_type": source.source_type,
                    "page": page_num,
                }
            })
            unit_index += 1

    if not prepared_units:
        logger.warning(f"[INGESTION] No non-empty chunks created for '{file_path}'.")
        _mark_source_failed(db, source_id)
        raise ValueError(f"Could not create any content units from the {media_type_label}.")

    try:
        texts_to_embed = [u["text"] for u in prepared_units]
        embeddings = create_embeddings(texts_to_embed)
    except Exception as exc:
        logger.error(f"[INGESTION] Embedding generation failed: {exc}")
        _mark_source_failed(db, source_id)
        raise RuntimeError(f"Embedding generation failed: {exc}") from exc

    new_content_units: List[ContentUnit] = []
    for item, emb_vec in zip(prepared_units, embeddings):
        serialized_vec = serialize_embedding(emb_vec)
        unit = ContentUnit(
            course_id=item["course_id"],
            source_id=item["source_id"],
            unit_index=item["unit_index"],
            content_type=item["content_type"],
            text=item["text"],
            char_start=item["char_start"],
            char_end=item["char_end"],
            page_number=item["page_number"],
            metadata_json=item["metadata_json"],
            embedding=serialized_vec,
        )
        new_content_units.append(unit)

    try:
        if replace_existing:
            db.query(ContentUnit).filter(
                ContentUnit.source_id == source_id
            ).delete(synchronize_session=False)

        db.add_all(new_content_units)
        source.processing_status = "completed"
        source.file_path = file_path
        db.commit()

        logger.info(
            f"[INGESTION] Successfully indexed source '{source_id}' in course '{course_id}': "
            f"{len(new_content_units)} content units created."
        )

        return {
            "course_id": course_id,
            "source_id": source_id,
            "filename": source.filename,
            "content_units_count": len(new_content_units),
            "page_count": len(pages),
            "status": "completed",
        }

    except Exception as exc:
        db.rollback()
        logger.error(f"[INGESTION] Database commit failed during ingestion: {exc}")
        _mark_source_failed(db, source_id)
        raise RuntimeError(f"Failed to persist content units to database: {exc}") from exc


def _mark_source_failed(db: Session, source_id: str) -> None:
    try:
        source = db.query(Source).filter(Source.id == source_id).first()
        if source:
            source.processing_status = "failed"
            db.commit()
    except Exception as exc:
        db.rollback()
        logger.error(f"[INGESTION] Could not record failed status for source '{source_id}': {exc}")