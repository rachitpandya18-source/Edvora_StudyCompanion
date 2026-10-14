"""
Regression tests for Critical Bug Fixes:
1. AI Tutor relevance & scope refusal (no context pollution for standalone queries, clean slide text, empty citations on refusal).
2. AI Tutor in-scope grounded answering for Chemistry.
3. Customize practice modal payload integration (question count, types, difficulty).
4. Study-Next recommendation contract consistency (concept_name, rationale, mastery_probability).
5. Topic question distribution (not repeating a single concept).
"""

import os
import uuid
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

TEST_DB_FILE = f"test_crit_temp_{uuid.uuid4().hex[:8]}.db"
TEST_DATABASE_URL = f"sqlite:///{TEST_DB_FILE}"

from app.db.database import Base, get_db
from app.models.user import User
from app.models.course import Course
from app.models.source import Source
from app.models.content_unit import ContentUnit
from app.models.topic import Topic
from app.models.concept import Concept
from app.core.security import get_password_hash, create_access_token
from app.services.embedding_service import create_embeddings, serialize_embedding
from app.main import app

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


@pytest.fixture(autouse=True)
def setup_and_teardown_db():
    app.dependency_overrides[get_db] = override_get_db
    with test_engine.connect() as conn:
        conn.exec_driver_sql("PRAGMA foreign_keys=ON")
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture(scope="session", autouse=True)
def cleanup_temp_db_file():
    yield
    if os.path.exists(TEST_DB_FILE):
        try:
            os.remove(TEST_DB_FILE)
        except OSError:
            pass


client = TestClient(app)


def _create_user(email: str, full_name: str):
    db = TestingSessionLocal()
    user = User(
        email=email,
        username=email.split("@")[0],
        hashed_password=get_password_hash("SecretPass123!"),
        full_name=full_name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token({"sub": str(user.id), "email": user.email})
    db.close()
    return user, token


def test_ai_tutor_rejects_out_of_scope_and_avoids_context_pollution():
    """
    Bug 1 Verification:
    In MFCS2 (Pigeonhole material), asking 'what is oxidation' after a Pigeonhole question
    must NOT be polluted with Pigeonhole context, must return out_of_scope/insufficient_evidence,
    and must return EMPTY citations.
    """
    user, token = _create_user("tutor_student@university.edu", "Tutor Student")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create MFCS2 course with Pigeonhole Principle content
    c_res = client.post("/courses", json={"title": "MFCS2 Discrete Mathematics"}, headers=headers)
    course_id = c_res.json()["id"]

    db = TestingSessionLocal()
    src = Source(course_id=course_id, filename="pigeonhole_lecture.pptx", source_type="pptx")
    db.add(src)
    db.commit()

    pigeonhole_text = (
        "Slide Title: Pigeonhole Principle\n"
        "If n items are put into m containers, with n > m, then at least one container must contain more than one item.\n"
        "Notes: This principle is widely used in combinatorics and graph theory proofs."
    )
    vecs = create_embeddings([pigeonhole_text])
    u = ContentUnit(
        course_id=course_id,
        source_id=src.id,
        text=pigeonhole_text,
        page_number=1,
        embedding=serialize_embedding(vecs[0]),
    )
    db.add(u)
    db.commit()
    db.close()

    # 2. Create a tutor thread
    t_res = client.post(
        f"/courses/{course_id}/tutor/threads",
        json={"title": "Discrete Math Study"},
        headers=headers,
    )
    thread_id = t_res.json()["id"]

    # 3. First turn: ask about Pigeonhole Principle (offline fallback synthesizer)
    with patch("app.services.llm_service.generate_response", side_effect=RuntimeError("LLM offline")):
        m1 = client.post(
            f"/courses/{course_id}/tutor/threads/{thread_id}/messages",
            json={"question": "What is the pigeonhole principle?"},
            headers=headers,
        )
    assert m1.status_code == 201
    m1_data = m1.json()
    assert m1_data["status"] == "answered"
    assert len(m1_data["citations"]) >= 1

    # 4. Second turn: ask completely out-of-scope question "what is oxidation"
    with patch("app.services.llm_service.generate_response", side_effect=RuntimeError("LLM offline")):
        m2 = client.post(
            f"/courses/{course_id}/tutor/threads/{thread_id}/messages",
            json={"question": "what is oxidation"},
            headers=headers,
        )
    assert m2.status_code == 201
    m2_data = m2.json()

    # Must be recognized as out of scope or insufficient evidence
    assert m2_data["status"] in ("out_of_scope", "insufficient_evidence")
    # Must NOT return Pigeonhole Principle as the explanation for oxidation
    assert "Pigeonhole" not in m2_data["content"]
    assert "at least one container" not in m2_data["content"]
    # Citations must be strictly empty on refusal
    assert len(m2_data["citations"]) == 0


def test_ai_tutor_answers_in_scope_chemistry_with_grounding():
    """
    Bug 1 Verification part 2:
    In Chemistry (Electrochemistry material), asking 'What is oxidation?'
    synthesizes a grounded explanation with authentic citations and clean text.
    """
    user, token = _create_user("chem_student@university.edu", "Chem Student")
    headers = {"Authorization": f"Bearer {token}"}

    c_res = client.post("/courses", json={"title": "Chemistry"}, headers=headers)
    course_id = c_res.json()["id"]

    db = TestingSessionLocal()
    src = Source(course_id=course_id, filename="Chemistry_Electrochemistry_Text_Notes.pdf", source_type="pdf")
    db.add(src)
    db.commit()

    electrochem_text = (
        "Oxidation is defined as the loss of electrons during a chemical reaction.\n"
        "In a galvanic cell, oxidation occurs at the anode where zinc metal loses electrons: Zn -> Zn2+ + 2e-.\n"
        "Reduction occurs at the cathode where copper ions gain electrons."
    )
    vecs = create_embeddings([electrochem_text])
    u = ContentUnit(
        course_id=course_id,
        source_id=src.id,
        text=electrochem_text,
        page_number=3,
        embedding=serialize_embedding(vecs[0]),
    )
    db.add(u)
    db.commit()
    db.close()

    t_res = client.post(
        f"/courses/{course_id}/tutor/threads",
        json={"title": "Electrochemistry Study"},
        headers=headers,
    )
    thread_id = t_res.json()["id"]

    with patch("app.services.llm_service.generate_response", side_effect=RuntimeError("LLM offline")):
        res = client.post(
            f"/courses/{course_id}/tutor/threads/{thread_id}/messages",
            json={"question": "What is oxidation?"},
            headers=headers,
        )
    assert res.status_code == 201
    data = res.json()
    assert data["status"] == "answered"
    assert "loss of electrons" in data["content"]
    assert len(data["citations"]) >= 1
    assert data["citations"][0]["filename"] == "Chemistry_Electrochemistry_Text_Notes.pdf"
    assert data["citations"][0]["page"] == 3


def test_customize_practice_payload_controls_generation():
    """
    Bug 2 Verification:
    Customize Practice sends question_types=['true_false'], question_count=4, difficulty='hard'.
    Verifies that backend respects count and type.
    """
    user, token = _create_user("practice_user@university.edu", "Practice User")
    headers = {"Authorization": f"Bearer {token}"}

    c_res = client.post("/courses", json={"title": "Computer Networks"}, headers=headers)
    course_id = c_res.json()["id"]

    db = TestingSessionLocal()
    t = Topic(course_id=course_id, title="Transport Layer", order_index=1)
    db.add(t)
    db.commit()

    topic_id = t.id
    c1 = Concept(course_id=course_id, topic_id=topic_id, name="TCP Handshake", description="Three-way handshake establishes connection", order_index=1)
    c2 = Concept(course_id=course_id, topic_id=topic_id, name="UDP Flow", description="Connectionless datagram delivery protocol", order_index=2)
    db.add_all([c1, c2])
    db.commit()
    db.close()

    # Request custom practice: true_false, count=4
    p_res = client.post(
        f"/courses/{course_id}/practice/generate",
        json={
            "mode": "adaptive",
            "topic_id": topic_id,
            "question_count": 4,
            "question_types": ["true_false"],
            "difficulty": "hard",
        },
        headers=headers,
    )
    assert p_res.status_code == 201
    data = p_res.json()
    questions = data["questions"]
    assert len(questions) == 4
    for q in questions:
        assert q["question_type"] == "true_false"
        assert q["options_json"] == ["True", "False"]


def test_topic_distribution_across_multiple_concepts():
    """
    Bug 2 & 5 Verification:
    When a topic with multiple concepts is selected, questions are distributed across concepts,
    not repeating a single concept.
    """
    user, token = _create_user("dist_user@university.edu", "Dist User")
    headers = {"Authorization": f"Bearer {token}"}

    c_res = client.post("/courses", json={"title": "Data Structures"}, headers=headers)
    course_id = c_res.json()["id"]

    db = TestingSessionLocal()
    t = Topic(course_id=course_id, title="Trees", order_index=1)
    db.add(t)
    db.commit()
    db.refresh(t)
    topic_id = t.id
    c1 = Concept(course_id=course_id, topic_id=topic_id, name="Binary Search Tree", order_index=1)
    c2 = Concept(course_id=course_id, topic_id=topic_id, name="AVL Tree", order_index=2)
    c3 = Concept(course_id=course_id, topic_id=topic_id, name="Red-Black Tree", order_index=3)
    db.add_all([c1, c2, c3])
    db.commit()
    db.close()

    p_res = client.post(
        f"/courses/{course_id}/practice/generate",
        json={
            "mode": "adaptive",
            "topic_id": topic_id,
            "question_count": 3,
        },
        headers=headers,
    )
    assert p_res.status_code == 201
    data = p_res.json()
    questions = data["questions"]
    concept_names = [q["concept_name"] or q["concept_title"] for q in questions]
    # Should include multiple distinct concepts
    assert len(set(concept_names)) >= 2


def test_study_next_schema_consistency():
    """
    Bug 4 Verification:
    Study-Next endpoint returns concept_name, topic_title, rationale, and mastery_probability,
    preventing UI from rendering raw UUIDs or undefined rationale notes.
    """
    user, token = _create_user("sn_user@university.edu", "SN User")
    headers = {"Authorization": f"Bearer {token}"}

    c_res = client.post("/courses", json={"title": "Operating Systems"}, headers=headers)
    course_id = c_res.json()["id"]

    db = TestingSessionLocal()
    t = Topic(course_id=course_id, title="Processes & Threads", order_index=1)
    db.add(t)
    db.commit()

    c1 = Concept(course_id=course_id, topic_id=t.id, name="Process Scheduling", order_index=1)
    db.add(c1)
    db.commit()
    db.close()

    sn_res = client.get(f"/courses/{course_id}/study-next", headers=headers)
    assert sn_res.status_code == 200
    rec = sn_res.json()
    assert rec is not None
    assert rec["concept_name"] == "Process Scheduling"
    assert rec["topic_title"] == "Processes & Threads"
    assert isinstance(rec["mastery_probability"], (int, float))
    assert rec["rationale"] is not None
    assert len(rec["rationale"]) > 0


def test_ai_tutor_answers_sock_drawer_pigeonhole_problem_in_mfcs2():
    """
    Verification of exact sock drawer problem in MFCS2:
    - User asks: 'A drawer contains 10 black socks and 10 white socks all mixed up in the dark.
      What is the minimum number of socks you must pull out blindly to guarantee that you have at least one matching pair (two socks of the same color)?'
    - Tutor must respond directly: 'The minimum is 3 socks. In the worst case...'
    - Must NOT output sequence definitions or a_n = 3n.
    - Citations must cite Pigeonhole Principle slides and be deduplicated.
    """
    user, token = _create_user("mfcs_student@university.edu", "MFCS Student")
    headers = {"Authorization": f"Bearer {token}"}

    c_res = client.post("/courses", json={"title": "MFCS2 Discrete Mathematics"}, headers=headers)
    course_id = c_res.json()["id"]

    db = TestingSessionLocal()
    src = Source(course_id=course_id, filename="Lecture 5 Pigeonhole Principle_ summation and sequence (1).pptx", source_type="pptx")
    db.add(src)
    db.commit()

    php_text = (
        "The Pigeonhole Principle\n"
        "If k is a positive integer and k + 1 objects are placed into k boxes, then at least one box contains two or more of the objects.\n"
        "Example: Among any group of 367 people, there must be at least two with the same birthday, because there are 366 possible birthdays.\n"
        "Example: How many cards must be selected from a standard deck of 52 cards to guarantee that at least three cards of the same suit are chosen?"
    )
    seq_text = (
        "Sequences and Summations\n"
        "A sequence is a discrete structure used to represent an ordered list.\n"
        "Example: {a_n} where a_n = 3n. The terms of this sequence are 3, 6, 9, 12, ...\n"
        "Arithmetic progression: a_n = a + nd."
    )

    vecs = create_embeddings([php_text, seq_text])
    u_php = ContentUnit(
        course_id=course_id,
        source_id=src.id,
        text=php_text,
        page_number=8,
        embedding=serialize_embedding(vecs[0]),
    )
    u_seq = ContentUnit(
        course_id=course_id,
        source_id=src.id,
        text=seq_text,
        page_number=18,
        embedding=serialize_embedding(vecs[1]),
    )
    db.add_all([u_php, u_seq])
    db.commit()
    db.close()

    t_res = client.post(
        f"/courses/{course_id}/tutor/threads",
        json={"title": "MFCS2 Study"},
        headers=headers,
    )
    thread_id = t_res.json()["id"]

    question = (
        "A drawer contains 10 black socks and 10 white socks all mixed up in the dark. "
        "What is the minimum number of socks you must pull out blindly to guarantee that you have at least one matching pair (two socks of the same color)?"
    )

    with patch("app.services.llm_service.generate_response", side_effect=RuntimeError("LLM offline")):
        res = client.post(
            f"/courses/{course_id}/tutor/threads/{thread_id}/messages",
            json={"question": question},
            headers=headers,
        )

    assert res.status_code == 201
    data = res.json()
    assert data["status"] == "answered"
    content = data["content"]

    # Direct answer first
    expected_prefix = (
        "The minimum is 3 socks. In the worst case, the first two socks are one black "
        "and one white. The third sock must be either black or white, so it matches one of the first two. "
        "Therefore, 3 socks guarantee a matching pair."
    )
    assert content.startswith(expected_prefix)
    assert "Pigeonhole Principle" in content

    # Must NOT output sequence definitions or a_n = 3n
    assert "a_n = 3n" not in content
    assert "Arithmetic progression" not in content
    assert "ordered list" not in content

    # Citations check
    assert len(data["citations"]) >= 1
    # Check deduplication and provenance
    pages = [c["page"] for c in data["citations"]]
    assert len(pages) == len(set(pages))
    # Must cite the Pigeonhole Principle slide (page 8)
    assert 8 in pages


def test_ai_tutor_multi_turn_independent_question_after_sequence():
    """
    Multi-turn test:
    Turn 1: Ask about sequences (a_n = 3n).
    Turn 2: Ask the sock drawer problem.
    Verifies that Turn 2 does not get topic-polluted with sequence definitions.
    """
    user, token = _create_user("turn_user@university.edu", "Turn User")
    headers = {"Authorization": f"Bearer {token}"}

    c_res = client.post("/courses", json={"title": "MFCS2 Discrete Mathematics 2"}, headers=headers)
    course_id = c_res.json()["id"]

    db = TestingSessionLocal()
    src = Source(course_id=course_id, filename="Lecture 5 Pigeonhole Principle_ summation and sequence (1).pptx", source_type="pptx")
    db.add(src)
    db.commit()

    php_text = (
        "The Pigeonhole Principle\n"
        "If k is a positive integer and k + 1 objects are placed into k boxes, then at least one box contains two or more of the objects."
    )
    seq_text = (
        "Sequences and Summations\n"
        "A sequence is a discrete structure used to represent an ordered list. For example, a_n = 3n."
    )

    vecs = create_embeddings([php_text, seq_text])
    u_php = ContentUnit(
        course_id=course_id,
        source_id=src.id,
        text=php_text,
        page_number=8,
        embedding=serialize_embedding(vecs[0]),
    )
    u_seq = ContentUnit(
        course_id=course_id,
        source_id=src.id,
        text=seq_text,
        page_number=18,
        embedding=serialize_embedding(vecs[1]),
    )
    db.add_all([u_php, u_seq])
    db.commit()
    db.close()

    t_res = client.post(
        f"/courses/{course_id}/tutor/threads",
        json={"title": "Multi-turn Math Thread"},
        headers=headers,
    )
    thread_id = t_res.json()["id"]

    # Turn 1: Ask about sequences
    with patch("app.services.llm_service.generate_response", side_effect=RuntimeError("LLM offline")):
        t1_res = client.post(
            f"/courses/{course_id}/tutor/threads/{thread_id}/messages",
            json={"question": "What is a sequence?"},
            headers=headers,
        )
    assert t1_res.status_code == 201

    # Turn 2: Ask the sock drawer problem
    question = (
        "A drawer contains 10 black socks and 10 white socks all mixed up in the dark. "
        "What is the minimum number of socks you must pull out blindly to guarantee that you have at least one matching pair (two socks of the same color)?"
    )
    with patch("app.services.llm_service.generate_response", side_effect=RuntimeError("LLM offline")):
        t2_res = client.post(
            f"/courses/{course_id}/tutor/threads/{thread_id}/messages",
            json={"question": question},
            headers=headers,
        )
    assert t2_res.status_code == 201
    t2_data = t2_res.json()
    assert t2_data["status"] == "answered"
    assert "The minimum is 3 socks" in t2_data["content"]
    assert "a_n = 3n" not in t2_data["content"]
    assert "ordered list" not in t2_data["content"]


def test_customize_practice_rejects_topic_without_eligible_concepts():
    """
    Bug 5 Verification:
    When a topic with 0 concepts is chosen in Customize Practice,
    the backend returns a clear HTTP 400 error stating no eligible concepts found.
    """
    user, token = _create_user("empty_topic_user@university.edu", "Empty Topic User")
    headers = {"Authorization": f"Bearer {token}"}

    c_res = client.post("/courses", json={"title": "Physics 101"}, headers=headers)
    course_id = c_res.json()["id"]

    db = TestingSessionLocal()
    t = Topic(course_id=course_id, title="Thermodynamics", order_index=1)
    db.add(t)
    db.commit()
    topic_id = t.id
    db.close()

    p_res = client.post(
        f"/courses/{course_id}/practice/generate",
        json={
            "mode": "adaptive",
            "topic_id": topic_id,
            "question_count": 5,
        },
        headers=headers,
    )
    assert p_res.status_code == 400
    detail = p_res.json()["detail"]
    assert "No eligible concepts found in selected topic 'Thermodynamics'" in detail
