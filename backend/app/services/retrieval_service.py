from typing import List, Dict, Any, Optional
import numpy as np
from sqlalchemy.orm import Session, joinedload

from app.models.content_unit import ContentUnit
from app.models.source import Source
from app.models.course import Course
from app.services.embedding_service import (
    create_embeddings,
    deserialize_embedding,
)


# =====================================================================
# Legacy In-Memory Retrieval (Preserved for Phase 0 compatibility)
# =====================================================================

def search_chunks(chunks: List[Dict[str, Any]], query: str, top_k: int = 3) -> List[Dict[str, Any]]:
    """
    Find chunks semantically most relevant to query from an in-memory chunk list.
    Preserved for Phase 0 regression tests.
    """
    if not chunks:
        return []

    chunk_texts = [chunk["text"] for chunk in chunks]

    # Create chunk embeddings
    chunk_embeddings = create_embeddings(chunk_texts)

    # Create query embedding
    query_embedding = create_embeddings([query])[0]

    # Calculate cosine similarity
    scores = np.dot(chunk_embeddings, query_embedding)

    # Highest similarity first
    ranked_indices = np.argsort(scores)[::-1]

    results = []
    for index in ranked_indices[:top_k]:
        result = chunks[index].copy()
        result["score"] = float(scores[index])
        results.append(result)

    return results


# =====================================================================
# Course-Scoped Persistent Retrieval (Phase B2)
# =====================================================================

def search_course_content(
    db: Session,
    course_id: str,
    query: str,
    top_k: int = 3,
    source_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Search persistently stored content units strictly within a course.

    Guarantees:
    - Never leaks or falls back to another course's content.
    - Reuses pre-computed binary embeddings from ContentUnit;
      NEVER regenerates stored chunk embeddings on query.
    - Emits citation-compatible structures matching legacy expectations
      for seamless downstream consumption by Tutor and Assessment services.
    - Returns [] safely when course has no indexed content.
    """
    if not course_id or not query or not query.strip():
        return []

    if top_k <= 0:
        return []

    # 1. Verify course exists
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise ValueError(f"Course '{course_id}' not found.")

    # 2. If source_id provided, verify it belongs to this course
    if source_id:
        src = db.query(Source).filter(Source.id == source_id).first()
        if not src:
            raise ValueError(f"Source '{source_id}' not found.")
        if src.course_id != course_id:
            raise ValueError(
                f"Source '{source_id}' does not belong to course '{course_id}'."
            )

    # 3. Query ContentUnits for this course with joined Source for metadata
    query_stmt = (
        db.query(ContentUnit)
        .options(joinedload(ContentUnit.source))
        .filter(ContentUnit.course_id == course_id)
        .filter(ContentUnit.embedding.isnot(None))
    )

    if source_id:
        query_stmt = query_stmt.filter(ContentUnit.source_id == source_id)

    content_units = query_stmt.all()

    if not content_units:
        return []

    # 4. Generate query embedding ONCE
    query_embeddings = create_embeddings([query.strip()])
    if query_embeddings is None or len(query_embeddings) == 0:
        return []
    query_vector = np.asarray(query_embeddings[0], dtype=np.float32)

    # 5. Extract and deserialize stored chunk vectors
    valid_units: List[ContentUnit] = []
    vector_list: List[np.ndarray] = []

    for unit in content_units:
        if not unit.embedding:
            continue
        try:
            vec = deserialize_embedding(unit.embedding)
            vector_list.append(vec)
            valid_units.append(unit)
        except Exception:
            # Skip corrupted vector without failing entire query
            continue

    if not valid_units or not vector_list:
        return []

    # 6. Stack into 2D matrix (num_units, 384) and compute cosine similarities via matrix multiplication
    vectors_matrix = np.vstack(vector_list)  # (N, 384)
    scores = np.dot(vectors_matrix, query_vector)  # (N,)

    # 7. Rank by highest similarity score
    ranked_indices = np.argsort(scores)[::-1]

    results = []
    for idx in ranked_indices[:top_k]:
        unit = valid_units[idx]
        score_val = float(scores[idx])

        filename = unit.source.filename if unit.source else ""
        results.append({
            "id": unit.id,
            "text": unit.text,
            "score": score_val,
            "source": {
                "type": unit.content_type or "pdf",
                "filename": filename,
                "page": unit.page_number,
                "source_id": unit.source_id,
                "course_id": unit.course_id,
                "unit_index": unit.unit_index,
            }
        })

    return results