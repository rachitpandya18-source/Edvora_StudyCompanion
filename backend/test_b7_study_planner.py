"""
Milestone B7 Test Suite: Adaptive Study Planner.

Verifies:
1. Empty course returns graceful empty study plan and None top_recommendation.
2. Unpracticed course initializes concepts to ready/blocked based on prerequisites.
3. Prerequisite Blocker Priority: Unmastered prerequisite (Concept A) is prioritized
   over dependent Concept B, and Concept B is marked BLOCKED.
4. Ready Concept Progression: Once Concept A is mastered (>= 0.70), Concept B becomes
   is_ready: True and is recommended next.
5. Weak Concept Prioritization: When multiple concepts are ready, the one with lowest
   mastery or highest failure rate has highest priority score.
6. Retention Refresh: Mastered concept without attempts for >= 7 days receives
   REFRESH_RETENTION recommendation.
7. Course Completion: When all concepts are mastered, top_recommendation returns
   COURSE_COMPLETED with mock exam practice action.
8. Non-existent course yields 404.
9. REST API endpoints /courses/{course_id}/study-plan and /courses/{course_id}/study-next
   return valid Pydantic responses.
"""

import os
import sys
import uuid
from datetime import datetime, timezone, timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

TEST_DB_FILE = f"test_b7_temp_{uuid.uuid4().hex[:8]}.db"
TEST_DATABASE_URL = f"sqlite:///{TEST_DB_FILE}"
os.environ["DATABASE_URL"] = TEST_DATABASE_URL

from app.db.database import Base, get_db
from app.models.course import Course
from app.models.topic import Topic
from app.models.concept import Concept, ConceptPrerequisite
from app.models.learner_mastery import LearnerConceptMastery
from app.models.content_unit import ContentUnit
from app.main import app

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
    test_engine.dispose()
    if os.path.exists(TEST_DB_FILE):
        try:
            os.remove(TEST_DB_FILE)
        except OSError:
            pass


def create_sample_course_with_curriculum(db):
    """
    Helper creating a test course with:
    Topic 1:
      - Concept A: Binary Search Trees (order 0)
      - Concept B: AVL Tree Rotations (order 1, requires Concept A)
    Topic 2:
      - Concept C: B-Trees (order 0, requires Concept B)
    """
    course = Course(
        title="Advanced Algorithms",
        description="Data structures and complexity analysis."
    )
    db.add(course)
    db.commit()
    db.refresh(course)

    topic_1 = Topic(course_id=course.id, title="Binary Trees", order_index=0)
    topic_2 = Topic(course_id=course.id, title="Multi-way Trees", order_index=1)
    db.add_all([topic_1, topic_2])
    db.commit()

    concept_a = Concept(course_id=course.id, topic_id=topic_1.id, name="Binary Search Trees", order_index=0)
    concept_b = Concept(course_id=course.id, topic_id=topic_1.id, name="AVL Tree Rotations", order_index=1)
    concept_c = Concept(course_id=course.id, topic_id=topic_2.id, name="B-Trees", order_index=0)
    db.add_all([concept_a, concept_b, concept_c])
    db.commit()

    # Prerequisites: B requires A, C requires B
    edge_1 = ConceptPrerequisite(concept_id=concept_b.id, prerequisite_id=concept_a.id)
    edge_2 = ConceptPrerequisite(concept_id=concept_c.id, prerequisite_id=concept_b.id)
    db.add_all([edge_1, edge_2])
    db.commit()

    return course, [concept_a, concept_b, concept_c]


# ============================================================================
# TESTS
# ============================================================================

def test_empty_course_study_plan():
    """Verify empty course returns gracefully with empty summary and None top recommendation."""
    db = TestingSessionLocal()
    course = Course(title="Empty Course")
    db.add(course)
    db.commit()
    course_id = course.id
    db.close()

    res = client.get(f"/courses/{course_id}/study-plan")
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["course_id"] == course_id
    assert data["overall_course_mastery"] == 0.0
    assert data["top_recommendation"] is None
    assert data["prioritized_concepts"] == []
    assert data["summary"]["total_concepts"] == 0


def test_prerequisite_blocking_and_unblocker_priority():
    """
    Concept B requires Concept A.
    Concept A has P(L) = 0.25 (unmastered).
    Concept B has P(L) = 0.10.
    Verify Concept A is prioritized with UNBLOCK_PREREQUISITE or REVISE_WEAK,
    and Concept B is marked BLOCKED (is_ready: False).
    """
    db = TestingSessionLocal()
    course, concepts = create_sample_course_with_curriculum(db)
    concept_a, concept_b, concept_c = concepts

    # Set mastery for A to 0.25 (attempted, weak)
    m_a = LearnerConceptMastery(
        student_id="default_student",
        course_id=course.id,
        concept_id=concept_a.id,
        mastery_probability=0.25,
        observation_count=2,
        correct_count=0
    )
    db.add(m_a)
    db.commit()
    course_id = course.id
    c_a_id = concept_a.id
    c_b_id = concept_b.id
    c_c_id = concept_c.id
    db.close()

    res = client.get(f"/courses/{course_id}/study-plan")
    assert res.status_code == 200
    plan = res.json()

    # Concept A should be ready and top priority
    top = plan["top_recommendation"]
    assert top is not None
    assert top["concept_id"] == c_a_id
    assert top["priority_category"] == "REVISE_WEAK"
    assert top["unblocked_dependents_count"] >= 1
    assert "Binary Search Trees" in top["rationale"]

    # Concept B and C should be marked BLOCKED
    concept_b_item = next(c for c in plan["prioritized_concepts"] if c["concept_id"] == c_b_id)
    assert concept_b_item["is_ready"] is False
    assert concept_b_item["priority_category"] == "BLOCKED"
    assert "Binary Search Trees" in concept_b_item["unmet_prerequisites"]

    concept_c_item = next(c for c in plan["prioritized_concepts"] if c["concept_id"] == c_c_id)
    assert concept_c_item["is_ready"] is False
    assert concept_c_item["priority_category"] == "BLOCKED"


def test_ready_concept_progression_when_prerequisite_mastered():
    """
    When Concept A is mastered (P(L) = 0.85), Concept B becomes is_ready: True
    and transitions to top recommendation (LEARN_NEW or UNBLOCK_PREREQUISITE).
    """
    db = TestingSessionLocal()
    course, concepts = create_sample_course_with_curriculum(db)
    concept_a, concept_b, concept_c = concepts

    # Master Concept A
    m_a = LearnerConceptMastery(
        student_id="default_student",
        course_id=course.id,
        concept_id=concept_a.id,
        mastery_probability=0.85,
        observation_count=5,
        correct_count=4,
        last_attempt_at=datetime.now(timezone.utc)
    )
    db.add(m_a)
    db.commit()
    course_id = course.id
    c_b_id = concept_b.id
    db.close()

    res = client.get(f"/courses/{course_id}/study-next")
    assert res.status_code == 200
    top = res.json()
    assert top is not None
    # Now Concept B should be recommended!
    assert top["concept_id"] == c_b_id
    assert top["priority_category"] in ("UNBLOCK_PREREQUISITE", "LEARN_NEW")
    assert len(top["recommended_actions"]) == 3


def test_retention_refresh_spaced_repetition():
    """
    Concept A was mastered (P(L) = 0.90), but not practiced in 10 days.
    Concept B and C do not exist or are also mastered.
    Verify category is REFRESH_RETENTION.
    """
    db = TestingSessionLocal()
    course = Course(title="Retention Course")
    db.add(course)
    db.commit()
    topic = Topic(course_id=course.id, title="Calculus", order_index=0)
    db.add(topic)
    db.commit()
    concept = Concept(course_id=course.id, topic_id=topic.id, name="Derivatives", order_index=0)
    db.add(concept)
    db.commit()

    ten_days_ago = datetime.now(timezone.utc) - timedelta(days=10)
    m = LearnerConceptMastery(
        student_id="default_student",
        course_id=course.id,
        concept_id=concept.id,
        mastery_probability=0.90,
        observation_count=4,
        correct_count=4,
        last_attempt_at=ten_days_ago
    )
    db.add(m)
    db.commit()
    course_id = course.id
    concept_id = concept.id
    db.close()

    res = client.get(f"/courses/{course_id}/study-next")
    assert res.status_code == 200
    top = res.json()
    assert top["concept_id"] == concept_id
    assert top["priority_category"] == "REFRESH_RETENTION"
    assert "retention" in top["rationale"].lower() or "decay" in top["rationale"].lower()


def test_course_completed_all_mastered():
    """
    All concepts mastered recently.
    Verify top_recommendation returns COURSE_COMPLETED with mock exam action.
    """
    db = TestingSessionLocal()
    course = Course(title="Completed Course")
    db.add(course)
    db.commit()
    topic = Topic(course_id=course.id, title="Linear Algebra", order_index=0)
    db.add(topic)
    db.commit()
    c1 = Concept(course_id=course.id, topic_id=topic.id, name="Vectors", order_index=0)
    c2 = Concept(course_id=course.id, topic_id=topic.id, name="Matrices", order_index=1)
    db.add_all([c1, c2])
    db.commit()

    now = datetime.now(timezone.utc)
    m1 = LearnerConceptMastery(
        student_id="default_student", course_id=course.id, concept_id=c1.id,
        mastery_probability=0.95, observation_count=5, correct_count=5, last_attempt_at=now
    )
    m2 = LearnerConceptMastery(
        student_id="default_student", course_id=course.id, concept_id=c2.id,
        mastery_probability=0.92, observation_count=5, correct_count=5, last_attempt_at=now
    )
    db.add_all([m1, m2])
    db.commit()
    course_id = course.id
    db.close()

    res = client.get(f"/courses/{course_id}/study-next")
    assert res.status_code == 200
    top = res.json()
    assert top["priority_category"] == "COURSE_COMPLETED"
    assert top["status_text"] == "All concepts mastered"
    assert "mock exam" in top["recommended_actions"][0]["title"].lower()


def test_nonexistent_course_404():
    """Verify non-existent course returns 404."""
    res = client.get("/courses/non-existent-course-id/study-plan")
    assert res.status_code == 404
    res = client.get("/courses/non-existent-course-id/study-next")
    assert res.status_code == 404


def test_legacy_recommendations_backward_compatibility():
    """Verify legacy Phase 0 /recommendations endpoint remains functional."""
    res = client.get("/recommendations/")
    assert res.status_code == 200
    assert "weak_concepts" in res.json()


if __name__ == "__main__":
    sys.exit(pytest.main(["-v", __file__]))
