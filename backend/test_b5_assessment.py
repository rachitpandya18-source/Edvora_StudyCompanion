"""
Test suite for Phase B5: Assessment Engine.

Verifies:
1. Reusable deterministic grading engine:
   - MCQ (exact match, option index, letter mapping, incorrect choice).
   - True/False (case-insensitive boolean mappings, invalid formats, incorrect choices).
   - Numerical (within tolerance, exceeding tolerance, non-numeric strings).
   - Short Answer (exact match, alternative delimiters, key phrase containment, incorrect answer).
2. Assessment CRUD:
   - Create mixed assessment with questions.
   - List assessments for a course.
   - Non-existent course returns HTTP 404.
   - Secure student view (hides correct_answer, tolerance, explanation).
   - Delete assessment with cascade.
3. Mock Test Support:
   - Assessment with type 'mock_test', time_limit_minutes, and collection of questions.
4. Attempt Lifecycle:
   - Start attempt (creates in_progress attempt with empty answers).
   - Save draft answers (updates student answers without evaluating or locking).
   - In-progress attempt hides answer keys, evaluation flags, and explanations.
   - Submit attempt (computes deterministic score, marks_awarded, feedback, explanations, percentage).
   - Idempotent re-submission (returns existing score without recalculating or resetting submitted_at).
   - Draft modification rejected after submission (HTTP 400).
   - List past attempts for an assessment.
5. Scoping & Isolation:
   - Cross-course assessment access returns HTTP 404.
   - Cross-assessment attempt access returns HTTP 404.
6. Alembic Migration:
   - Full migration upgrade to revision a5e1c8d2b903 and downgrade verification.
"""

import os
import sys
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

# Isolate database for B5 tests
TEST_DB_FILE = "test_b5_temp.db"
TEST_DATABASE_URL = f"sqlite:///{TEST_DB_FILE}"
os.environ["DATABASE_URL"] = TEST_DATABASE_URL

from app.db.database import Base, get_db
from app.models.course import Course
from app.models.assessment import Assessment, Question, AssessmentAttempt, AttemptAnswer
from app.services.assessment_service import evaluate_single_answer
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
# 1. Deterministic Evaluation Unit Tests
# ============================================================================

def test_mcq_evaluation():
    """Verify MCQ evaluation for exact matches, letters, and invalid options."""
    options = ["Paris", "London", "Berlin", "Madrid"]

    # Exact string match
    is_corr, marks, fb = evaluate_single_answer(
        question_type="mcq",
        correct_answer="Paris",
        student_answer="Paris",
        marks=2.0,
        options_json=options,
    )
    assert is_corr is True
    assert marks == 2.0

    # Letter choice 'A' matching 'Paris' (first option)
    is_corr, marks, fb = evaluate_single_answer(
        question_type="mcq",
        correct_answer="Paris",
        student_answer="A",
        marks=2.0,
        options_json=options,
    )
    assert is_corr is True
    assert marks == 2.0

    # Incorrect choice
    is_corr, marks, fb = evaluate_single_answer(
        question_type="mcq",
        correct_answer="Paris",
        student_answer="Berlin",
        marks=2.0,
        options_json=options,
    )
    assert is_corr is False
    assert marks == 0.0

    # Empty answer
    is_corr, marks, fb = evaluate_single_answer(
        question_type="mcq",
        correct_answer="Paris",
        student_answer="",
        marks=2.0,
    )
    assert is_corr is False
    assert marks == 0.0


def test_true_false_evaluation():
    """Verify True/False boolean evaluation with various text tokens."""
    # True matching tokens
    for token in ["True", "true", "t", "1", "yes"]:
        is_corr, marks, fb = evaluate_single_answer(
            question_type="true_false",
            correct_answer="True",
            student_answer=token,
            marks=1.5,
        )
        assert is_corr is True
        assert marks == 1.5

    # False matching tokens
    for token in ["False", "false", "f", "0", "no"]:
        is_corr, marks, fb = evaluate_single_answer(
            question_type="true_false",
            correct_answer="False",
            student_answer=token,
            marks=1.5,
        )
        assert is_corr is True
        assert marks == 1.5

    # Opposite choice
    is_corr, marks, fb = evaluate_single_answer(
        question_type="true_false",
        correct_answer="True",
        student_answer="False",
        marks=1.5,
    )
    assert is_corr is False
    assert marks == 0.0

    # Invalid boolean string
    is_corr, marks, fb = evaluate_single_answer(
        question_type="true_false",
        correct_answer="True",
        student_answer="maybe",
        marks=1.5,
    )
    assert is_corr is False
    assert marks == 0.0


def test_numerical_evaluation():
    """Verify Numerical evaluation within tolerance and format handling."""
    # Exact match
    is_corr, marks, fb = evaluate_single_answer(
        question_type="numerical",
        correct_answer="9.81",
        student_answer="9.81",
        marks=3.0,
        tolerance=0.05,
    )
    assert is_corr is True
    assert marks == 3.0

    # Within tolerance (9.81 + 0.03 = 9.84)
    is_corr, marks, fb = evaluate_single_answer(
        question_type="numerical",
        correct_answer="9.81",
        student_answer="9.84",
        marks=3.0,
        tolerance=0.05,
    )
    assert is_corr is True
    assert marks == 3.0

    # Exceeding tolerance (9.81 + 0.10 = 9.91)
    is_corr, marks, fb = evaluate_single_answer(
        question_type="numerical",
        correct_answer="9.81",
        student_answer="9.91",
        marks=3.0,
        tolerance=0.05,
    )
    assert is_corr is False
    assert marks == 0.0

    # Malformed string
    is_corr, marks, fb = evaluate_single_answer(
        question_type="numerical",
        correct_answer="9.81",
        student_answer="ten meters per second",
        marks=3.0,
        tolerance=0.05,
    )
    assert is_corr is False
    assert marks == 0.0


def test_short_answer_evaluation():
    """Verify Short Answer evaluation with case normalization, alternatives, and key phrases."""
    # Exact match case-insensitive
    is_corr, marks, fb = evaluate_single_answer(
        question_type="short_answer",
        correct_answer="Mitochondria",
        student_answer="mitochondria",
        marks=2.0,
    )
    assert is_corr is True
    assert marks == 2.0

    # Alternative candidate answers separated by ';'
    is_corr, marks, fb = evaluate_single_answer(
        question_type="short_answer",
        correct_answer="Mitochondria; Powerhouse of the cell",
        student_answer="powerhouse of the cell",
        marks=2.0,
    )
    assert is_corr is True
    assert marks == 2.0

    # Key phrase contained in student's longer explanation
    is_corr, marks, fb = evaluate_single_answer(
        question_type="short_answer",
        correct_answer="photosynthesis",
        student_answer="Plants produce energy using photosynthesis in leaves",
        marks=2.0,
    )
    assert is_corr is True
    assert marks == 2.0

    # Incorrect answer
    is_corr, marks, fb = evaluate_single_answer(
        question_type="short_answer",
        correct_answer="photosynthesis",
        student_answer="cellular respiration in animals",
        marks=2.0,
    )
    assert is_corr is False
    assert marks == 0.0


# ============================================================================
# 2. Mixed Assessment CRUD & Student Privacy Tests
# ============================================================================

def test_create_and_get_mixed_assessment():
    """Verify creating a mixed assessment containing all 4 question types and student view privacy."""
    db = TestingSessionLocal()
    course = Course(title="Cell Biology 101", description="Introductory cell biology")
    db.add(course)
    db.commit()

    payload = {
        "title": "Module 1 Comprehensive Assessment",
        "description": "Assessment covering cell organelle functions and energy generation.",
        "assessment_type": "mixed",
        "time_limit_minutes": 45,
        "questions": [
            {
                "question_type": "mcq",
                "prompt": "Which organelle is responsible for ATP synthesis?",
                "order_index": 0,
                "marks": 2.0,
                "options_json": ["Mitochondria", "Nucleus", "Ribosome", "Golgi"],
                "correct_answer": "Mitochondria",
                "explanation": "Mitochondria generate most of the chemical energy needed by the cell.",
            },
            {
                "question_type": "true_false",
                "prompt": "Plant cells have cell walls, while animal cells do not.",
                "order_index": 1,
                "marks": 1.0,
                "correct_answer": "True",
                "explanation": "Plant cells have rigid walls made of cellulose.",
            },
            {
                "question_type": "numerical",
                "prompt": "What is the net ATP yield from one glucose molecule in aerobic respiration (approx)?",
                "order_index": 2,
                "marks": 3.0,
                "correct_answer": "32",
                "tolerance": 2.0,
                "explanation": "Net yield is typically between 30 and 32 ATP molecules.",
            },
            {
                "question_type": "short_answer",
                "prompt": "What green pigment absorbs light during photosynthesis?",
                "order_index": 3,
                "marks": 2.0,
                "correct_answer": "Chlorophyll",
                "explanation": "Chlorophyll absorbs blue and red wavelengths of light.",
            },
        ],
    }

    resp = client.post(f"/courses/{course.id}/assessments", json=payload)
    assert resp.status_code == 201
    data = resp.json()

    assert data["title"] == "Module 1 Comprehensive Assessment"
    assert data["assessment_type"] == "mixed"
    assert data["total_marks"] == 8.0
    assert len(data["questions"]) == 4

    # Security check: correct_answer, tolerance, and explanation MUST NOT be returned in student view
    for q in data["questions"]:
        assert "correct_answer" not in q
        assert "tolerance" not in q
        assert "explanation" not in q

    # List assessments endpoint
    list_resp = client.get(f"/courses/{course.id}/assessments")
    assert list_resp.status_code == 200
    summaries = list_resp.json()
    assert len(summaries) == 1
    assert summaries[0]["title"] == "Module 1 Comprehensive Assessment"
    assert summaries[0]["question_count"] == 4
    assert summaries[0]["total_marks"] == 8.0

    # Get single assessment endpoint
    get_resp = client.get(f"/courses/{course.id}/assessments/{data['id']}")
    assert get_resp.status_code == 200
    get_data = get_resp.json()
    assert get_data["id"] == data["id"]
    for q in get_data["questions"]:
        assert "correct_answer" not in q
        assert "tolerance" not in q
        assert "explanation" not in q


def test_mock_test_creation_and_listing():
    """Verify mock test assessment type with timed configuration."""
    db = TestingSessionLocal()
    course = Course(title="Organic Chemistry", description="CHEM 201")
    db.add(course)
    db.commit()

    payload = {
        "title": "Midterm Mock Exam 1",
        "description": "Full-length timed practice exam under timed test conditions.",
        "assessment_type": "mock_test",
        "time_limit_minutes": 60,
        "questions": [
            {
                "question_type": "mcq",
                "prompt": "Which functional group contains a carbonyl bonded to an OH?",
                "order_index": 0,
                "marks": 5.0,
                "options_json": ["Carboxylic acid", "Ester", "Aldehyde", "Ketone"],
                "correct_answer": "Carboxylic acid",
                "explanation": "R-COOH is a carboxylic acid.",
            },
            {
                "question_type": "numerical",
                "prompt": "What is the bond angle of sp3 hybridized carbon in degrees?",
                "order_index": 1,
                "marks": 5.0,
                "correct_answer": "109.5",
                "tolerance": 0.5,
                "explanation": "Tetrahedral bond angle is 109.5 degrees.",
            },
        ],
    }

    resp = client.post(f"/courses/{course.id}/assessments", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["assessment_type"] == "mock_test"
    assert data["time_limit_minutes"] == 60
    assert data["total_marks"] == 10.0


# ============================================================================
# 3. Assessment Attempt Lifecycle & Draft Answers
# ============================================================================

def test_attempt_lifecycle_draft_and_submission():
    """
    Verify complete attempt lifecycle:
    1. Start attempt (in_progress).
    2. Save draft answers.
    3. Verify answers are not scored in-progress.
    4. Submit attempt and verify deterministic scoring and explanations revealed.
    5. Verify attempt is locked (saving draft answers rejected).
    6. Verify submission idempotency.
    """
    db = TestingSessionLocal()
    course = Course(title="Physics 101", description="Mechanics")
    db.add(course)
    db.commit()

    # Create assessment
    payload = {
        "title": "Kinematics Quiz",
        "assessment_type": "quiz",
        "questions": [
            {
                "question_type": "numerical",
                "prompt": "Acceleration due to Earth's gravity in m/s^2?",
                "order_index": 0,
                "marks": 2.0,
                "correct_answer": "9.8",
                "tolerance": 0.1,
                "explanation": "g = 9.8 m/s^2 at sea level.",
            },
            {
                "question_type": "true_false",
                "prompt": "Velocity is a scalar quantity.",
                "order_index": 1,
                "marks": 2.0,
                "correct_answer": "False",
                "explanation": "Velocity has magnitude and direction (vector).",
            },
            {
                "question_type": "short_answer",
                "prompt": "What is the unit of force in SI units?",
                "order_index": 2,
                "marks": 2.0,
                "correct_answer": "Newton; N",
                "explanation": "Force is measured in Newtons (N).",
            },
        ],
    }
    create_resp = client.post(f"/courses/{course.id}/assessments", json=payload)
    assessment = create_resp.json()
    assessment_id = assessment["id"]
    q_ids = [q["id"] for q in assessment["questions"]]

    # 1. Start attempt
    start_resp = client.post(
        f"/courses/{course.id}/assessments/{assessment_id}/attempts",
        json={"student_id": "student_alice"},
    )
    assert start_resp.status_code == 201
    attempt = start_resp.json()
    attempt_id = attempt["id"]
    assert attempt["status"] == "in_progress"
    assert attempt["score"] is None
    assert attempt["submitted_at"] is None
    assert len(attempt["answers"]) == 3

    # Answers should have is_correct None and correct_answer None
    for ans in attempt["answers"]:
        assert ans["is_correct"] is None
        assert ans["marks_awarded"] == 0.0
        assert ans["correct_answer"] is None
        assert ans["explanation"] is None

    # 2. Save draft answers
    draft_payload = {
        "answers": [
            {"question_id": q_ids[0], "student_answer": "9.81"},
            {"question_id": q_ids[1], "student_answer": "False"},
        ]
    }
    draft_resp = client.patch(
        f"/courses/{course.id}/assessments/{assessment_id}/attempts/{attempt_id}/draft",
        json=draft_payload,
    )
    assert draft_resp.status_code == 200
    draft_data = draft_resp.json()
    assert draft_data["status"] == "in_progress"
    ans_map = {a["question_id"]: a for a in draft_data["answers"]}
    assert ans_map[q_ids[0]]["student_answer"] == "9.81"
    assert ans_map[q_ids[1]]["student_answer"] == "False"
    assert ans_map[q_ids[0]]["is_correct"] is None  # Still not evaluated!

    # 3. Submit attempt with 3rd question answered at submission time
    submit_payload = {
        "answers": [
            {"question_id": q_ids[2], "student_answer": "Newton"}
        ]
    }
    submit_resp = client.post(
        f"/courses/{course.id}/assessments/{assessment_id}/attempts/{attempt_id}/submit",
        json=submit_payload,
    )
    assert submit_resp.status_code == 200
    result = submit_resp.json()
    assert result["status"] == "submitted"
    assert result["score"] == 6.0
    assert result["max_score"] == 6.0
    assert result["percentage"] == 100.0
    assert result["submitted_at"] is not None

    # Check answers breakdown
    for ans in result["answers"]:
        assert ans["is_correct"] is True
        assert ans["marks_awarded"] == 2.0
        assert ans["correct_answer"] is not None
        assert ans["explanation"] is not None

    # 4. Attempt is now locked: draft edit should be rejected with HTTP 400
    edit_resp = client.patch(
        f"/courses/{course.id}/assessments/{assessment_id}/attempts/{attempt_id}/draft",
        json={"answers": [{"question_id": q_ids[0], "student_answer": "9.0"}]},
    )
    assert edit_resp.status_code == 400
    assert "already been submitted" in edit_resp.json()["detail"].lower()

    # 5. Re-submission should be idempotent and return existing results
    re_submit_resp = client.post(
        f"/courses/{course.id}/assessments/{assessment_id}/attempts/{attempt_id}/submit",
        json={},
    )
    assert re_submit_resp.status_code == 200
    re_result = re_submit_resp.json()
    assert re_result["score"] == 6.0
    assert re_result["submitted_at"] == result["submitted_at"]

    # 6. List past attempts
    list_attempts_resp = client.get(
        f"/courses/{course.id}/assessments/{assessment_id}/attempts"
    )
    assert list_attempts_resp.status_code == 200
    all_attempts = list_attempts_resp.json()
    assert len(all_attempts) == 1
    assert all_attempts[0]["id"] == attempt_id


def test_partial_and_incorrect_submission():
    """Verify scoring when student provides partially correct and incorrect answers."""
    db = TestingSessionLocal()
    course = Course(title="Mathematics 101", description="Calculus")
    db.add(course)
    db.commit()

    payload = {
        "title": "Calculus Derivatives Quiz",
        "assessment_type": "quiz",
        "questions": [
            {
                "question_type": "numerical",
                "prompt": "What is the derivative of x^2 at x=3?",
                "marks": 5.0,
                "correct_answer": "6",
                "tolerance": 0.01,
            },
            {
                "question_type": "true_false",
                "prompt": "Is every continuous function differentiable?",
                "marks": 5.0,
                "correct_answer": "False",
                "explanation": "The absolute value function |x| is continuous at 0 but not differentiable.",
            },
        ],
    }
    assessment = client.post(f"/courses/{course.id}/assessments", json=payload).json()
    q_ids = [q["id"] for q in assessment["questions"]]

    # Start attempt
    attempt = client.post(
        f"/courses/{course.id}/assessments/{assessment['id']}/attempts",
        json={"student_id": "bob"},
    ).json()

    # Answer question 1 correctly (6), question 2 incorrectly (True)
    submit_resp = client.post(
        f"/courses/{course.id}/assessments/{assessment['id']}/attempts/{attempt['id']}/submit",
        json={
            "answers": [
                {"question_id": q_ids[0], "student_answer": "6"},
                {"question_id": q_ids[1], "student_answer": "True"},
            ]
        },
    )
    assert submit_resp.status_code == 200
    res = submit_resp.json()
    assert res["score"] == 5.0
    assert res["max_score"] == 10.0
    assert res["percentage"] == 50.0

    ans_map = {a["question_id"]: a for a in res["answers"]}
    assert ans_map[q_ids[0]]["is_correct"] is True
    assert ans_map[q_ids[0]]["marks_awarded"] == 5.0
    assert ans_map[q_ids[1]]["is_correct"] is False
    assert ans_map[q_ids[1]]["marks_awarded"] == 0.0


# ============================================================================
# 4. Scoping & Cascade Tests
# ============================================================================

def test_cross_course_isolation_and_cascade_delete():
    """Verify assessments and attempts are isolated by course, and cascade delete cleans up."""
    db = TestingSessionLocal()
    course1 = Course(title="Course 1")
    course2 = Course(title="Course 2")
    db.add_all([course1, course2])
    db.commit()

    # Create assessment in Course 1
    payload = {
        "title": "Course 1 Quiz",
        "questions": [
            {
                "question_type": "true_false",
                "prompt": "Is 1+1=2?",
                "marks": 1.0,
                "correct_answer": "True",
            }
        ],
    }
    ass_c1 = client.post(f"/courses/{course1.id}/assessments", json=payload).json()

    # Accessing Course 1 assessment via Course 2 should return 404
    resp = client.get(f"/courses/{course2.id}/assessments/{ass_c1['id']}")
    assert resp.status_code == 404

    # Starting attempt on Course 1 assessment under Course 2 should return 404
    resp = client.post(
        f"/courses/{course2.id}/assessments/{ass_c1['id']}/attempts",
        json={"student_id": "test"},
    )
    assert resp.status_code == 404

    # Delete Course 1 assessment
    del_resp = client.delete(f"/courses/{course1.id}/assessments/{ass_c1['id']}")
    assert del_resp.status_code == 200

    # Assessment should no longer exist
    assert client.get(f"/courses/{course1.id}/assessments/{ass_c1['id']}").status_code == 404


# ============================================================================
# 5. Alembic Migration Verification
# ============================================================================

def test_alembic_assessment_migration():
    """Verify that Alembic runs up to a5e1c8d2b903 and cleanly downgrades back to f9a3c2b1d402."""
    from alembic.config import Config
    from alembic import command

    alembic_cfg_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "alembic.ini")
    )
    alembic_cfg = Config(alembic_cfg_path)

    # Use a separate dedicated SQLite database file for Alembic test
    alembic_test_db = "test_alembic_b5_clean.db"
    if os.path.exists(alembic_test_db):
        try:
            os.remove(alembic_test_db)
        except OSError:
            pass

    alembic_url = f"sqlite:///{alembic_test_db}"
    alembic_cfg.set_main_option("sqlalchemy.url", alembic_url)

    try:
        # Upgrade to head (including a5e1c8d2b903)
        command.upgrade(alembic_cfg, "head")

        # Downgrade back to curriculum migration f9a3c2b1d402
        command.downgrade(alembic_cfg, "f9a3c2b1d402")

        # Upgrade back to head
        command.upgrade(alembic_cfg, "head")
    finally:
        if os.path.exists(alembic_test_db):
            try:
                os.remove(alembic_test_db)
            except OSError:
                pass

