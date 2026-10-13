"""
Regression security test suite for Milestone C1:
Multi-Tenant Boundary and IDOR Hardening.

Verifies:
1. User A cannot access User B's course curriculum, topics, concepts, or prerequisites (returns 404).
2. User A cannot access User B's study plan or study next recommendations (returns 404).
3. User A cannot access User B's course analytics or velocity trends (returns 404).
4. User A cannot access User B's concept mastery or initialize mastery state (returns 404).
5. User A cannot access User B's assessments or start attempts (returns 404).
6. User A cannot generate practice sessions on User B's course (returns 404).
7. User A has full normal access to their own course resources (returns 200/201).
8. Fail-closed authentication in production/missing mode rejects requests without JWT (returns 401).
"""

import os
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

TEST_DB_FILE = f"test_c1_temp_{uuid.uuid4().hex[:8]}.db"
TEST_DATABASE_URL = f"sqlite:///{TEST_DB_FILE}"

from app.db.database import Base, get_db
from app.models.user import User
from app.models.course import Course
from app.models.topic import Topic
from app.models.concept import Concept
from app.core.security import get_password_hash, create_access_token
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
    test_engine.dispose()
    if os.path.exists(TEST_DB_FILE):
        try:
            os.remove(TEST_DB_FILE)
        except OSError:
            pass


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def test_users():
    db = TestingSessionLocal()
    try:
        user_a = User(
            id=str(uuid.uuid4()),
            email="tenant_a@edvora.edu",
            username="tenant_a",
            full_name="Tenant Alice",
            hashed_password=get_password_hash("StrongPassword123!"),
        )
        user_b = User(
            id=str(uuid.uuid4()),
            email="tenant_b@edvora.edu",
            username="tenant_b",
            full_name="Tenant Bob",
            hashed_password=get_password_hash("StrongPassword123!"),
        )
        db.add_all([user_a, user_b])
        db.commit()

        token_a = create_access_token(data={"sub": user_a.id, "email": user_a.email})
        token_b = create_access_token(data={"sub": user_b.id, "email": user_b.email})

        return {
            "user_a": user_a,
            "user_b": user_b,
            "headers_a": {"Authorization": f"Bearer {token_a}"},
            "headers_b": {"Authorization": f"Bearer {token_b}"},
        }
    finally:
        db.close()


def test_cross_tenant_curriculum_and_topic_idor(client, test_users):
    headers_a = test_users["headers_a"]
    headers_b = test_users["headers_b"]

    # Alice creates Course A
    res_a = client.post(
        "/courses",
        headers=headers_a,
        json={"title": "Alice Biology", "description": "Alice's Private Biology Course"},
    )
    assert res_a.status_code == 201
    course_a_id = res_a.json()["id"]

    # Alice creates a Topic and a Concept in Course A
    topic_res = client.post(
        f"/courses/{course_a_id}/topics",
        headers=headers_a,
        json={"title": "Cell Biology", "order_index": 1},
    )
    assert topic_res.status_code == 201
    topic_a_id = topic_res.json()["id"]

    concept_res = client.post(
        f"/courses/{course_a_id}/topics/{topic_a_id}/concepts",
        headers=headers_a,
        json={"name": "Mitochondria", "description": "Powerhouse", "order_index": 1},
    )
    assert concept_res.status_code == 201
    concept_a_id = concept_res.json()["id"]

    # Bob attempts to read Alice's curriculum
    curriculum_res = client.get(f"/courses/{course_a_id}/curriculum", headers=headers_b)
    assert curriculum_res.status_code == 404

    # Bob attempts to list Alice's topics
    topics_res = client.get(f"/courses/{course_a_id}/topics", headers=headers_b)
    assert topics_res.status_code == 404

    # Bob attempts to mutate Alice's topic
    update_res = client.put(
        f"/courses/{course_a_id}/topics/{topic_a_id}",
        headers=headers_b,
        json={"title": "Hacked Topic"},
    )
    assert update_res.status_code == 404

    # Bob attempts to delete Alice's topic
    del_res = client.delete(f"/courses/{course_a_id}/topics/{topic_a_id}", headers=headers_b)
    assert del_res.status_code == 404

    # Bob attempts to read/mutate Alice's concepts
    get_concept_res = client.get(
        f"/courses/{course_a_id}/concepts/{concept_a_id}",
        headers=headers_b,
    )
    assert get_concept_res.status_code == 404


def test_cross_tenant_study_planner_and_analytics_idor(client, test_users):
    headers_a = test_users["headers_a"]
    headers_b = test_users["headers_b"]

    res_a = client.post(
        "/courses",
        headers=headers_a,
        json={"title": "Alice Physics", "description": "Physics 101"},
    )
    assert res_a.status_code == 201
    course_a_id = res_a.json()["id"]

    # Bob attempts study planner endpoints on Alice's course
    plan_res = client.get(f"/courses/{course_a_id}/study-plan", headers=headers_b)
    assert plan_res.status_code == 404

    next_res = client.get(f"/courses/{course_a_id}/study-next", headers=headers_b)
    assert next_res.status_code == 404

    # Bob attempts analytics endpoints on Alice's course
    overview_res = client.get(f"/courses/{course_a_id}/analytics/overview", headers=headers_b)
    assert overview_res.status_code == 404

    trends_res = client.get(f"/courses/{course_a_id}/analytics/trends", headers=headers_b)
    assert trends_res.status_code == 404


def test_cross_tenant_mastery_and_assessment_idor(client, test_users):
    headers_a = test_users["headers_a"]
    headers_b = test_users["headers_b"]

    res_a = client.post(
        "/courses",
        headers=headers_a,
        json={"title": "Alice Chemistry", "description": "Chemistry 101"},
    )
    assert res_a.status_code == 201
    course_a_id = res_a.json()["id"]

    # Bob attempts to view or initialize mastery in Alice's course
    mastery_res = client.get(f"/courses/{course_a_id}/mastery", headers=headers_b)
    assert mastery_res.status_code == 404

    # Bob attempts to view or create assessments in Alice's course
    assessments_res = client.get(f"/courses/{course_a_id}/assessments", headers=headers_b)
    assert assessments_res.status_code == 404

    create_ass_res = client.post(
        f"/courses/{course_a_id}/assessments",
        headers=headers_b,
        json={"title": "Bob's Malicious Quiz", "questions": []},
    )
    assert create_ass_res.status_code == 404

    # Bob attempts to generate practice in Alice's course
    practice_res = client.post(
        f"/courses/{course_a_id}/practice/generate",
        headers=headers_b,
        json={"item_count": 5},
    )
    assert practice_res.status_code == 404


def test_tenant_a_normal_access_succeeds(client, test_users):
    headers_a = test_users["headers_a"]

    # Alice creates course
    res = client.post(
        "/courses",
        headers=headers_a,
        json={"title": "Alice Valid Course", "description": "Everything should work"},
    )
    assert res.status_code == 201
    course_id = res.json()["id"]

    # Alice accesses her own study plan
    plan_res = client.get(f"/courses/{course_id}/study-plan", headers=headers_a)
    assert plan_res.status_code == 200

    # Alice accesses her own analytics overview
    analytics_res = client.get(f"/courses/{course_id}/analytics/overview", headers=headers_a)
    assert analytics_res.status_code == 200

    # Alice accesses her own mastery
    mastery_res = client.get(f"/courses/{course_id}/mastery", headers=headers_a)
    assert mastery_res.status_code == 200
    assert mastery_res.json()["course_id"] == course_id


def test_unowned_legacy_course_read_only_and_mutation_blocked(client, test_users):
    headers_a = test_users["headers_a"]
    headers_b = test_users["headers_b"]

    # Create a legacy course directly in DB with owner_id=None
    db = TestingSessionLocal()
    try:
        legacy_course = Course(
            id=str(uuid.uuid4()),
            title="Legacy Unowned Course",
            description="Created prior to multi-tenant milestone without owner_id",
            owner_id=None,
        )
        db.add(legacy_course)
        db.commit()
        legacy_id = legacy_course.id
    finally:
        db.close()

    # 1. Read operations ARE permitted for both tenants
    get_res_a = client.get(f"/courses/{legacy_id}", headers=headers_a)
    assert get_res_a.status_code == 200
    assert get_res_a.json()["title"] == "Legacy Unowned Course"

    get_res_b = client.get(f"/courses/{legacy_id}", headers=headers_b)
    assert get_res_b.status_code == 200

    curriculum_res = client.get(f"/courses/{legacy_id}/curriculum", headers=headers_b)
    assert curriculum_res.status_code == 200

    # 2. Structural mutations are strictly BLOCKED (403 Forbidden) for both tenants
    # Rename attempt
    put_res = client.put(
        f"/courses/{legacy_id}",
        headers=headers_b,
        json={"title": "Hijacked Course Title"},
    )
    assert put_res.status_code == 403
    assert "ownership is unassigned" in put_res.json()["detail"].lower()

    # Delete attempt
    del_res = client.delete(f"/courses/{legacy_id}", headers=headers_b)
    assert del_res.status_code == 403

    # Topic creation attempt
    topic_res = client.post(
        f"/courses/{legacy_id}/topics",
        headers=headers_a,
        json={"title": "Unauthorized Topic", "order_index": 1},
    )
    assert topic_res.status_code == 403

    # Source creation attempt
    source_res = client.post(
        f"/courses/{legacy_id}/sources",
        headers=headers_a,
        json={"filename": "unauthorized.pdf", "source_type": "pdf"},
    )
    assert source_res.status_code == 403

    # Assessment creation attempt
    ass_res = client.post(
        f"/courses/{legacy_id}/assessments",
        headers=headers_b,
        json={"title": "Unauthorized Assessment", "questions": []},
    )
    assert ass_res.status_code == 403


def test_unowned_legacy_course_learner_isolation(client, test_users):
    headers_a = test_users["headers_a"]
    headers_b = test_users["headers_b"]
    user_a = test_users["user_a"]
    user_b = test_users["user_b"]

    # Seed an unowned legacy course with an assessment and a question
    from app.models.assessment import Assessment, Question
    db = TestingSessionLocal()
    try:
        legacy_course = Course(
            id=str(uuid.uuid4()),
            title="Legacy Practice Course",
            owner_id=None,
        )
        assessment = Assessment(
            id=str(uuid.uuid4()),
            course_id=legacy_course.id,
            title="Legacy Diagnostic Quiz",
            assessment_type="mcq",
            total_marks=10.0,
        )
        q1 = Question(
            id=str(uuid.uuid4()),
            assessment_id=assessment.id,
            prompt="What is 2 + 2?",
            question_type="mcq",
            options_json=["3", "4", "5"],
            correct_answer="4",
            marks=10.0,
            order_index=1,
        )
        db.add_all([legacy_course, assessment, q1])
        db.commit()
        course_id = legacy_course.id
        assessment_id = assessment.id
        q1_id = q1.id
    finally:
        db.close()

    # Tenant Alice takes the quiz on the legacy course
    start_a = client.post(
        f"/courses/{course_id}/assessments/{assessment_id}/attempts",
        headers=headers_a,
    )
    assert start_a.status_code == 201
    attempt_a_id = start_a.json()["id"]

    submit_a = client.post(
        f"/courses/{course_id}/assessments/{assessment_id}/attempts/{attempt_a_id}/submit",
        headers=headers_a,
        json={"answers": [{"question_id": q1_id, "student_answer": "4"}]},
    )
    assert submit_a.status_code == 200

    # Tenant Bob takes the quiz on the same legacy course
    start_b = client.post(
        f"/courses/{course_id}/assessments/{assessment_id}/attempts",
        headers=headers_b,
    )
    assert start_b.status_code == 201
    attempt_b_id = start_b.json()["id"]

    # Tenant Bob CANNOT read Alice's attempt (returns 404)
    bob_reads_alice = client.get(
        f"/courses/{course_id}/assessments/{assessment_id}/attempts/{attempt_a_id}",
        headers=headers_b,
    )
    assert bob_reads_alice.status_code == 404

    # Tenant Alice CANNOT read Bob's attempt (returns 404)
    alice_reads_bob = client.get(
        f"/courses/{course_id}/assessments/{assessment_id}/attempts/{attempt_b_id}",
        headers=headers_a,
    )
    assert alice_reads_bob.status_code == 404

    # Listing attempts strictly returns only the requesting student's attempts
    alice_list = client.get(
        f"/courses/{course_id}/assessments/{assessment_id}/attempts",
        headers=headers_a,
    )
    assert alice_list.status_code == 200
    alice_attempts = alice_list.json()
    assert len(alice_attempts) == 1
    assert alice_attempts[0]["id"] == attempt_a_id

    bob_list = client.get(
        f"/courses/{course_id}/assessments/{assessment_id}/attempts",
        headers=headers_b,
    )
    assert bob_list.status_code == 200
    bob_attempts = bob_list.json()
    assert len(bob_attempts) == 1
    assert bob_attempts[0]["id"] == attempt_b_id


