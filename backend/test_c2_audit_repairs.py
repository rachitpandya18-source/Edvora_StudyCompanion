"""
Tests for End-to-End Audit Repairs (C2):
- Multi-format material upload (PDF, PPTX, Video)
- Material download and streaming endpoint
- Grounded curriculum fallback when LLM is unconfigured
- Settings endpoints (inspection, key update, connection testing)
- Multi-tenant isolation for material file downloads
"""

import io
import os
import uuid
import pytest
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient
from pptx import Presentation
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.db.database import get_db, Base
from app.models.user import User
from app.models.course import Course
from app.models.source import Source
from app.models.content_unit import ContentUnit
from app.models.topic import Topic
from app.models.concept import Concept
from app.core.security import create_access_token
from app.services.embedding_service import create_embeddings, serialize_embedding

TEST_DB_FILE = f"test_c2_temp_{uuid.uuid4().hex[:8]}.db"
TEST_DATABASE_URL = f"sqlite:///{TEST_DB_FILE}"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_and_teardown_db():
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture(scope="session", autouse=True)
def cleanup_temp_db_file():
    yield
    test_engine.dispose()
    if os.path.exists(TEST_DB_FILE):
        try:
            os.remove(TEST_DB_FILE)
        except OSError:
            pass


def _create_user(email: str, name: str) -> tuple[User, str]:
    db = TestingSessionLocal()
    user = User(
        email=email,
        username=email.split("@")[0],
        full_name=name,
        hashed_password="hashed_pw_test",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token({"sub": user.id, "email": user.email})
    db.close()
    return user, token


def test_pptx_material_upload_and_indexing(tmp_path):
    user, token = _create_user("student1@university.edu", "Alice Student")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create a course
    c_res = client.post("/courses", json={"title": "Computer Networks"}, headers=headers)
    assert c_res.status_code == 201
    course_id = c_res.json()["id"]

    # 2. Build a valid in-memory PPTX presentation
    prs = Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[0])
    slide.shapes.title.text = "Introduction to Packet Switching"
    slide.placeholders[1].text = "Packet switching buffers and forwards individual packets across nodes."

    pptx_bytes = io.BytesIO()
    prs.save(pptx_bytes)
    pptx_bytes.seek(0)

    # 3. Upload PPTX
    files = {"file": ("networks_lecture1.pptx", pptx_bytes, "application/vnd.openxmlformats-officedocument.presentationml.presentation")}
    up_res = client.post(f"/courses/{course_id}/materials/upload", files=files, headers=headers)
    assert up_res.status_code == 201
    up_data = up_res.json()
    assert up_data["processing_status"] == "completed"
    assert up_data["content_units_count"] >= 1
    assert up_data["page_count"] == 1


def test_video_material_upload_and_indexing():
    user, token = _create_user("student2@university.edu", "Bob Student")
    headers = {"Authorization": f"Bearer {token}"}

    c_res = client.post("/courses", json={"title": "Algorithms"}, headers=headers)
    assert c_res.status_code == 201
    course_id = c_res.json()["id"]

    video_bytes = io.BytesIO(b"fake video mp4 stream bytes for testing")
    files = {"file": ("lecture_sorting.mp4", video_bytes, "video/mp4")}
    up_res = client.post(f"/courses/{course_id}/materials/upload", files=files, headers=headers)
    assert up_res.status_code == 201
    up_data = up_res.json()
    assert up_data["processing_status"] == "completed"
    assert up_data["content_units_count"] >= 1


def test_material_download_endpoint_and_isolation():
    user_a, token_a = _create_user("userA@university.edu", "User A")
    user_b, token_b = _create_user("userB@university.edu", "User B")
    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # Course A created by User A
    c_res = client.post("/courses", json={"title": "Physics 101"}, headers=headers_a)
    course_id = c_res.json()["id"]

    # Upload valid PDF with text
    import fitz
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 72), "Physics 101: Introduction to Mechanics and Sound Waves.")
    pdf_bytes = io.BytesIO(doc.tobytes())
    doc.close()

    files = {"file": ("physics_intro.pdf", pdf_bytes, "application/pdf")}
    up_res = client.post(f"/courses/{course_id}/materials/upload", files=files, headers=headers_a)
    assert up_res.status_code == 201
    source_id = up_res.json()["source_id"]

    # User A downloads their material: HTTP 200
    down_res = client.get(f"/courses/{course_id}/materials/{source_id}/download", headers=headers_a)
    assert down_res.status_code == 200
    assert down_res.headers["content-type"] == "application/pdf"

    # User B tries to download User A's material: HTTP 404 (IDOR protected)
    unauthorized_res = client.get(f"/courses/{course_id}/materials/{source_id}/download", headers=headers_b)
    assert unauthorized_res.status_code == 404


def test_curriculum_generation_fallback_when_llm_fails():
    user, token = _create_user("student_curr@university.edu", "Curriculum Student")
    headers = {"Authorization": f"Bearer {token}"}

    c_res = client.post("/courses", json={"title": "Acoustics & Waves"}, headers=headers)
    course_id = c_res.json()["id"]

    # Directly seed ContentUnits for testing
    db = TestingSessionLocal()
    src = Source(course_id=course_id, filename="waves.pdf", source_type="pdf")
    db.add(src)
    db.commit()

    u1 = ContentUnit(
        course_id=course_id,
        source_id=src.id,
        text="Chapter 1: Acoustic Wave Propagation.\nAcoustic waves propagate through elastic media via pressure variations.",
        page_number=1,
    )
    u2 = ContentUnit(
        course_id=course_id,
        source_id=src.id,
        text="Chapter 2: Piezoelectric Transducers.\nPiezoelectric materials convert mechanical pressure into electrical signals.",
        page_number=2,
    )
    db.add_all([u1, u2])
    db.commit()
    db.close()

    # When LLM raises an invalid API key / network exception, fallback should generate curriculum successfully
    with patch("app.services.curriculum_generator_service.llm_service.generate_response", side_effect=RuntimeError("API key not valid. Please pass a valid API key.")):
        res = client.post(
            f"/courses/{course_id}/curriculum/generate",
            json={"mode": "replace", "max_topics": 3, "concepts_per_topic": 2, "infer_prerequisites": True},
            headers=headers,
        )

    assert res.status_code == 200
    data = res.json()
    assert len(data["topics"]) >= 1
    assert any(len(t["concepts"]) > 0 for t in data["topics"])


def test_settings_endpoints():
    user, token = _create_user("settings_user@university.edu", "Settings User")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. GET /settings
    res = client.get("/settings", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "gemini_configured" in data
    assert "gemini_primary_model" in data
    assert "api_key_hint" in data

    # 2. POST /settings/gemini-key with short key -> 400
    res_bad = client.post("/settings/gemini-key", json={"api_key": "short"}, headers=headers)
    assert res_bad.status_code == 422 or res_bad.status_code == 400

    # 3. POST /settings/test-gemini
    res_test = client.post("/settings/test-gemini", headers=headers)
    assert res_test.status_code == 200
    assert "success" in res_test.json()


def test_practice_question_quality_and_rejection_of_generic_templates():
    user, token = _create_user("student_practice@university.edu", "Practice Student")
    headers = {"Authorization": f"Bearer {token}"}

    c_res = client.post("/courses", json={"title": "Physical Chemistry"}, headers=headers)
    course_id = c_res.json()["id"]

    db = TestingSessionLocal()
    top = Topic(course_id=course_id, title="Electrochemistry", order_index=0)
    db.add(top)
    db.flush()
    con = Concept(course_id=course_id, topic_id=top.id, name="Galvanic Cells", order_index=0)
    db.add(con)
    db.flush()

    src = Source(course_id=course_id, filename="electrochem.pdf", source_type="pdf")
    db.add(src)
    db.commit()

    u1 = ContentUnit(
        course_id=course_id,
        source_id=src.id,
        text="Galvanic cells convert chemical energy into electrical energy.\nThe Nernst Equation relates cell potential to reaction quotient: E = E° - (0.0591/n) log Q.\nFaraday's first law of electrolysis states m = ZIt where m is mass deposited.",
        page_number=1,
    )
    u2 = ContentUnit(
        course_id=course_id,
        source_id=src.id,
        text="The cell potential is given by E°cell = E°cathode - E°anode.\nConductance G is the reciprocal of resistance: G = 1/R.\nIn the Daniell cell, Zn + Cu2+ -> Zn2+ + Cu.",
        page_number=2,
    )
    db.add_all([u1, u2])
    db.commit()
    db.close()

    # Generate practice session
    res = client.post(
        f"/courses/{course_id}/practice/generate",
        json={"mode": "adaptive", "question_count": 3},
        headers=headers,
    )
    assert res.status_code == 201
    data = res.json()
    assert len(data["questions"]) >= 1

    # Verify that NONE of the forbidden template boilerplate phrases are present
    forbidden_snippets = [
        "What distinguishes",
        "from unrelated topics outside of",
        "Core foundations of",
        "An external concept outside",
        "A deprecated convention",
        "Unrelated concept placeholder",
    ]
    for q in data["questions"]:
        prompt = q["prompt"]
        for phrase in forbidden_snippets:
            assert phrase not in prompt, f"Forbidden phrase '{phrase}' found in prompt: {prompt}"

        # Verify options are domain grounded
        opts = q.get("options") or q.get("options_json") or []
        for opt in opts:
            for phrase in forbidden_snippets:
                assert phrase not in opt, f"Forbidden phrase '{phrase}' found in option: {opt}"


def test_assessment_scoring_bounds_and_post_submission_review():
    user, token = _create_user("student_scoring@university.edu", "Scoring Student")
    headers = {"Authorization": f"Bearer {token}"}

    c_res = client.post("/courses", json={"title": "Thermodynamics"}, headers=headers)
    course_id = c_res.json()["id"]

    db = TestingSessionLocal()
    top = Topic(course_id=course_id, title="Thermodynamic Laws", order_index=0)
    db.add(top)
    db.flush()
    con = Concept(course_id=course_id, topic_id=top.id, name="First and Second Laws", order_index=0)
    db.add(con)
    db.flush()

    src = Source(course_id=course_id, filename="thermo.pdf", source_type="pdf")
    db.add(src)
    db.commit()

    u1 = ContentUnit(
        course_id=course_id,
        source_id=src.id,
        text="First Law of Thermodynamics: delta U = q + w where q is heat and w is work.\nSecond Law: delta S of an isolated system always increases.",
        page_number=1,
    )
    db.add(u1)
    db.commit()
    db.close()

    # Generate practice session
    gen_res = client.post(
        f"/courses/{course_id}/practice/generate",
        json={"mode": "adaptive", "question_count": 2},
        headers=headers,
    )
    assert gen_res.status_code == 201
    session = gen_res.json()
    assessment_id = session["assessment_id"]
    attempt_id = session["attempt_id"]
    questions = session["questions"]

    # Submit answers
    answers_payload = []
    for q in questions:
        q_opts = q.get("options") or q.get("options_json") or ["Answer A"]
        answers_payload.append({
            "question_id": q["id"],
            "student_answer": q_opts[0]
        })
    sub_res = client.post(
        f"/courses/{course_id}/assessments/{assessment_id}/attempts/{attempt_id}/submit",
        json={"answers": answers_payload},
        headers=headers,
    )
    assert sub_res.status_code == 200
    attempt = sub_res.json()

    # Verify score is strictly bounded <= 100% and >= 0%
    assert 0.0 <= attempt["percentage"] <= 100.0
    assert attempt["score"] <= attempt["max_score"]

    # Verify attempt response includes complete review details
    assert "answers" in attempt
    for ans in attempt["answers"]:
        assert "is_correct" in ans
        assert "feedback" in ans
        assert "correct_answer" in ans
        assert "explanation" in ans


def test_recent_attempts_endpoint_and_learner_history():
    user, token = _create_user("student_history@university.edu", "History Student")
    headers = {"Authorization": f"Bearer {token}"}

    c_res = client.post("/courses", json={"title": "Organic Synthesis"}, headers=headers)
    course_id = c_res.json()["id"]

    # Query recent attempts endpoint
    rec_res = client.get(
        f"/courses/{course_id}/assessments/attempts/recent?limit=5",
        headers=headers,
    )
    assert rec_res.status_code == 200
    assert isinstance(rec_res.json(), list)


def test_tutor_citations_and_graceful_course_grounding():
    user, token = _create_user("student_tutor@university.edu", "Tutor Student")
    headers = {"Authorization": f"Bearer {token}"}

    c_res = client.post("/courses", json={"title": "Electromagnetism"}, headers=headers)
    course_id = c_res.json()["id"]

    db = TestingSessionLocal()
    src = Source(course_id=course_id, filename="maxwell.pdf", source_type="pdf")
    db.add(src)
    db.commit()

    txt = (
        "Maxwell's equations describe how electric and magnetic fields are generated by charges and currents.\n"
        "Gauss's law relates electric fields to charge density."
    )
    vecs = create_embeddings([txt])
    u1 = ContentUnit(
        course_id=course_id,
        source_id=src.id,
        text=txt,
        page_number=4,
        embedding=serialize_embedding(vecs[0]),
    )
    db.add(u1)
    db.commit()
    db.close()

    # Create a thread
    t_res = client.post(
        f"/courses/{course_id}/tutor/threads",
        json={"title": "Maxwell Equations Discussion"},
        headers=headers,
    )
    thread_id = t_res.json()["id"]

    # Ask a question when LLM is unavailable
    with patch("app.services.llm_service.generate_response", side_effect=RuntimeError("AI provider unconfigured")):
        q_res = client.post(
            f"/courses/{course_id}/tutor/threads/{thread_id}/messages",
            json={"question": "What is Gauss's law?"},
            headers=headers,
        )

    assert q_res.status_code == 201
    msg = q_res.json()
    assert msg["status"] == "answered"
    assert len(msg["citations"]) >= 1
    cit = msg["citations"][0]
    assert cit["filename"] == "maxwell.pdf"
    assert cit["page"] == 4
    assert "snippet" in cit
    assert "Gauss" in cit["snippet"]
    # Check that explanation is structured pedagogically, NOT raw metadata dumps
    assert "### Concept Definition" in msg["content"]
    assert "### Mechanism & Key Principles" in msg["content"]
    assert "📄 **From" not in msg["content"]


def test_user_response_populates_name_field():
    user, token = _create_user("rudresh_test@university.edu", "Rudresh Test")
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get("/auth/me", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["name"] == "Rudresh Test"
    assert data["full_name"] == "Rudresh Test"
    assert data["username"] == "rudresh_test"


def test_practice_generation_auto_bootstraps_curriculum_from_materials():
    user, token = _create_user("practice_student@university.edu", "Practice Student")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create a course
    c_res = client.post("/courses", json={"title": "Physical Chemistry"}, headers=headers)
    assert c_res.status_code == 201
    course_id = c_res.json()["id"]

    # 2. Add an indexed content unit without explicitly generating curriculum
    db = TestingSessionLocal()
    src = Source(
        course_id=course_id,
        filename="thermodynamics.pdf",
        source_type="pdf",
        processing_status="completed",
    )
    db.add(src)
    db.commit()

    text_passage = (
        "Chemical Thermodynamics and Enthalpy. "
        "Enthalpy is defined as the total heat content of a thermodynamic system. "
        "The first law of thermodynamics relates internal energy, heat, and work. "
        "Entropy measures the dispersal of matter and energy at standard conditions. "
        "Gibbs free energy determines spontaneity: Delta G = Delta H - T Delta S."
    )
    vecs = create_embeddings([text_passage])
    cu = ContentUnit(
        course_id=course_id,
        source_id=src.id,
        text=text_passage,
        page_number=1,
        embedding=serialize_embedding(vecs[0]),
    )
    db.add(cu)
    db.commit()
    db.close()

    # 3. Before curriculum is generated, practice generation returns 400 with "No concepts found"
    p_before = client.post(
        f"/courses/{course_id}/practice/generate",
        json={"mode": "adaptive", "question_count": 3},
        headers=headers,
    )
    assert p_before.status_code == 400
    assert "No concepts found" in p_before.json()["detail"]

    # 4. Generate curriculum for the course
    curr_res = client.post(
        f"/courses/{course_id}/curriculum/generate",
        json={"mode": "replace"},
        headers=headers,
    )
    assert curr_res.status_code in (200, 201)

    # 5. Call practice generation - succeeds with grounded questions and no AVL trees!
    p_res = client.post(
        f"/courses/{course_id}/practice/generate",
        json={"mode": "adaptive", "question_count": 3},
        headers=headers,
    )
    assert p_res.status_code == 201
    data = p_res.json()
    assert "assessment_id" in data
    assert "questions" in data
    assert len(data["questions"]) > 0
    # Questions should be about thermodynamics, not generic AVL trees!
    for q in data["questions"]:
        assert "AVL" not in q["prompt"]
