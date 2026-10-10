"""
Test suite for Phase B4: Course-Grounded Tutor.

Verifies:
1. Supported question returns an answer with valid citations.
2. Citation metadata matches actual stored source and content_unit records.
3. Multi-source RAG combines evidence from multiple sources under one course.
4. Cross-course retrieval isolation is strictly enforced.
5. Source filter validation (cannot query source from another course).
6. Empty courses follow the NO_COURSE_MATERIAL contract.
7. Unsupported and out-of-scope questions return clean refusals with empty citations.
8. Non-existent courses return HTTP 404.
9. Upstream LLM provider failure returns HTTP 503 safely without fabricating answers.
10. Legacy /tutor/ask endpoint remains 100% backward-compatible.
11. Optional source filter scopes retrieval strictly to that source.
"""

import os
import sys
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

# Isolate database for B4 tests
TEST_DB_FILE = "test_b4_temp.db"
TEST_DATABASE_URL = f"sqlite:///{TEST_DB_FILE}"
os.environ["DATABASE_URL"] = TEST_DATABASE_URL

from app.db.database import Base, get_db
from app.models.course import Course
from app.models.source import Source
from app.models.content_unit import ContentUnit
from app.services.embedding_service import create_embeddings, serialize_embedding
from app.schemas.tutor import TutorStatus
from app.main import app

# Create test engine and session factory
test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False}
)

@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    import sqlite3
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

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


@pytest.fixture(scope="session", autouse=True)
def cleanup_temp_db_file():
    yield
    test_engine.dispose()
    if os.path.exists(TEST_DB_FILE):
        try:
            os.remove(TEST_DB_FILE)
        except OSError:
            pass


@pytest.fixture(autouse=True)
def setup_and_teardown_db():
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


# =====================================================================
# B4 Tests
# =====================================================================

def test_grounded_answer_with_valid_citations():
    """Verify supported questions return an answer with verified citations matching DB records."""
    db = TestingSessionLocal()
    course = Course(title="Physics 101")
    db.add(course)
    db.commit()

    source = Source(course_id=course.id, filename="ultrasonics.pdf", processing_status="completed")
    db.add(source)
    db.commit()

    text_sample = "The piezoelectric effect is the generation of electric charge in certain materials in response to applied mechanical stress."
    vec = create_embeddings([text_sample])[0]
    unit = ContentUnit(
        course_id=course.id,
        source_id=source.id,
        text=text_sample,
        page_number=2,
        embedding=serialize_embedding(vec)
    )
    db.add(unit)
    db.commit()
    unit_id = unit.id
    source_id = source.id
    course_id = course.id
    db.close()

    mock_llm_answer = "The piezoelectric effect occurs when mechanical stress applied to certain crystals generates an electric charge."

    with patch("app.services.course_tutor_service.llm_service.generate_response", return_value=mock_llm_answer):
        response = client.post(
            f"/courses/{course_id}/tutor/ask",
            json={"question": "What is the piezoelectric effect?"}
        )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == TutorStatus.ANSWERED.value
    assert data["answer"] == mock_llm_answer
    assert data["course_id"] == course_id
    assert len(data["citations"]) == 1

    citation = data["citations"][0]
    assert citation["content_unit_id"] == unit_id
    assert citation["source_id"] == source_id
    assert citation["filename"] == "ultrasonics.pdf"
    assert citation["page"] == 2
    assert citation["score"] > 0.5
    assert citation["content_type"] == "text" or citation["content_type"] == "pdf"


def test_multi_source_evidence_synthesis():
    """Verify tutor can retrieve and cite evidence across multiple uploaded sources in the course."""
    db = TestingSessionLocal()
    course = Course(title="Economics 101")
    db.add(course)
    db.commit()

    # Source 1: Microeconomics
    src1 = Source(course_id=course.id, filename="micro_foundations.pdf", processing_status="completed")
    # Source 2: Macroeconomics
    src2 = Source(course_id=course.id, filename="macro_principles.pdf", processing_status="completed")
    db.add_all([src1, src2])
    db.commit()

    t1 = "Opportunity cost represents the potential benefits an individual misses out on when choosing one alternative over another."
    t2 = "Fiscal policy involves government spending and taxation to influence national economic conditions."
    vecs = create_embeddings([t1, t2])

    u1 = ContentUnit(course_id=course.id, source_id=src1.id, text=t1, page_number=5, embedding=serialize_embedding(vecs[0]))
    u2 = ContentUnit(course_id=course.id, source_id=src2.id, text=t2, page_number=12, embedding=serialize_embedding(vecs[1]))
    db.add_all([u1, u2])
    db.commit()
    course_id = course.id
    s1_id, s2_id = src1.id, src2.id
    db.close()

    mock_answer = "Opportunity cost governs individual micro choices, while fiscal policy addresses national macroeconomic stability."

    with patch("app.services.course_tutor_service.llm_service.generate_response", return_value=mock_answer):
        response = client.post(
            f"/courses/{course_id}/tutor/ask",
            json={"question": "Compare opportunity cost and fiscal policy.", "top_k": 2}
        )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == TutorStatus.ANSWERED.value
    assert len(data["citations"]) == 2

    # Verify both sources are represented in citations
    cited_source_ids = {c["source_id"] for c in data["citations"]}
    assert cited_source_ids == {s1_id, s2_id}

    cited_filenames = {c["filename"] for c in data["citations"]}
    assert cited_filenames == {"micro_foundations.pdf", "macro_principles.pdf"}


def test_cross_course_retrieval_isolation():
    """Verify that materials from Course B are never retrieved or cited when asking in Course A."""
    db = TestingSessionLocal()
    course_a = Course(title="Course A - Astronomy")
    course_b = Course(title="Course B - Botany")
    db.add_all([course_a, course_b])
    db.commit()

    src_b = Source(course_id=course_b.id, filename="plants.pdf")
    db.add(src_b)
    db.commit()

    t_botany = "Photosynthesis is the biological process used by plants to convert light energy into chemical energy."
    vec_b = create_embeddings([t_botany])[0]
    u_b = ContentUnit(course_id=course_b.id, source_id=src_b.id, text=t_botany, page_number=1, embedding=serialize_embedding(vec_b))
    db.add(u_b)
    db.commit()
    c_a_id = course_a.id
    db.close()

    # Course A has no material -> must return no_course_material without leaking Botany
    response = client.post(
        f"/courses/{c_a_id}/tutor/ask",
        json={"question": "What is photosynthesis?"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == TutorStatus.NO_COURSE_MATERIAL.value
    assert len(data["citations"]) == 0


def test_source_filter_scoping_and_cross_course_rejection():
    """Verify that source_id filter restricts retrieval and rejects sources from other courses."""
    db = TestingSessionLocal()
    course1 = Course(title="Course 1")
    course2 = Course(title="Course 2")
    db.add_all([course1, course2])
    db.commit()

    src1_a = Source(course_id=course1.id, filename="c1_doc_a.pdf")
    src1_b = Source(course_id=course1.id, filename="c1_doc_b.pdf")
    src2 = Source(course_id=course2.id, filename="c2_doc.pdf")
    db.add_all([src1_a, src1_b, src2])
    db.commit()

    t1 = "Quantum entanglement is a physical phenomenon where particles become interconnected."
    t2 = "Superconductivity is a set of physical properties where electrical resistance vanishes."
    vecs = create_embeddings([t1, t2])
    u1 = ContentUnit(course_id=course1.id, source_id=src1_a.id, text=t1, page_number=1, embedding=serialize_embedding(vecs[0]))
    u2 = ContentUnit(course_id=course1.id, source_id=src1_b.id, text=t2, page_number=2, embedding=serialize_embedding(vecs[1]))
    db.add_all([u1, u2])
    db.commit()
    c1_id = course1.id
    s1_a_id = src1_a.id
    s2_id = src2.id
    db.close()

    # 1. Cross-course source filter must return HTTP 400
    bad_resp = client.post(
        f"/courses/{c1_id}/tutor/ask",
        json={"question": "Explain entanglement", "source_id": s2_id}
    )
    assert bad_resp.status_code == 400
    assert "does not belong to course" in bad_resp.json()["detail"]

    # 2. Scoped source filter to s1_a only
    mock_ans = "Entanglement means particles are interconnected."
    with patch("app.services.course_tutor_service.llm_service.generate_response", return_value=mock_ans):
        resp = client.post(
            f"/courses/{c1_id}/tutor/ask",
            json={"question": "Explain entanglement", "source_id": s1_a_id}
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == TutorStatus.ANSWERED.value
    assert len(data["citations"]) == 1
    assert data["citations"][0]["source_id"] == s1_a_id


def test_empty_course_outside_material_contract():
    """Verify that an empty course returns NO_COURSE_MATERIAL with zero citations."""
    db = TestingSessionLocal()
    course = Course(title="Empty Course")
    db.add(course)
    db.commit()
    course_id = course.id
    db.close()

    response = client.post(
        f"/courses/{course_id}/tutor/ask",
        json={"question": "What is the course schedule?"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == TutorStatus.NO_COURSE_MATERIAL.value
    assert "uploaded or indexed study material" in data["answer"].lower()
    assert data["citations"] == []


def test_out_of_scope_and_unsupported_questions():
    """Verify that unsupported questions return clean refusals with zero false citations."""
    db = TestingSessionLocal()
    course = Course(title="Differential Equations")
    db.add(course)
    db.commit()

    src = Source(course_id=course.id, filename="ode.pdf")
    db.add(src)
    db.commit()

    text_math = "First order differential equations can be solved using separation of variables or integrating factors."
    vec = create_embeddings([text_math])[0]
    unit = ContentUnit(course_id=course.id, source_id=src.id, text=text_math, page_number=1, embedding=serialize_embedding(vec))
    db.add(unit)
    db.commit()
    course_id = course.id
    db.close()

    # 1. Out-of-scope question with very low similarity (e.g. cookie recipe)
    # The low similarity check directly catches this without LLM invocation
    resp_unrelated = client.post(
        f"/courses/{course_id}/tutor/ask",
        json={"question": "What is the recipe for baking chocolate chip cookies with chocolate fudge?"}
    )
    assert resp_unrelated.status_code == 200
    d_unrelated = resp_unrelated.json()
    assert d_unrelated["status"] == TutorStatus.OUT_OF_SCOPE.value
    assert d_unrelated["citations"] == []

    # 2. Question with moderate similarity where LLM explicitly rejects due to lack of evidence
    mock_refusal = "I could not find this information in the provided course material."
    with patch("app.services.course_tutor_service.llm_service.generate_response", return_value=mock_refusal):
        resp_refusal = client.post(
            f"/courses/{course_id}/tutor/ask",
            json={"question": "How do you solve third order non-linear boundary value problems?"}
        )
    assert resp_refusal.status_code == 200
    d_refusal = resp_refusal.json()
    assert d_refusal["status"] in (TutorStatus.INSUFFICIENT_EVIDENCE.value, TutorStatus.OUT_OF_SCOPE.value)
    assert d_refusal["citations"] == []
    assert "could not find this information" in d_refusal["answer"].lower()


def test_missing_course_and_source_errors():
    """Verify appropriate HTTP 404 errors for non-existent courses or sources."""
    # 1. Non-existent course
    resp = client.post(
        "/courses/non-existent-course-uuid/tutor/ask",
        json={"question": "Hello?"}
    )
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()

    # 2. Existing course with non-existent source
    db = TestingSessionLocal()
    course = Course(title="Real Course")
    db.add(course)
    db.commit()
    course_id = course.id
    db.close()

    resp_bad_src = client.post(
        f"/courses/{course_id}/tutor/ask",
        json={"question": "Hello?", "source_id": "non-existent-source-uuid"}
    )
    assert resp_bad_src.status_code == 404
    assert "source" in resp_bad_src.json()["detail"].lower()


def test_llm_provider_failure_handling():
    """Verify that an unexpected upstream LLM failure returns HTTP 503 without fabricating answers."""
    db = TestingSessionLocal()
    course = Course(title="Computer Networks")
    db.add(course)
    db.commit()

    src = Source(course_id=course.id, filename="tcp.pdf")
    db.add(src)
    db.commit()

    text_net = "TCP provides reliable, ordered, and error-checked delivery of a stream of octets between applications."
    vec = create_embeddings([text_net])[0]
    unit = ContentUnit(course_id=course.id, source_id=src.id, text=text_net, page_number=3, embedding=serialize_embedding(vec))
    db.add(unit)
    db.commit()
    course_id = course.id
    db.close()

    # Mock LLM failure
    with patch("app.services.course_tutor_service.llm_service.generate_response", side_effect=RuntimeError("Google GenAI 503 Unavailable")):
        resp = client.post(
            f"/courses/{course_id}/tutor/ask",
            json={"question": "What guarantees does TCP provide?"}
        )

    assert resp.status_code == 503
    assert "temporarily unavailable" in resp.json()["detail"].lower()


def test_legacy_tutor_ask_endpoint_compatibility():
    """Verify that legacy POST /tutor/ask remains operational and returns expected structure."""
    from app.services.document_store import store_document

    sample_chunks = [
        {
            "id": "legacy_doc.pdf_page_1_chunk_0",
            "text": "The solar system consists of the Sun and the astronomical objects bound in orbit around it.",
            "source": {"type": "pdf", "filename": "legacy_doc.pdf", "page": 1}
        }
    ]
    store_document("legacy_doc.pdf", sample_chunks)

    mock_answer = "The solar system consists of the Sun and orbiting astronomical objects."

    with patch("app.services.rag_service.generate_response", return_value=mock_answer):
        resp = client.post(
            "/tutor/ask",
            json={"question": "What is the solar system?", "filename": "legacy_doc.pdf"}
        )

    assert resp.status_code == 200
    data = resp.json()
    assert "answer" in data
    assert "sources" in data
    assert len(data["sources"]) == 1
    assert data["sources"][0]["filename"] == "legacy_doc.pdf"

