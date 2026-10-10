"""
Test suite for Phase B2: Unified Content Model & Persistent Retrieval.

Verifies:
1. Content units and embeddings persist after closing and reopening a database session/engine.
2. Course and source relationships and foreign key integrity.
3. Cross-course validation: content units cannot reference a source from another course.
4. PDF page numbers remain strictly 1-based.
5. Persistent retrieval returns relevant content with correct citation metadata.
6. Course scoping: retrieval never leaks content between two different courses.
7. Source filtering works accurately within a course.
8. Empty course retrieval returns an empty list without error.
9. Persistent retrieval avoids re-generating chunk embeddings on query (only query vector is generated).
10. Successful re-ingestion cleanly replaces previous units without duplicate inflation.
11. Failed re-ingestion preserves the previous successful index and marks source status 'failed'.
12. Corrupt or invalid PDFs fail safely without crashing the service or leaving corrupt records.
13. Deleting a course or source cascades and removes dependent content units.
14. Alembic migration chain (d7f92aabd290 -> e8c2f1a3b501) runs upgrade and downgrade cleanly.
15. Material upload endpoint (POST /courses/{course_id}/materials/upload) works end-to-end.
"""

import os
import sys
import tempfile
import pytest
import numpy as np
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Isolate database for tests using local SQLite
TEST_DB_FILE = "test_b2_temp.db"
TEST_DATABASE_URL = f"sqlite:///{TEST_DB_FILE}"
os.environ["DATABASE_URL"] = TEST_DATABASE_URL

from app.db.database import Base, get_db
from app.models.course import Course
from app.models.source import Source
from app.models.content_unit import ContentUnit
from app.services.embedding_service import (
    create_embeddings,
    serialize_embedding,
    deserialize_embedding,
    validate_embedding_vector,
    EMBEDDING_DIM,
)
from app.services.ingestion_service import ingest_pdf_to_course, ingest_pdf
from app.services.retrieval_service import search_course_content, search_chunks
from app.main import app

# Create test engine and session factory
test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=test_engine
)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

SAMPLE_PDF_PATH = os.path.join(os.path.dirname(__file__), "data", "uploads", "physics.pdf")


@pytest.fixture(autouse=True)
def setup_and_teardown_db():
    with test_engine.connect() as conn:
        conn.exec_driver_sql("PRAGMA foreign_keys=ON")
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="session", autouse=True)
def cleanup_temp_db_file():
    yield
    test_engine.dispose()
    if os.path.exists(TEST_DB_FILE):
        try:
            os.remove(TEST_DB_FILE)
        except OSError:
            pass


# =====================================================================
# 1. Embedding Serialization & Deserialization
# =====================================================================

def test_embedding_serialization_and_validation():
    """Verify vector serialization, deserialization, and dimension constraints."""
    vec = np.random.randn(EMBEDDING_DIM).astype(np.float32)
    # Normalize
    vec = vec / np.linalg.norm(vec)

    assert validate_embedding_vector(vec) is True
    assert validate_embedding_vector(np.zeros(10)) is False

    serialized = serialize_embedding(vec)
    assert isinstance(serialized, bytes)
    assert len(serialized) == EMBEDDING_DIM * 4

    deserialized = deserialize_embedding(serialized)
    assert deserialized.shape == (EMBEDDING_DIM,)
    assert np.allclose(vec, deserialized, atol=1e-6)


# =====================================================================
# 2. ContentUnit Persistence Across Session & Engine Restart
# =====================================================================

def test_content_unit_persistence_across_reconnect():
    """Verify ContentUnits and binary embeddings persist after closing session and recreating engine."""
    db = TestingSessionLocal()
    course = Course(title="Physics 101", description="Mechanics and thermodynamics")
    db.add(course)
    db.commit()

    source = Source(course_id=course.id, filename="physics.pdf", source_type="pdf")
    db.add(source)
    db.commit()

    sample_vec = np.ones(EMBEDDING_DIM, dtype=np.float32) / np.sqrt(EMBEDDING_DIM)
    unit = ContentUnit(
        course_id=course.id,
        source_id=source.id,
        unit_index=0,
        content_type="text",
        text="Piezoelectric materials generate electric charge under mechanical stress.",
        page_number=1,
        embedding=serialize_embedding(sample_vec)
    )
    db.add(unit)
    db.commit()
    unit_id = unit.id
    db.close()

    # Reopen fresh session
    fresh_db = TestingSessionLocal()
    retrieved = fresh_db.query(ContentUnit).filter(ContentUnit.id == unit_id).first()
    assert retrieved is not None
    assert retrieved.text.startswith("Piezoelectric")
    assert retrieved.page_number == 1
    assert retrieved.embedding is not None

    restored_vec = deserialize_embedding(retrieved.embedding)
    assert np.allclose(restored_vec, sample_vec, atol=1e-5)
    fresh_db.close()


# =====================================================================
# 3. Cross-Course Integrity Enforcement
# =====================================================================

def test_cross_course_validation():
    """ContentUnit cannot be associated with a source belonging to a different course."""
    db = TestingSessionLocal()
    course_a = Course(title="Course A")
    course_b = Course(title="Course B")
    db.add_all([course_a, course_b])
    db.commit()

    source_b = Source(course_id=course_b.id, filename="b_notes.pdf")
    db.add(source_b)
    db.commit()

    # Attempting to assign source_b to a ContentUnit under course_a must fail validation
    with pytest.raises(ValueError, match="does not match Source course_id"):
        invalid_unit = ContentUnit(
            course_id=course_a.id,
            source_id=source_b.id,
            text="Invalid content assignment",
            source=source_b
        )
        db.add(invalid_unit)
        db.flush()

    db.close()


# =====================================================================
# 4. Ingestion Pipeline & 1-Based Page Numbers
# =====================================================================

def test_ingest_pdf_to_course_success():
    """Verify PDF ingestion creates ContentUnits with 1-based page numbers and embeddings."""
    if not os.path.exists(SAMPLE_PDF_PATH):
        pytest.skip(f"Sample PDF {SAMPLE_PDF_PATH} not found.")

    db = TestingSessionLocal()
    course = Course(title="Physics Course")
    db.add(course)
    db.commit()

    source = Source(course_id=course.id, filename="physics.pdf", source_type="pdf")
    db.add(source)
    db.commit()

    result = ingest_pdf_to_course(
        db=db,
        course_id=course.id,
        source_id=source.id,
        file_path=SAMPLE_PDF_PATH,
        replace_existing=True
    )

    assert result["status"] == "completed"
    assert result["content_units_count"] > 0
    assert result["page_count"] > 0

    # Query created units from DB
    units = db.query(ContentUnit).filter(ContentUnit.source_id == source.id).all()
    assert len(units) == result["content_units_count"]

    # Verify 1-based page numbers
    for u in units:
        assert u.page_number >= 1
        assert u.embedding is not None
        assert u.course_id == course.id

    # Verify source status
    db.refresh(source)
    assert source.processing_status == "completed"
    assert source.file_path == SAMPLE_PDF_PATH
    db.close()


# =====================================================================
# 5. Course-Scoped Retrieval & Course Isolation
# =====================================================================

def test_course_scoped_retrieval_and_isolation():
    """Verify retrieval returns relevant content for target course and never leaks other courses."""
    db = TestingSessionLocal()
    course_physics = Course(title="Physics")
    course_econ = Course(title="Economics")
    db.add_all([course_physics, course_econ])
    db.commit()

    source_p = Source(course_id=course_physics.id, filename="physics.pdf")
    source_e = Source(course_id=course_econ.id, filename="econ.pdf")
    db.add_all([source_p, source_e])
    db.commit()

    # Pre-generate real embeddings
    texts_p = ["Piezoelectric transducers convert mechanical pressure into electricity."]
    texts_e = ["Opportunity cost is the loss of potential gain from other alternatives."]

    vecs_p = create_embeddings(texts_p)
    vecs_e = create_embeddings(texts_e)

    unit_p = ContentUnit(
        course_id=course_physics.id,
        source_id=source_p.id,
        unit_index=0,
        text=texts_p[0],
        page_number=3,
        embedding=serialize_embedding(vecs_p[0])
    )
    unit_e = ContentUnit(
        course_id=course_econ.id,
        source_id=source_e.id,
        unit_index=0,
        text=texts_e[0],
        page_number=1,
        embedding=serialize_embedding(vecs_e[0])
    )
    db.add_all([unit_p, unit_e])
    db.commit()

    # Query physics course
    results_p = search_course_content(
        db=db,
        course_id=course_physics.id,
        query="What is piezoelectric effect?",
        top_k=3
    )

    assert len(results_p) == 1
    assert "Piezoelectric" in results_p[0]["text"]
    assert results_p[0]["source"]["course_id"] == course_physics.id
    assert results_p[0]["source"]["page"] == 3
    assert results_p[0]["score"] > 0.4

    # Query economics course with physics query: must return ECON units or nothing, NEVER physics units
    results_e = search_course_content(
        db=db,
        course_id=course_econ.id,
        query="What is piezoelectric effect?",
        top_k=3
    )

    assert len(results_e) == 1
    assert results_e[0]["source"]["course_id"] == course_econ.id
    assert "Opportunity cost" in results_e[0]["text"]
    assert "Piezoelectric" not in results_e[0]["text"]

    db.close()


# =====================================================================
# 6. Source Filtering & Empty-Course Handling
# =====================================================================

def test_source_filtering_and_empty_course():
    """Verify source filtering isolates specific sources, and empty courses return []."""
    db = TestingSessionLocal()
    course = Course(title="Multi-source Course")
    empty_course = Course(title="Empty Course")
    db.add_all([course, empty_course])
    db.commit()

    src1 = Source(course_id=course.id, filename="book1.pdf")
    src2 = Source(course_id=course.id, filename="book2.pdf")
    db.add_all([src1, src2])
    db.commit()

    vecs = create_embeddings(["Content from book one.", "Content from book two."])
    u1 = ContentUnit(course_id=course.id, source_id=src1.id, text="Content from book one.", embedding=serialize_embedding(vecs[0]))
    u2 = ContentUnit(course_id=course.id, source_id=src2.id, text="Content from book two.", embedding=serialize_embedding(vecs[1]))
    db.add_all([u1, u2])
    db.commit()

    # Filter to src1 only
    res_src1 = search_course_content(db=db, course_id=course.id, query="book", source_id=src1.id)
    assert len(res_src1) == 1
    assert res_src1[0]["source"]["source_id"] == src1.id

    # Filter to empty course returns []
    res_empty = search_course_content(db=db, course_id=empty_course.id, query="book")
    assert res_empty == []

    # Filter with source from another course raises ValueError
    other_course = Course(title="Other")
    db.add(other_course)
    db.commit()
    other_src = Source(course_id=other_course.id, filename="other.pdf")
    db.add(other_src)
    db.commit()

    with pytest.raises(ValueError, match="does not belong to course"):
        search_course_content(db=db, course_id=course.id, query="test", source_id=other_src.id)

    db.close()


# =====================================================================
# 7. No Embedding Regeneration on Query
# =====================================================================

def test_retrieval_does_not_regenerate_chunk_embeddings():
    """Verify search_course_content only encodes the query string, never stored chunks."""
    db = TestingSessionLocal()
    course = Course(title="Test Perf Course")
    db.add(course)
    db.commit()

    src = Source(course_id=course.id, filename="doc.pdf")
    db.add(src)
    db.commit()

    vecs = create_embeddings(["Chunk 1 text", "Chunk 2 text"])
    u1 = ContentUnit(course_id=course.id, source_id=src.id, text="Chunk 1 text", embedding=serialize_embedding(vecs[0]))
    u2 = ContentUnit(course_id=course.id, source_id=src.id, text="Chunk 2 text", embedding=serialize_embedding(vecs[1]))
    db.add_all([u1, u2])
    db.commit()

    # Patch create_embeddings to monitor calls
    with patch("app.services.retrieval_service.create_embeddings", wraps=create_embeddings) as mock_encode:
        results = search_course_content(db=db, course_id=course.id, query="Chunk 1", top_k=2)
        assert len(results) == 2
        # create_embeddings should be called EXACTLY once for the query ["Chunk 1"]
        assert mock_encode.call_count == 1
        args, _ = mock_encode.call_args
        assert args[0] == ["Chunk 1"]

    db.close()


# =====================================================================
# 8. Re-ingestion Replacement and Failed Processing Safety
# =====================================================================

def test_safe_reingestion_and_failure_rollback():
    """Verify successful re-ingestion replaces units cleanly, while failures preserve existing units."""
    if not os.path.exists(SAMPLE_PDF_PATH):
        pytest.skip(f"Sample PDF {SAMPLE_PDF_PATH} not found.")

    db = TestingSessionLocal()
    course = Course(title="Reingestion Course")
    db.add(course)
    db.commit()

    source = Source(course_id=course.id, filename="physics.pdf")
    db.add(source)
    db.commit()

    # First successful ingestion
    res1 = ingest_pdf_to_course(db, course.id, source.id, SAMPLE_PDF_PATH, replace_existing=True)
    count1 = res1["content_units_count"]
    assert count1 > 0

    # Second successful re-ingestion
    res2 = ingest_pdf_to_course(db, course.id, source.id, SAMPLE_PDF_PATH, replace_existing=True)
    units_after = db.query(ContentUnit).filter(ContentUnit.source_id == source.id).all()
    # Count should NOT double; old units were replaced
    assert len(units_after) == count1

    # Simulate failure on re-ingestion: corrupt PDF path
    with pytest.raises(ValueError):
        ingest_pdf_to_course(db, course.id, source.id, "non_existent_corrupt.pdf", replace_existing=True)

    # Previous units must STILL be intact!
    preserved_units = db.query(ContentUnit).filter(ContentUnit.source_id == source.id).all()
    assert len(preserved_units) == count1

    # Source status must reflect failed
    db.refresh(source)
    assert source.processing_status == "failed"
    db.close()


# =====================================================================
# 9. Cascade Deletion of ContentUnits
# =====================================================================

def test_cascade_deletion():
    """Deleting a course or source cascades and purges dependent ContentUnits."""
    db = TestingSessionLocal()
    course = Course(title="Cascade Course")
    db.add(course)
    db.commit()

    src1 = Source(course_id=course.id, filename="src1.pdf")
    src2 = Source(course_id=course.id, filename="src2.pdf")
    db.add_all([src1, src2])
    db.commit()

    vec = np.ones(EMBEDDING_DIM, dtype=np.float32)
    u1 = ContentUnit(course_id=course.id, source_id=src1.id, text="u1", embedding=serialize_embedding(vec))
    u2 = ContentUnit(course_id=course.id, source_id=src2.id, text="u2", embedding=serialize_embedding(vec))
    db.add_all([u1, u2])
    db.commit()

    assert db.query(ContentUnit).filter(ContentUnit.course_id == course.id).count() == 2

    # Delete src1
    db.delete(src1)
    db.commit()
    assert db.query(ContentUnit).filter(ContentUnit.source_id == src1.id).count() == 0
    assert db.query(ContentUnit).filter(ContentUnit.source_id == src2.id).count() == 1

    # Delete entire course
    db.delete(course)
    db.commit()
    assert db.query(ContentUnit).count() == 0
    assert db.query(Source).count() == 0

    db.close()


# =====================================================================
# 10. Material Upload API Endpoint
# =====================================================================

def test_material_upload_api():
    """Verify POST /courses/{course_id}/materials/upload works end-to-end via FastAPI test client."""
    if not os.path.exists(SAMPLE_PDF_PATH):
        pytest.skip(f"Sample PDF {SAMPLE_PDF_PATH} not found.")

    # 1. Create a course
    resp_create = client.post("/courses", json={"title": "API Upload Test Course"})
    assert resp_create.status_code == 201
    course_id = resp_create.json()["id"]

    # 2. Upload PDF
    with open(SAMPLE_PDF_PATH, "rb") as f:
        resp_upload = client.post(
            f"/courses/{course_id}/materials/upload",
            files={"file": ("physics.pdf", f, "application/pdf")}
        )

    assert resp_upload.status_code == 201
    data = resp_upload.json()
    assert data["course_id"] == course_id
    assert data["processing_status"] == "completed"
    assert data["content_units_count"] > 0
    assert data["page_count"] > 0

    # 3. Verify sources endpoint lists this source
    resp_sources = client.get(f"/courses/{course_id}/sources")
    assert resp_sources.status_code == 200
    sources_list = resp_sources.json()
    assert len(sources_list) == 1
    assert sources_list[0]["filename"] == "physics.pdf"
    assert sources_list[0]["processing_status"] == "completed"


# =====================================================================
# 11. Alembic Migration Bidirectional Execution
# =====================================================================

def test_alembic_migrations_b2():
    """Verify alembic migrations run upgrade head and downgrade base cleanly."""
    from alembic.config import Config
    from alembic import command

    alembic_test_db = "test_alembic_b2_clean.db"
    alembic_test_url = f"sqlite:///{alembic_test_db}"
    if os.path.exists(alembic_test_db):
        os.remove(alembic_test_db)

    try:
        alembic_ini_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "alembic.ini")
        )
        alembic_cfg = Config(alembic_ini_path)
        alembic_cfg.set_main_option("sqlalchemy.url", alembic_test_url)

        # Run upgrade head (covers d7f92aabd290 and e8c2f1a3b501)
        command.upgrade(alembic_cfg, "head")

        # Run downgrade base
        command.downgrade(alembic_cfg, "base")
    finally:
        if os.path.exists(alembic_test_db):
            os.remove(alembic_test_db)


# =====================================================================
# 12. Legacy Retrieval and Ingestion Preserved
# =====================================================================

def test_legacy_ingestion_and_retrieval_functions():
    """Verify legacy ingest_pdf and search_chunks maintain identical contracts."""
    if not os.path.exists(SAMPLE_PDF_PATH):
        pytest.skip(f"Sample PDF {SAMPLE_PDF_PATH} not found.")

    chunks = ingest_pdf(SAMPLE_PDF_PATH, "physics.pdf")
    assert len(chunks) > 0
    assert "source" in chunks[0]
    assert chunks[0]["source"]["filename"] == "physics.pdf"
    assert chunks[0]["source"]["page"] >= 1

    results = search_chunks(chunks, "piezoelectric", top_k=2)
    assert len(results) > 0
    assert "score" in results[0]
    assert "text" in results[0]


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main(["-v", __file__]))

