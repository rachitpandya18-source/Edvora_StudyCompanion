"""
Test suite for Phase B6: Bayesian Knowledge Tracing (BKT).

Verifies:
1. Pure BKT Mathematics:
   - Correct Bayesian update matches exact analytical calculation (L0=0.1 -> L1=0.4000).
   - Incorrect Bayesian update matches exact analytical calculation (L0=0.5 -> L1=0.2000).
   - Monotonic learning progression over consecutive correct answers.
   - Clamping and boundary safety at L=0 and L=1 without division by zero.
   - Parameter validation (range [0, 1], P(G) + P(S) < 1.0 constraint).
2. Learner State Initialization & Persistence:
   - Initial learner state has prior probability P(L0) and 0 observations.
   - State persists across updates.
3. Learner & Concept Isolation:
   - Isolation between different students.
   - Isolation between different concepts.
4. Assessment Submission Integration:
   - Assessment submission triggers BKT updates for concept-mapped questions.
   - Unmapped questions (no concept_id) are skipped.
   - Unanswered questions are skipped without altering BKT.
   - Duplicate attempt submission is strictly idempotent and does not apply repeat updates.
5. Course Scoping & API Endpoints:
   - GET /courses/{course_id}/mastery returns all concepts in course.
   - GET /courses/{course_id}/mastery/{concept_id} returns specific concept.
   - POST /courses/{course_id}/mastery/{concept_id}/initialize resets state.
   - Non-existent course or cross-course concept returns HTTP 404.
6. Alembic Migration:
   - Migration b6c1d4e2f704 upgrade and downgrade back to a5e1c8d2b903.
"""

import os
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

# Isolate database for B6 tests
TEST_DB_FILE = "test_b6_temp.db"
TEST_DATABASE_URL = f"sqlite:///{TEST_DB_FILE}"
os.environ["DATABASE_URL"] = TEST_DATABASE_URL

from app.db.database import Base, get_db
from app.models.course import Course
from app.models.topic import Topic
from app.models.concept import Concept
from app.models.assessment import Assessment, Question, AssessmentAttempt, AttemptAnswer
from app.models.learner_mastery import LearnerConceptMastery
from app.services.bkt_service import (
    calculate_bkt_update,
    validate_bkt_parameters,
    DEFAULT_P_L0,
    DEFAULT_P_T,
    DEFAULT_P_G,
    DEFAULT_P_S,
)
from app.api.deps import get_current_student_id
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
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)
    app.dependency_overrides.pop(get_db, None)


# ============================================================================
# 1. Pure BKT Mathematics Unit Tests
# ============================================================================

def test_bkt_correct_answer_calculation():
    """
    Given: L0 = 0.10, T = 0.10, G = 0.20, S = 0.10
    Observation: Correct (C = 1)
    Bayes Update:
      num = 0.10 * 0.90 = 0.09
      denom = 0.09 + (0.90 * 0.20) = 0.27
      P(L0|correct) = 0.09 / 0.27 = 1/3 ~ 0.333333
    Transition:
      L1 = 1/3 + (1 - 1/3) * 0.10 = 0.333333 + 0.066667 = 0.4000
    """
    new_mastery = calculate_bkt_update(
        current_mastery=0.10,
        is_correct=True,
        p_t=0.10,
        p_g=0.20,
        p_s=0.10,
    )
    assert new_mastery == 0.4000


def test_bkt_incorrect_answer_calculation():
    """
    Given: L0 = 0.50, T = 0.10, G = 0.20, S = 0.10
    Observation: Incorrect (C = 0)
    Bayes Update:
      num = 0.50 * 0.10 = 0.05
      denom = 0.05 + (0.50 * 0.80) = 0.45
      P(L0|incorrect) = 0.05 / 0.45 = 1/9 ~ 0.111111
    Transition:
      L1 = 1/9 + (8/9) * 0.10 = 0.111111 + 0.088889 = 0.2000
    """
    new_mastery = calculate_bkt_update(
        current_mastery=0.50,
        is_correct=False,
        p_t=0.10,
        p_g=0.20,
        p_s=0.10,
    )
    assert new_mastery == 0.2000


def test_bkt_monotonic_increase_on_correct_sequence():
    """Verify that mastery monotonically increases with consecutive correct answers."""
    mastery = 0.10
    history = [mastery]
    for _ in range(5):
        mastery = calculate_bkt_update(
            current_mastery=mastery,
            is_correct=True,
            p_t=0.10,
            p_g=0.20,
            p_s=0.10,
        )
        history.append(mastery)

    for i in range(len(history) - 1):
        assert history[i + 1] > history[i]

    # After 5 correct answers from 0.10, student should have high mastery > 0.95
    assert history[-1] > 0.95


def test_bkt_bounds_and_edge_cases():
    """Verify that extreme initial masteries (0.0 and 1.0) stay within [0.0, 1.0]."""
    # At L=0, correct answer
    m_0_corr = calculate_bkt_update(0.0, True, p_t=0.1, p_g=0.2, p_s=0.1)
    assert 0.0 <= m_0_corr <= 1.0
    assert m_0_corr == 0.10  # posterior is 0, transition adds T=0.1

    # At L=0, incorrect answer
    m_0_inc = calculate_bkt_update(0.0, False, p_t=0.1, p_g=0.2, p_s=0.1)
    assert 0.0 <= m_0_inc <= 1.0
    assert m_0_inc == 0.10

    # At L=1, correct answer
    m_1_corr = calculate_bkt_update(1.0, True, p_t=0.1, p_g=0.2, p_s=0.1)
    assert m_1_corr == 1.0

    # At L=1, incorrect answer
    m_1_inc = calculate_bkt_update(1.0, False, p_t=0.1, p_g=0.2, p_s=0.1)
    assert m_1_inc == 1.0


def test_bkt_parameter_validation():
    """Verify that invalid BKT parameters raise ValueError."""
    # Probability out of bounds
    with pytest.raises(ValueError, match="P\\(L0\\) must be within"):
        validate_bkt_parameters(p_l0=-0.1, p_t=0.1, p_g=0.2, p_s=0.1)

    with pytest.raises(ValueError, match="P\\(T\\) must be within"):
        validate_bkt_parameters(p_l0=0.1, p_t=1.5, p_g=0.2, p_s=0.1)

    # Identifiability violation: P(G) + P(S) >= 1.0
    with pytest.raises(ValueError, match="Guess \\+ Slip .* must be < 1.0"):
        validate_bkt_parameters(p_l0=0.1, p_t=0.1, p_g=0.6, p_s=0.5)


# ============================================================================
# 2. Assessment Submission Updates & Idempotency
# ============================================================================

def test_assessment_submission_updates_mastery():
    """Verify that submitting an assessment updates BKT mastery for concept-mapped questions."""
    db = TestingSessionLocal()
    course = Course(title="Algorithms 101")
    db.add(course)
    db.flush()

    topic = Topic(course_id=course.id, title="Sorting")
    db.add(topic)
    db.flush()

    concept = Concept(course_id=course.id, topic_id=topic.id, name="Quicksort Partitioning")
    db.add(concept)
    db.commit()

    # Create assessment with a question mapped to the concept
    payload = {
        "title": "Quicksort Quiz",
        "questions": [
            {
                "question_type": "mcq",
                "concept_id": concept.id,
                "prompt": "What is the average time complexity of Quicksort?",
                "marks": 2.0,
                "options_json": ["O(N log N)", "O(N^2)", "O(N)", "O(log N)"],
                "correct_answer": "O(N log N)",
            }
        ],
    }
    create_resp = client.post(f"/courses/{course.id}/assessments", json=payload)
    assert create_resp.status_code == 201
    assessment = create_resp.json()
    q_id = assessment["questions"][0]["id"]

    # Start attempt
    app.dependency_overrides[get_current_student_id] = lambda: "student_charlie"
    start_resp = client.post(
        f"/courses/{course.id}/assessments/{assessment['id']}/attempts",
        json={"student_id": "student_charlie"},
    )
    attempt = start_resp.json()

    # Submit with correct answer
    submit_resp = client.post(
        f"/courses/{course.id}/assessments/{assessment['id']}/attempts/{attempt['id']}/submit",
        json={"answers": [{"question_id": q_id, "student_answer": "O(N log N)"}]},
    )
    assert submit_resp.status_code == 200

    # Verify learner mastery state was updated
    mastery_resp = client.get(
        f"/courses/{course.id}/mastery/{concept.id}?student_id=student_charlie"
    )
    assert mastery_resp.status_code == 200
    m_data = mastery_resp.json()
    assert m_data["student_id"] == "student_charlie"
    assert m_data["concept_id"] == concept.id
    assert m_data["observation_count"] == 1
    assert m_data["correct_count"] == 1
    # Starting from L0=0.10, after 1 correct answer it should be exactly 0.4000
    assert m_data["mastery_probability"] == 0.4000
    assert m_data["last_attempt_at"] is not None


def test_skipping_unmapped_and_unanswered_questions():
    """Verify that unmapped or unanswered questions do not alter BKT mastery."""
    db = TestingSessionLocal()
    course = Course(title="Discrete Math")
    db.add(course)
    db.flush()

    topic = Topic(course_id=course.id, title="Logic")
    db.add(topic)
    db.flush()

    concept = Concept(course_id=course.id, topic_id=topic.id, name="Truth Tables")
    db.add(concept)
    db.commit()

    # Assessment with:
    # 1. Unmapped question (concept_id = None)
    # 2. Mapped question left blank (unanswered)
    payload = {
        "title": "Logic Warmup",
        "questions": [
            {
                "question_type": "true_false",
                "prompt": "Is True AND False equal to False?",
                "marks": 1.0,
                "correct_answer": "True",
                "concept_id": None,  # Unmapped
            },
            {
                "question_type": "true_false",
                "prompt": "Is True OR False equal to True?",
                "marks": 1.0,
                "correct_answer": "True",
                "concept_id": concept.id,  # Mapped, but will be left unanswered
            },
        ],
    }
    assessment = client.post(f"/courses/{course.id}/assessments", json=payload).json()
    q_ids = [q["id"] for q in assessment["questions"]]

    # Start attempt
    app.dependency_overrides[get_current_student_id] = lambda: "student_dana"
    attempt = client.post(
        f"/courses/{course.id}/assessments/{assessment['id']}/attempts",
        json={"student_id": "student_dana"},
    ).json()

    # Submit answering ONLY the unmapped question (leave question 2 blank)
    submit_resp = client.post(
        f"/courses/{course.id}/assessments/{assessment['id']}/attempts/{attempt['id']}/submit",
        json={"answers": [{"question_id": q_ids[0], "student_answer": "True"}]},
    )
    assert submit_resp.status_code == 200

    # Verify concept mastery was NOT modified because question 2 was unanswered
    mastery_resp = client.get(
        f"/courses/{course.id}/mastery/{concept.id}?student_id=student_dana"
    )
    assert mastery_resp.status_code == 200
    m_data = mastery_resp.json()
    assert m_data["observation_count"] == 0
    assert m_data["mastery_probability"] == DEFAULT_P_L0


def test_idempotent_submission_prevents_duplicate_bkt_updates():
    """Verify that re-submitting an already-submitted attempt does NOT apply BKT twice."""
    db = TestingSessionLocal()
    course = Course(title="Operating Systems")
    db.add(course)
    db.flush()

    topic = Topic(course_id=course.id, title="Concurrency")
    db.add(topic)
    db.flush()

    concept = Concept(course_id=course.id, topic_id=topic.id, name="Deadlocks")
    db.add(concept)
    db.commit()

    payload = {
        "title": "Deadlock Quiz",
        "questions": [
            {
                "question_type": "true_false",
                "concept_id": concept.id,
                "prompt": "Mutual exclusion is one of Coffman's conditions.",
                "marks": 1.0,
                "correct_answer": "True",
            }
        ],
    }
    assessment = client.post(f"/courses/{course.id}/assessments", json=payload).json()
    q_id = assessment["questions"][0]["id"]

    app.dependency_overrides[get_current_student_id] = lambda: "student_eli"
    attempt = client.post(
        f"/courses/{course.id}/assessments/{assessment['id']}/attempts",
        json={"student_id": "student_eli"},
    ).json()

    # First submission
    client.post(
        f"/courses/{course.id}/assessments/{assessment['id']}/attempts/{attempt['id']}/submit",
        json={"answers": [{"question_id": q_id, "student_answer": "True"}]},
    )

    # Check mastery after 1st submit
    m1 = client.get(
        f"/courses/{course.id}/mastery/{concept.id}?student_id=student_eli"
    ).json()
    assert m1["observation_count"] == 1
    assert m1["mastery_probability"] == 0.4000

    # Second submission (idempotency check)
    re_resp = client.post(
        f"/courses/{course.id}/assessments/{assessment['id']}/attempts/{attempt['id']}/submit",
        json={"answers": [{"question_id": q_id, "student_answer": "True"}]},
    )
    assert re_resp.status_code == 200

    # Mastery must NOT have been updated again
    m2 = client.get(
        f"/courses/{course.id}/mastery/{concept.id}?student_id=student_eli"
    ).json()
    assert m2["observation_count"] == 1
    assert m2["mastery_probability"] == 0.4000


# ============================================================================
# 3. Learner & Concept Isolation Tests
# ============================================================================

def test_learner_and_concept_isolation():
    """Verify that mastery updates are strictly isolated across students and concepts."""
    db = TestingSessionLocal()
    course = Course(title="Linear Algebra")
    db.add(course)
    db.flush()

    topic = Topic(course_id=course.id, title="Vector Spaces")
    db.add(topic)
    db.flush()

    concept_a = Concept(course_id=course.id, topic_id=topic.id, name="Basis")
    concept_b = Concept(course_id=course.id, topic_id=topic.id, name="Dimension")
    db.add_all([concept_a, concept_b])
    db.commit()

    # Student 1 gets Concept A correct
    payload_a = {
        "title": "Basis Quiz",
        "questions": [
            {
                "question_type": "true_false",
                "concept_id": concept_a.id,
                "prompt": "A basis is linearly independent.",
                "marks": 1.0,
                "correct_answer": "True",
            }
        ],
    }
    ass_a = client.post(f"/courses/{course.id}/assessments", json=payload_a).json()
    app.dependency_overrides[get_current_student_id] = lambda: "student_1"
    att_1 = client.post(
        f"/courses/{course.id}/assessments/{ass_a['id']}/attempts",
        json={"student_id": "student_1"},
    ).json()
    client.post(
        f"/courses/{course.id}/assessments/{ass_a['id']}/attempts/{att_1['id']}/submit",
        json={"answers": [{"question_id": ass_a["questions"][0]["id"], "student_answer": "True"}]},
    )

    # Check Student 1 on Concept A (mastery = 0.4000)
    s1_a = client.get(f"/courses/{course.id}/mastery/{concept_a.id}?student_id=student_1").json()
    assert s1_a["mastery_probability"] == 0.4000
    assert s1_a["observation_count"] == 1

    # Check Student 2 on Concept A (still initial prior 0.10)
    app.dependency_overrides[get_current_student_id] = lambda: "student_2"
    s2_a = client.get(f"/courses/{course.id}/mastery/{concept_a.id}?student_id=student_2").json()
    assert s2_a["mastery_probability"] == DEFAULT_P_L0
    assert s2_a["observation_count"] == 0

    # Check Student 1 on Concept B (still initial prior 0.10)
    app.dependency_overrides[get_current_student_id] = lambda: "student_1"
    s1_b = client.get(f"/courses/{course.id}/mastery/{concept_b.id}?student_id=student_1").json()
    assert s1_b["mastery_probability"] == DEFAULT_P_L0
    assert s1_b["observation_count"] == 0
    app.dependency_overrides.pop(get_current_student_id, None)


# ============================================================================
# 4. Course Scoping & Mastery APIs
# ============================================================================

def test_course_mastery_list_and_scoping():
    """Verify listing all concepts in course and scoping enforcement."""
    db = TestingSessionLocal()
    course1 = Course(title="Course 1")
    course2 = Course(title="Course 2")
    db.add_all([course1, course2])
    db.flush()

    topic1 = Topic(course_id=course1.id, title="Topic 1")
    topic2 = Topic(course_id=course2.id, title="Topic 2")
    db.add_all([topic1, topic2])
    db.flush()

    c1 = Concept(course_id=course1.id, topic_id=topic1.id, name="C1")
    c2 = Concept(course_id=course1.id, topic_id=topic1.id, name="C2")
    c3_other = Concept(course_id=course2.id, topic_id=topic2.id, name="C3")
    db.add_all([c1, c2, c3_other])
    db.commit()

    # List mastery for course 1
    resp = client.get(f"/courses/{course1.id}/mastery?student_id=frank")
    assert resp.status_code == 200
    data = resp.json()
    assert data["course_id"] == course1.id
    assert len(data["masteries"]) == 2
    concept_names = [m["concept_name"] for m in data["masteries"]]
    assert "C1" in concept_names
    assert "C2" in concept_names
    assert "C3" not in concept_names

    # Accessing Concept 3 (belongs to course 2) through Course 1 returns 404
    cross_resp = client.get(f"/courses/{course1.id}/mastery/{c3_other.id}?student_id=frank")
    assert cross_resp.status_code == 404

    # Non-existent course returns 404
    non_resp = client.get(f"/courses/non-existent-course-id/mastery?student_id=frank")
    assert non_resp.status_code == 404


def test_initialize_concept_mastery_endpoint():
    """Verify POST /courses/{course_id}/mastery/{concept_id}/initialize endpoint."""
    db = TestingSessionLocal()
    course = Course(title="Statistics")
    db.add(course)
    db.flush()

    topic = Topic(course_id=course.id, title="Inference")
    db.add(topic)
    db.flush()

    concept = Concept(course_id=course.id, topic_id=topic.id, name="Hypothesis Testing")
    db.add(concept)
    db.commit()

    # Initialize with custom parameters
    init_payload = {
        "student_id": "grace",
        "p_l0": 0.25,
        "p_t": 0.15,
        "p_g": 0.20,
        "p_s": 0.05,
    }
    resp = client.post(
        f"/courses/{course.id}/mastery/{concept.id}/initialize",
        json=init_payload,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["mastery_probability"] == 0.25
    assert data["p_l0"] == 0.25
    assert data["p_t"] == 0.15
    assert data["observation_count"] == 0

    # Initialize with invalid parameters returns 400
    bad_payload = {
        "student_id": "grace",
        "p_g": 0.8,
        "p_s": 0.3,  # sum = 1.1 >= 1.0
    }
    bad_resp = client.post(
        f"/courses/{course.id}/mastery/{concept.id}/initialize",
        json=bad_payload,
    )
    assert bad_resp.status_code == 400


# ============================================================================
# 5. Alembic Migration Verification
# ============================================================================

def test_alembic_bkt_migration():
    """Verify that Alembic runs up to b6c1d4e2f704 and cleanly downgrades back to a5e1c8d2b903."""
    from alembic.config import Config
    from alembic import command

    alembic_cfg_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "alembic.ini")
    )
    alembic_cfg = Config(alembic_cfg_path)

    alembic_test_db = "test_alembic_b6_clean.db"
    if os.path.exists(alembic_test_db):
        try:
            os.remove(alembic_test_db)
        except OSError:
            pass

    alembic_url = f"sqlite:///{alembic_test_db}"
    alembic_cfg.set_main_option("sqlalchemy.url", alembic_url)

    try:
        # Upgrade to head (including b6c1d4e2f704)
        command.upgrade(alembic_cfg, "head")

        # Downgrade back to assessment engine migration a5e1c8d2b903
        command.downgrade(alembic_cfg, "a5e1c8d2b903")

        # Upgrade back to head
        command.upgrade(alembic_cfg, "head")
    finally:
        if os.path.exists(alembic_test_db):
            try:
                os.remove(alembic_test_db)
            except OSError:
                pass

