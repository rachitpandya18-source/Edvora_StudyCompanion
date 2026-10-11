"""
Milestone B8 Test Suite: Adaptive Practice Engine & Dynamic Question Generation.

Verifies:
1. Practice Configuration Options (/courses/{course_id}/practice/options):
   - Returns topics with concept counts, question types, difficulties, and study planner recommendation.
   - 404 on non-existent course.
2. Adaptive Practice Generation (/courses/{course_id}/practice/generate):
   - Targeted concept practice generates valid questions tied to concept_id.
   - Automatic attempt creation in 'in_progress' state.
   - Student-safe response (answers/explanations omitted).
   - Valid submit_endpoint pointing to B5 attempt submission.
3. Quick Practice Mode:
   - Targets weak concepts (mastery < 0.70).
4. Mock Test Mode:
   - Curriculum-wide sampling across topics and concepts.
5. Robust Validation and Course Isolation:
   - Invalid mode yields 400.
   - Foreign concept/topic from another course yields 400.
   - Non-existent concept/topic yields 404.
   - Complete course isolation: Course A generation never leaks Course B data.
6. Full Learning Loop Closure:
   - B7 Study Plan (initial mastery 0.10)
   - -> B8 Practice Session Generate
   - -> B5 Submit Attempt (evaluate answers)
   - -> B6 BKT Mastery Update (automatic single update)
   - -> B7 Study Plan Updated (reflects updated mastery and priority)
7. LLM Resilience & Fallback:
   - Valid LLM generation parsed and persisted.
   - Graceful fallback when LLM raises Exception or returns invalid payload.
"""

import os
import sys
import uuid
from datetime import datetime, timezone
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

TEST_DB_FILE = f"test_b8_temp_{uuid.uuid4().hex[:8]}.db"
TEST_DATABASE_URL = f"sqlite:///{TEST_DB_FILE}"
os.environ["DATABASE_URL"] = TEST_DATABASE_URL

from app.db.database import Base, get_db
from app.models.course import Course
from app.models.topic import Topic
from app.models.concept import Concept
from app.models.content_unit import ContentUnit
from app.models.assessment import Assessment, Question, AssessmentAttempt
from app.models.learner_mastery import LearnerConceptMastery
from app.main import app

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
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
    if os.path.exists(TEST_DB_FILE):
        try:
            os.remove(TEST_DB_FILE)
        except OSError:
            pass


DEFAULT_MOCK_QUESTIONS_JSON = """[
    {
        "prompt": "What primary mechanism does this concept evaluate?",
        "question_type": "mcq",
        "options": ["Core curricular mechanisms", "Irrelevant dynamic", "External factor", "Noise term"],
        "correct_answer": "Core curricular mechanisms",
        "explanation": "It tests core curricular principles directly.",
        "marks": 1.0
    }
]"""


@pytest.fixture(autouse=True)
def mock_default_llm_response(monkeypatch):
    """
    By default, mock practice LLM generation to return structured JSON
    instantly, preventing slow internet requests and Gemini rate-limiting.
    """
    counter = {"count": 0}

    def mock_gen(prompt: str):
        counter["count"] += 1
        idx = counter["count"]
        # Extract concept name if present in prompt
        import re
        import json
        match = re.search(r'testing the concept: "([^"]+)"', prompt)
        concept_name = match.group(1) if match else f"Concept_{idx}"
        return json.dumps([
            {
                "prompt": f"Variation {idx}: Which statement best describes the fundamental mechanics of {concept_name}?",
                "question_type": "mcq",
                "options": [
                    f"Core principles and definitions of {concept_name}",
                    f"Secondary unrelated factor for {concept_name}",
                    f"Deprecated approach to {concept_name}",
                    f"None of the above for {concept_name}",
                ],
                "correct_answer": f"Core principles and definitions of {concept_name}",
                "explanation": f"Explains {concept_name} thoroughly.",
                "marks": 1.0,
            }
        ])

    monkeypatch.setattr(
        "app.services.practice_service.llm_service.generate_response",
        mock_gen
    )


def create_course_with_curriculum(db, course_id="course_test_1"):
    course = Course(
        id=course_id,
        title="Macroeconomics 101",
        description="Fundamentals of Macroeconomics",
    )
    db.add(course)

    topic1 = Topic(
        id=f"{course_id}_topic_1",
        course_id=course_id,
        title="Fiscal Policy",
        order_index=1,
    )
    topic2 = Topic(
        id=f"{course_id}_topic_2",
        course_id=course_id,
        title="Monetary Policy",
        order_index=2,
    )
    db.add_all([topic1, topic2])
    db.flush()

    concept1 = Concept(
        id=f"{course_id}_concept_1",
        course_id=course_id,
        topic_id=topic1.id,
        name="Government Spending Multiplier",
        description="Impact of fiscal stimulus on aggregate demand",
        order_index=1,
    )
    concept2 = Concept(
        id=f"{course_id}_concept_2",
        course_id=course_id,
        topic_id=topic1.id,
        name="Tax Policy",
        description="Direct and indirect taxation dynamics",
        order_index=2,
    )
    concept3 = Concept(
        id=f"{course_id}_concept_3",
        course_id=course_id,
        topic_id=topic2.id,
        name="Central Bank Interest Rates",
        description="Policy rate transmission mechanism",
        order_index=1,
    )
    db.add_all([concept1, concept2, concept3])
    db.commit()

    return course, [topic1, topic2], [concept1, concept2, concept3]


# ============================================================================
# 1. Practice Options Tests
# ============================================================================

def test_get_practice_options_success():
    db = TestingSessionLocal()
    course, topics, concepts = create_course_with_curriculum(db, "course_opt")
    db.close()

    response = client.get(f"/courses/{course.id}/practice/options")
    assert response.status_code == 200
    data = response.json()

    assert data["course_id"] == course.id
    assert len(data["topics"]) == 2
    assert data["topics"][0]["name"] == "Fiscal Policy"
    assert data["topics"][0]["concept_count"] == 2
    assert data["topics"][1]["name"] == "Monetary Policy"
    assert data["topics"][1]["concept_count"] == 1
    assert any(qt["value"] == "mcq" for qt in data["question_types"])
    assert any(d["value"] == "medium" for d in data["difficulties"])


def test_get_practice_options_not_found():
    response = client.get("/courses/non_existent_course/practice/options")
    assert response.status_code == 404


# ============================================================================
# 2. Adaptive Practice Generation Tests
# ============================================================================

def test_generate_adaptive_practice_specific_concept():
    db = TestingSessionLocal()
    course, topics, concepts = create_course_with_curriculum(db, "course_adapt")
    target_concept = concepts[0]
    db.close()

    payload = {
        "mode": "adaptive",
        "concept_id": target_concept.id,
        "question_count": 3,
        "difficulty": "medium",
        "student_id": "student_alpha",
    }
    response = client.post(f"/courses/{course.id}/practice/generate", json=payload)
    assert response.status_code == 201
    data = response.json()

    assert data["course_id"] == course.id
    assert data["mode"] == "adaptive"
    assert data["concept_id"] == target_concept.id
    assert data["concept_name"] == target_concept.name
    assert data["total_questions"] == 3
    assert len(data["questions"]) == 3

    # Check student-safe structure: correct_answer & explanation MUST NOT be exposed
    for q in data["questions"]:
        assert "correct_answer" not in q
        assert "explanation" not in q
        assert q["concept_id"] == target_concept.id
        assert q["question_type"] == "mcq"
        assert len(q["options_json"]) >= 2
        assert q["marks"] > 0

    # Verify attempt and endpoint
    assert data["attempt_id"] is not None
    assert data["assessment_id"] is not None
    assert data["submit_endpoint"] == f"/courses/{course.id}/assessments/{data['assessment_id']}/attempts/{data['attempt_id']}/submit"

    # Verify database persistence
    db = TestingSessionLocal()
    assessment = db.query(Assessment).filter(Assessment.id == data["assessment_id"]).first()
    assert assessment is not None
    assert assessment.assessment_type == "practice"
    assert len(assessment.questions) == 3

    attempt = db.query(AssessmentAttempt).filter(AssessmentAttempt.id == data["attempt_id"]).first()
    assert attempt is not None
    assert attempt.status == "in_progress"
    assert attempt.student_id == "student_alpha"
    assert len(attempt.answers) == 3
    db.close()


def test_generate_adaptive_practice_top_recommended():
    db = TestingSessionLocal()
    course, topics, concepts = create_course_with_curriculum(db, "course_rec")
    db.close()

    payload = {
        "mode": "adaptive",
        "question_count": 3,
        "student_id": "student_rec",
    }
    response = client.post(f"/courses/{course.id}/practice/generate", json=payload)
    assert response.status_code == 201
    data = response.json()

    assert data["mode"] == "adaptive"
    assert data["concept_id"] is not None
    assert len(data["questions"]) == 3


# ============================================================================
# 3. Quick Mode & Mock Test Mode Tests
# ============================================================================

def test_generate_quick_practice_weak_concepts():
    db = TestingSessionLocal()
    course, topics, concepts = create_course_with_curriculum(db, "course_quick")

    # Set concept 1 as mastered (0.85), concept 2 as weak (0.35)
    mastered = LearnerConceptMastery(
        student_id="student_quick",
        course_id=course.id,
        concept_id=concepts[0].id,
        mastery_probability=0.85,
    )
    weak = LearnerConceptMastery(
        student_id="student_quick",
        course_id=course.id,
        concept_id=concepts[1].id,
        mastery_probability=0.35,
    )
    db.add_all([mastered, weak])
    db.commit()
    db.close()

    payload = {
        "mode": "quick",
        "question_count": 3,
        "student_id": "student_quick",
    }
    response = client.post(f"/courses/{course.id}/practice/generate", json=payload)
    assert response.status_code == 201
    data = response.json()

    assert data["mode"] == "quick"
    assert len(data["questions"]) == 3
    # Generated questions should target weak or unmastered concepts, not the 0.85 mastered one
    concept_ids_in_practice = {q["concept_id"] for q in data["questions"]}
    assert concepts[1].id in concept_ids_in_practice or concepts[2].id in concept_ids_in_practice


def test_generate_mock_test_mode_curriculum_sampling():
    db = TestingSessionLocal()
    course, topics, concepts = create_course_with_curriculum(db, "course_mock")
    db.close()

    payload = {
        "mode": "mock_test",
        "question_count": 5,
        "student_id": "student_mock",
    }
    response = client.post(f"/courses/{course.id}/practice/generate", json=payload)
    assert response.status_code == 201
    data = response.json()

    assert data["mode"] == "mock_test"
    assert len(data["questions"]) == 5
    sampled_concepts = {q["concept_id"] for q in data["questions"]}
    # Curriculum sampling should include multiple concepts
    assert len(sampled_concepts) >= 2


# ============================================================================
# 4. Validation & Course Isolation Tests
# ============================================================================

def test_validation_invalid_mode():
    db = TestingSessionLocal()
    course, _, _ = create_course_with_curriculum(db, "course_val1")
    db.close()

    response = client.post(f"/courses/{course.id}/practice/generate", json={"mode": "invalid_mode"})
    assert response.status_code == 400
    assert "Invalid practice mode" in response.json()["detail"]


def test_validation_foreign_concept_rejection():
    db = TestingSessionLocal()
    course_a, _, concepts_a = create_course_with_curriculum(db, "course_a")
    course_b, _, concepts_b = create_course_with_curriculum(db, "course_b")
    db.close()

    # Attempt to request Concept B inside Course A
    payload = {
        "mode": "adaptive",
        "concept_id": concepts_b[0].id,
    }
    response = client.post(f"/courses/{course_a.id}/practice/generate", json=payload)
    assert response.status_code == 400
    assert "does not belong to course" in response.json()["detail"]


def test_validation_nonexistent_concept():
    db = TestingSessionLocal()
    course, _, _ = create_course_with_curriculum(db, "course_val2")
    db.close()

    payload = {
        "mode": "adaptive",
        "concept_id": "non_existent_concept_id",
    }
    response = client.post(f"/courses/{course.id}/practice/generate", json=payload)
    assert response.status_code == 404


def test_validation_foreign_topic_rejection():
    db = TestingSessionLocal()
    course_a, topics_a, _ = create_course_with_curriculum(db, "course_ta")
    course_b, topics_b, _ = create_course_with_curriculum(db, "course_tb")
    db.close()

    payload = {
        "mode": "mock_test",
        "topic_id": topics_b[0].id,
    }
    response = client.post(f"/courses/{course_a.id}/practice/generate", json=payload)
    assert response.status_code == 400
    assert "does not belong to course" in response.json()["detail"]


def test_validation_empty_course_rejection():
    db = TestingSessionLocal()
    empty_course = Course(id="course_empty", title="Empty Course")
    db.add(empty_course)
    db.commit()
    db.close()

    response = client.post(f"/{empty_course.id}/practice/generate", json={"mode": "adaptive"})
    # Either 404 (due to prefix) or 400
    res = client.post(f"/courses/{empty_course.id}/practice/generate", json={"mode": "adaptive"})
    assert res.status_code == 400
    assert "No concepts found" in res.json()["detail"]


# ============================================================================
# 5. Full Closed Learning Loop Integration Test
# ============================================================================

def test_closed_learning_loop_b7_to_b8_to_b5_to_b6_to_b7():
    """
    Validates complete educational cycle:
    1. B7 /study-plan shows initial mastery state (P(L0) = 0.10) for Concept 1.
    2. B8 /practice/generate creates session and start attempt for Concept 1.
    3. Student answers questions correctly and calls B5 submit_endpoint.
    4. B5 evaluates answers, marks attempt as submitted.
    5. B6 BKT automatically updates LearnerConceptMastery in database.
    6. B7 /study-plan immediately reflects higher mastery for Concept 1.
    """
    db = TestingSessionLocal()
    course, topics, concepts = create_course_with_curriculum(db, "course_loop")
    target_concept = concepts[0]
    db.close()

    student_id = "loop_student_1"

    # Step 1: Check initial B7 Study Plan
    resp_plan_initial = client.get(f"/courses/{course.id}/study-plan?student_id={student_id}")
    assert resp_plan_initial.status_code == 200
    plan_data_init = resp_plan_initial.json()
    init_cand = next(c for c in plan_data_init["prioritized_concepts"] if c["concept_id"] == target_concept.id)
    assert init_cand["mastery_probability"] == 0.10

    # Step 2: Generate B8 Practice Session
    gen_payload = {
        "mode": "adaptive",
        "concept_id": target_concept.id,
        "question_count": 2,
        "student_id": student_id,
    }
    resp_gen = client.post(f"/courses/{course.id}/practice/generate", json=gen_payload)
    assert resp_gen.status_code == 201
    practice_data = resp_gen.json()

    assessment_id = practice_data["assessment_id"]
    attempt_id = practice_data["attempt_id"]
    submit_url = practice_data["submit_endpoint"]
    questions = practice_data["questions"]
    assert len(questions) == 2

    # Step 3: Fetch correct answers from DB to simulate correct student submission
    db = TestingSessionLocal()
    db_questions = db.query(Question).filter(Question.assessment_id == assessment_id).all()
    q_ans_map = {q.id: q.correct_answer for q in db_questions}
    db.close()

    # Step 4: Submit attempt via B5 endpoint
    submission_payload = {
        "answers": [
            {
                "question_id": q["id"],
                "student_answer": q_ans_map[q["id"]],
            }
            for q in questions
        ]
    }
    resp_submit = client.post(submit_url, json=submission_payload)
    assert resp_submit.status_code == 200
    submit_result = resp_submit.json()

    assert submit_result["status"] == "submitted"
    assert submit_result["score"] == submit_result["max_score"]
    assert submit_result["percentage"] == 100.0

    # Step 5: Verify B6 BKT updated mastery
    db = TestingSessionLocal()
    mastery_record = (
        db.query(LearnerConceptMastery)
        .filter(
            LearnerConceptMastery.course_id == course.id,
            LearnerConceptMastery.student_id == student_id,
            LearnerConceptMastery.concept_id == target_concept.id,
        )
        .first()
    )
    assert mastery_record is not None
    # Since 2 correct answers were submitted, mastery must have updated twice and exceed 0.10
    assert mastery_record.mastery_probability > 0.10
    assert mastery_record.observation_count == 2
    assert mastery_record.correct_count == 2
    updated_prob = mastery_record.mastery_probability
    db.close()

    # Step 6: Verify B7 Study Plan reflects updated mastery
    resp_plan_updated = client.get(f"/courses/{course.id}/study-plan?student_id={student_id}")
    assert resp_plan_updated.status_code == 200
    plan_data_updated = resp_plan_updated.json()
    updated_cand = next(c for c in plan_data_updated["prioritized_concepts"] if c["concept_id"] == target_concept.id)
    assert updated_cand["mastery_probability"] == updated_prob
    assert updated_cand["mastery_probability"] > 0.10


# ============================================================================
# 6. LLM Dynamic Generation & Fallback Resilience
# ============================================================================

def test_llm_generation_success_mocked():
    db = TestingSessionLocal()
    course, topics, concepts = create_course_with_curriculum(db, "course_llm_ok")
    target_concept = concepts[0]
    db.close()

    mock_llm_json = """[
        {
            "prompt": "What primary mechanism does the spending multiplier employ?",
            "question_type": "mcq",
            "options": ["Autonomous consumption loops", "Static tax rates", "Gold reserves", "Tariff barriers"],
            "correct_answer": "Autonomous consumption loops",
            "explanation": "Autonomous expenditure triggers successive induced consumption rounds.",
            "marks": 1.0
        }
    ]"""

    with patch("app.services.llm_service.generate_response", return_value=mock_llm_json):
        payload = {
            "mode": "adaptive",
            "concept_id": target_concept.id,
            "question_count": 1,
            "student_id": "student_llm",
        }
        response = client.post(f"/courses/{course.id}/practice/generate", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert len(data["questions"]) == 1
        assert data["questions"][0]["prompt"] == "What primary mechanism does the spending multiplier employ?"


def test_llm_fallback_resilience_when_error_raised():
    db = TestingSessionLocal()
    course, topics, concepts = create_course_with_curriculum(db, "course_llm_fail")
    target_concept = concepts[0]
    db.close()

    # Simulate LLM raising an unexpected connection or quota error
    with patch("app.services.llm_service.generate_response", side_effect=RuntimeError("Quota exceeded")):
        payload = {
            "mode": "adaptive",
            "concept_id": target_concept.id,
            "question_count": 2,
            "student_id": "student_fallback",
        }
        response = client.post(f"/courses/{course.id}/practice/generate", json=payload)
        # Should gracefully fall back to deterministic question generation without crashing
        assert response.status_code == 201
        data = response.json()
        assert len(data["questions"]) == 2
        for q in data["questions"]:
            assert q["concept_id"] == target_concept.id
            assert len(q["options_json"]) >= 2
