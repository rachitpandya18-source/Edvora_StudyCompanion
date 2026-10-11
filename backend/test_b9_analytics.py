"""
Milestone B9 Test Suite: Learner Analytics & Course Progress Engine.

Comprehensive coverage for:
1. Course overview with populated data.
2. Mastery aggregation (sum of P(L) / total_concepts with unassessed default 0.10).
3. Mastery category boundaries (mastered >= 0.85, proficient [0.70, 0.85), developing [0.40, 0.70), struggling < 0.40 with attempt, unassessed).
4. Unassessed concepts handling.
5. Syllabus completion rate calculation (concepts with completed attempts / total).
6. Topic rollups (order, total, mastered, average mastery, completion pct).
7. Topic status calculation (not_started, in_progress, mastered).
8. Assessment summary (attempts, questions answered, overall accuracy, last practiced).
9. Velocity/trend calculation (chronological bucketing, day counts, average scores).
10. Exam readiness calculation (0.50*mastery + 0.30*completion + 0.20*recent_accuracy)*100.
11. Empty course handling (0 concepts, completion 0.0, bounded readiness).
12. Learner with no attempts handling.
13. Learner isolation (Student A data never leaks to Student B).
14. Topic/course isolation (Topic from Course A cannot be queried under Course B).
15. Missing course 404.
16. Missing topic 404.
17. Invalid days validation (<= 0 or > 365 returns 400).
18. Read-only verification (No DB mutation occurs when querying analytics endpoints).
"""

import os
import sys
import uuid
from datetime import datetime, timezone, timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

TEST_DB_FILE = f"test_b9_temp_{uuid.uuid4().hex[:8]}.db"
TEST_DATABASE_URL = f"sqlite:///{TEST_DB_FILE}"
os.environ["DATABASE_URL"] = TEST_DATABASE_URL

from app.db.database import Base, get_db
from app.models.course import Course
from app.models.topic import Topic
from app.models.concept import Concept
from app.models.assessment import Assessment, Question, AssessmentAttempt, AttemptAnswer
from app.models.learner_mastery import LearnerConceptMastery
from app.main import app

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=test_engine,
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


@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def populated_course(db_session):
    """
    Creates a course with 2 topics:
    Topic 1: 3 concepts (C1, C2, C3)
    Topic 2: 2 concepts (C4, C5)
    Total: 5 concepts.
    """
    course = Course(
        id=str(uuid.uuid4()),
        title="Microeconomics 101",
        description="Comprehensive introductory economics course",
    )
    db_session.add(course)

    t1 = Topic(
        id=str(uuid.uuid4()),
        course_id=course.id,
        title="Supply and Demand",
        order_index=1,
    )
    t2 = Topic(
        id=str(uuid.uuid4()),
        course_id=course.id,
        title="Market Structures",
        order_index=2,
    )
    db_session.add_all([t1, t2])

    c1 = Concept(id=str(uuid.uuid4()), course_id=course.id, topic_id=t1.id, name="Demand Curves", order_index=1)
    c2 = Concept(id=str(uuid.uuid4()), course_id=course.id, topic_id=t1.id, name="Supply Equilibrium", order_index=2)
    c3 = Concept(id=str(uuid.uuid4()), course_id=course.id, topic_id=t1.id, name="Price Elasticity", order_index=3)

    c4 = Concept(id=str(uuid.uuid4()), course_id=course.id, topic_id=t2.id, name="Monopoly", order_index=1)
    c5 = Concept(id=str(uuid.uuid4()), course_id=course.id, topic_id=t2.id, name="Oligopoly", order_index=2)
    db_session.add_all([c1, c2, c3, c4, c5])

    db_session.commit()
    return {
        "course": course,
        "topics": [t1, t2],
        "concepts": [c1, c2, c3, c4, c5],
    }


def test_missing_course_404():
    res = client.get(f"/courses/{uuid.uuid4()}/analytics/overview")
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()


def test_empty_course_analytics(db_session):
    """
    Empty course with 0 topics and 0 concepts.
    """
    empty_c = Course(id=str(uuid.uuid4()), title="Empty Course")
    db_session.add(empty_c)
    db_session.commit()

    res = client.get(f"/courses/{empty_c.id}/analytics/overview?learner_id=student_x")
    assert res.status_code == 200
    data = res.json()

    assert data["course_id"] == empty_c.id
    assert data["overall_mastery"] == 0.0
    assert data["syllabus_completion_rate"] == 0.0
    assert data["readiness_score"] == 0.0
    assert data["total_concepts"] == 0
    assert data["concepts_completed"] == 0
    assert data["mastery_breakdown"]["unassessed"] == 0
    assert data["assessment_summary"]["total_attempts"] == 0
    assert data["topics"] == []


def test_course_overview_with_unassessed_concepts(populated_course):
    """
    Course has concepts, but student has taken 0 attempts and has no mastery records.
    Every concept should be unassessed, prior mastery = 0.10, completion = 0.0.
    """
    course = populated_course["course"]
    res = client.get(f"/courses/{course.id}/analytics/overview?learner_id=brand_new_student")
    assert res.status_code == 200
    data = res.json()

    assert data["course_id"] == course.id
    assert data["learner_id"] == "brand_new_student"
    assert data["total_concepts"] == 5
    assert data["concepts_completed"] == 0
    assert data["overall_mastery"] == 0.10  # 5 * 0.10 / 5 = 0.10
    assert data["syllabus_completion_rate"] == 0.0
    # readiness: (0.50 * 0.10 + 0.30 * 0.0 + 0.20 * 0.0) * 100 = 5.0
    assert data["readiness_score"] == 5.0

    breakdown = data["mastery_breakdown"]
    assert breakdown["unassessed"] == 5
    assert breakdown["mastered"] == 0
    assert breakdown["proficient"] == 0
    assert breakdown["developing"] == 0
    assert breakdown["struggling"] == 0

    topics = data["topics"]
    assert len(topics) == 2
    assert topics[0]["status"] == "not_started"
    assert topics[0]["total_concepts"] == 3
    assert topics[0]["mastered_concepts"] == 0
    assert topics[0]["completion_percentage"] == 0.0
    assert topics[0]["average_mastery"] == 0.10


def test_mastery_category_boundaries_and_assessments(populated_course, db_session):
    """
    Verify exact category boundaries:
    - Mastered (>= 0.85): C1 at 0.90 with attempt
    - Proficient (0.70 <= P < 0.85): C2 at 0.75 with attempt
    - Developing (0.40 <= P < 0.70): C3 at 0.50 with attempt
    - Struggling (P < 0.40 with attempt): C4 at 0.25 with attempt
    - Unassessed (no attempt): C5 at 0.10 (no attempt)
    """
    course = populated_course["course"]
    concepts = populated_course["concepts"]
    student_id = "eval_student"

    # Set masteries for C1, C2, C3, C4
    m1 = LearnerConceptMastery(
        student_id=student_id,
        course_id=course.id,
        concept_id=concepts[0].id,
        mastery_probability=0.90,
        observation_count=3,
        correct_count=3,
    )
    m2 = LearnerConceptMastery(
        student_id=student_id,
        course_id=course.id,
        concept_id=concepts[1].id,
        mastery_probability=0.75,
        observation_count=2,
        correct_count=2,
    )
    m3 = LearnerConceptMastery(
        student_id=student_id,
        course_id=course.id,
        concept_id=concepts[2].id,
        mastery_probability=0.50,
        observation_count=2,
        correct_count=1,
    )
    m4 = LearnerConceptMastery(
        student_id=student_id,
        course_id=course.id,
        concept_id=concepts[3].id,
        mastery_probability=0.25,
        observation_count=1,
        correct_count=0,
    )
    db_session.add_all([m1, m2, m3, m4])

    # Create assessment and completed attempt covering C1, C2, C3, C4
    now = datetime.now(timezone.utc)
    assessment = Assessment(
        course_id=course.id,
        title="Quiz 1",
        total_marks=4.0,
    )
    db_session.add(assessment)
    db_session.flush()

    q1 = Question(assessment_id=assessment.id, question_type="mcq", prompt="Q1", correct_answer="A", marks=1.0, concept_id=concepts[0].id)
    q2 = Question(assessment_id=assessment.id, question_type="mcq", prompt="Q2", correct_answer="B", marks=1.0, concept_id=concepts[1].id)
    q3 = Question(assessment_id=assessment.id, question_type="mcq", prompt="Q3", correct_answer="C", marks=1.0, concept_id=concepts[2].id)
    q4 = Question(assessment_id=assessment.id, question_type="mcq", prompt="Q4", correct_answer="D", marks=1.0, concept_id=concepts[3].id)
    db_session.add_all([q1, q2, q3, q4])
    db_session.flush()

    attempt = AssessmentAttempt(
        assessment_id=assessment.id,
        student_id=student_id,
        status="submitted",
        score=3.0,
        max_score=4.0,
        percentage=75.0,
        submitted_at=now,
    )
    db_session.add(attempt)
    db_session.flush()

    ans1 = AttemptAnswer(attempt_id=attempt.id, question_id=q1.id, student_answer="A", is_correct=True, marks_awarded=1.0)
    ans2 = AttemptAnswer(attempt_id=attempt.id, question_id=q2.id, student_answer="B", is_correct=True, marks_awarded=1.0)
    ans3 = AttemptAnswer(attempt_id=attempt.id, question_id=q3.id, student_answer="C", is_correct=True, marks_awarded=1.0)
    ans4 = AttemptAnswer(attempt_id=attempt.id, question_id=q4.id, student_answer="X", is_correct=False, marks_awarded=0.0)
    db_session.add_all([ans1, ans2, ans3, ans4])
    db_session.commit()

    # Query overview
    res = client.get(f"/courses/{course.id}/analytics/overview?learner_id={student_id}")
    assert res.status_code == 200
    data = res.json()

    assert data["total_concepts"] == 5
    assert data["concepts_completed"] == 4  # C1..C4 have completed attempts
    # Overall mastery: (0.90 + 0.75 + 0.50 + 0.25 + 0.10) / 5 = 2.50 / 5 = 0.50
    assert data["overall_mastery"] == 0.50
    # Completion rate: 4 / 5 = 0.80
    assert data["syllabus_completion_rate"] == 0.80

    breakdown = data["mastery_breakdown"]
    assert breakdown["mastered"] == 1    # C1
    assert breakdown["proficient"] == 1  # C2
    assert breakdown["developing"] == 1  # C3
    assert breakdown["struggling"] == 1  # C4
    assert breakdown["unassessed"] == 1  # C5

    summary = data["assessment_summary"]
    assert summary["total_attempts"] == 1
    assert summary["total_questions_answered"] == 4
    assert summary["overall_accuracy"] == 0.75  # 3.0 / 4.0

    # Readiness score:
    # overall_mastery = 0.50
    # completion_rate = 0.80
    # recent_accuracy_rate = 0.75
    # readiness = (0.50*0.50 + 0.30*0.80 + 0.20*0.75) * 100 = (0.25 + 0.24 + 0.15) * 100 = 64.0
    assert data["readiness_score"] == 64.0


def test_topic_analytics_detail(populated_course, db_session):
    """
    Test GET /courses/{course_id}/topics/{topic_id}/analytics
    """
    course = populated_course["course"]
    t1 = populated_course["topics"][0]
    concepts = populated_course["concepts"][:3]
    student_id = "eval_student"

    # Set masteries for Topic 1 concepts: C1=0.90, C2=0.75, C3=0.50
    m1 = LearnerConceptMastery(
        student_id=student_id,
        course_id=course.id,
        concept_id=concepts[0].id,
        mastery_probability=0.90,
        observation_count=3,
        correct_count=3,
    )
    m2 = LearnerConceptMastery(
        student_id=student_id,
        course_id=course.id,
        concept_id=concepts[1].id,
        mastery_probability=0.75,
        observation_count=2,
        correct_count=2,
    )
    m3 = LearnerConceptMastery(
        student_id=student_id,
        course_id=course.id,
        concept_id=concepts[2].id,
        mastery_probability=0.50,
        observation_count=2,
        correct_count=1,
    )
    db_session.add_all([m1, m2, m3])

    # Assessment covering all 3 concepts
    a = Assessment(course_id=course.id, title="Topic 1 Quiz", total_marks=3.0)
    db_session.add(a)
    db_session.flush()

    q1 = Question(assessment_id=a.id, question_type="mcq", prompt="Q1", correct_answer="A", marks=1.0, concept_id=concepts[0].id)
    q2 = Question(assessment_id=a.id, question_type="mcq", prompt="Q2", correct_answer="B", marks=1.0, concept_id=concepts[1].id)
    q3 = Question(assessment_id=a.id, question_type="mcq", prompt="Q3", correct_answer="C", marks=1.0, concept_id=concepts[2].id)
    db_session.add_all([q1, q2, q3])
    db_session.flush()

    att = AssessmentAttempt(assessment_id=a.id, student_id=student_id, status="submitted", score=3.0, max_score=3.0, percentage=100.0)
    db_session.add(att)
    db_session.flush()

    ans1 = AttemptAnswer(attempt_id=att.id, question_id=q1.id, student_answer="A", is_correct=True, marks_awarded=1.0)
    ans2 = AttemptAnswer(attempt_id=att.id, question_id=q2.id, student_answer="B", is_correct=True, marks_awarded=1.0)
    ans3 = AttemptAnswer(attempt_id=att.id, question_id=q3.id, student_answer="C", is_correct=True, marks_awarded=1.0)
    db_session.add_all([ans1, ans2, ans3])
    db_session.commit()

    res = client.get(f"/courses/{course.id}/topics/{t1.id}/analytics?learner_id={student_id}")
    assert res.status_code == 200
    detail = res.json()

    assert detail["course_id"] == course.id
    assert detail["topic_id"] == t1.id
    assert detail["topic_title"] == t1.title
    assert detail["order_index"] == 1
    assert detail["total_concepts"] == 3
    assert detail["mastered_concepts"] == 1  # C1 is 0.90
    assert detail["completion_percentage"] == 100.0  # All 3 have attempts
    # Topic 1 average mastery: (0.90 + 0.75 + 0.50) / 3 = 2.15 / 3 = 0.7167
    assert detail["average_mastery"] == 0.7167
    assert detail["status"] == "in_progress"

    concepts = detail["concepts"]
    assert len(concepts) == 3
    assert concepts[0]["mastery_category"] == "mastered"
    assert concepts[1]["mastery_category"] == "proficient"
    assert concepts[2]["mastery_category"] == "developing"
    assert concepts[0]["completed_attempts_count"] >= 1


def test_topic_status_mastered(populated_course, db_session):
    """
    Topic status becomes 'mastered' when topic average mastery >= 0.85
    and has completed attempts.
    """
    course = populated_course["course"]
    t1 = populated_course["topics"][0]
    concepts = populated_course["concepts"][:3]
    student_id = "star_student"

    # Set all 3 concepts in Topic 1 to >= 0.85
    for c in concepts:
        m = LearnerConceptMastery(
            student_id=student_id,
            course_id=course.id,
            concept_id=c.id,
            mastery_probability=0.90,
            observation_count=2,
            correct_count=2,
        )
        db_session.add(m)

    # Provide an attempt
    assessment = Assessment(course_id=course.id, title="A1", total_marks=1.0)
    db_session.add(assessment)
    db_session.flush()

    q = Question(assessment_id=assessment.id, question_type="mcq", prompt="Q", correct_answer="A", marks=1.0, concept_id=concepts[0].id)
    db_session.add(q)
    db_session.flush()

    attempt = AssessmentAttempt(assessment_id=assessment.id, student_id=student_id, status="submitted", score=1.0, max_score=1.0, percentage=100.0)
    db_session.add(attempt)
    db_session.flush()

    ans = AttemptAnswer(attempt_id=attempt.id, question_id=q.id, student_answer="A", is_correct=True, marks_awarded=1.0)
    db_session.add(ans)
    db_session.commit()

    res = client.get(f"/courses/{course.id}/topics/{t1.id}/analytics?learner_id={student_id}")
    assert res.status_code == 200
    assert res.json()["status"] == "mastered"


def test_velocity_trends_calculation(populated_course, db_session):
    """
    Verify chronological trends over configurable days.
    """
    course = populated_course["course"]
    student_id = "trend_student"

    now = datetime.now(timezone.utc)
    day1 = now - timedelta(days=2)
    day2 = now - timedelta(days=1)

    a1 = Assessment(course_id=course.id, title="Exam D1", total_marks=10.0)
    a2 = Assessment(course_id=course.id, title="Exam D2", total_marks=10.0)
    db_session.add_all([a1, a2])
    db_session.flush()

    att1 = AssessmentAttempt(
        assessment_id=a1.id,
        student_id=student_id,
        status="submitted",
        score=8.0,
        max_score=10.0,
        percentage=80.0,
        submitted_at=day1,
    )
    att2 = AssessmentAttempt(
        assessment_id=a2.id,
        student_id=student_id,
        status="submitted",
        score=10.0,
        max_score=10.0,
        percentage=100.0,
        submitted_at=day2,
    )
    db_session.add_all([att1, att2])
    db_session.commit()

    res = client.get(f"/courses/{course.id}/analytics/trends?learner_id={student_id}&days=7")
    assert res.status_code == 200
    trends_data = res.json()

    assert trends_data["course_id"] == course.id
    assert trends_data["learner_id"] == student_id
    assert trends_data["days"] == 7
    trends = trends_data["trends"]
    assert len(trends) == 2

    d1_str = day1.strftime("%Y-%m-%d")
    d2_str = day2.strftime("%Y-%m-%d")
    assert trends[0]["date"] == d1_str
    assert trends[0]["attempt_count"] == 1
    assert trends[0]["average_score_percentage"] == 80.0

    assert trends[1]["date"] == d2_str
    assert trends[1]["attempt_count"] == 1
    assert trends[1]["average_score_percentage"] == 100.0


def test_velocity_trends_invalid_days(populated_course):
    course = populated_course["course"]
    res = client.get(f"/courses/{course.id}/analytics/trends?days=0")
    assert res.status_code == 400
    res_neg = client.get(f"/courses/{course.id}/analytics/trends?days=-5")
    assert res_neg.status_code == 400
    res_huge = client.get(f"/courses/{course.id}/analytics/trends?days=400")
    assert res_huge.status_code == 400


def test_learner_isolation(populated_course, db_session):
    """
    Ensure Student A data is never visible to Student B.
    """
    course = populated_course["course"]
    c1 = populated_course["concepts"][0]

    # Student A has mastery 0.95
    mA = LearnerConceptMastery(
        student_id="student_A",
        course_id=course.id,
        concept_id=c1.id,
        mastery_probability=0.95,
        observation_count=5,
        correct_count=5,
    )
    db_session.add(mA)
    db_session.commit()

    resA = client.get(f"/courses/{course.id}/analytics/overview?learner_id=student_A")
    assert resA.status_code == 200
    assert resA.json()["mastery_breakdown"]["mastered"] == 1

    resB = client.get(f"/courses/{course.id}/analytics/overview?learner_id=student_B")
    assert resB.status_code == 200
    # Student B has no record, should be 0 mastered, 5 unassessed
    assert resB.json()["mastery_breakdown"]["mastered"] == 0
    assert resB.json()["mastery_breakdown"]["unassessed"] == 5


def test_topic_and_course_isolation(populated_course, db_session):
    """
    Ensure a topic belonging to Course 1 cannot be accessed under Course 2.
    """
    c1_data = populated_course
    course2 = Course(id=str(uuid.uuid4()), title="Macroeconomics 201")
    db_session.add(course2)
    db_session.commit()

    topic1 = c1_data["topics"][0]

    # Querying topic1 under course2 should fail (404)
    res = client.get(f"/courses/{course2.id}/topics/{topic1.id}/analytics")
    assert res.status_code == 404
    assert "does not belong to course" in res.json()["detail"].lower()

    # Querying non-existent topic returns 404
    res_bad_topic = client.get(f"/courses/{c1_data['course'].id}/topics/{uuid.uuid4()}/analytics")
    assert res_bad_topic.status_code == 404


def test_no_mutation_on_analytics_calls(populated_course, db_session):
    """
    Verify analytics queries are read-only and create no records.
    """
    course = populated_course["course"]
    student = "read_only_student"

    before_masteries = db_session.query(LearnerConceptMastery).count()
    before_attempts = db_session.query(AssessmentAttempt).count()

    res1 = client.get(f"/courses/{course.id}/analytics/overview?learner_id={student}")
    assert res1.status_code == 200
    res2 = client.get(f"/courses/{course.id}/topics/{populated_course['topics'][0].id}/analytics?learner_id={student}")
    assert res2.status_code == 200
    res3 = client.get(f"/courses/{course.id}/analytics/trends?learner_id={student}&days=30")
    assert res3.status_code == 200

    after_masteries = db_session.query(LearnerConceptMastery).count()
    after_attempts = db_session.query(AssessmentAttempt).count()

    assert before_masteries == after_masteries
    assert before_attempts == after_attempts


def test_learner_isolation_multi_student(populated_course, db_session):
    """
    Explicit test for multiple learners in the same course:
    Student 1 has completed attempt on C1.
    Student 2 has completed attempt on C2.
    Assert both see only their own completion and accuracy.
    """
    course = populated_course["course"]
    c1 = populated_course["concepts"][0]
    c2 = populated_course["concepts"][1]

    # Student 1 mastery and attempt
    m1 = LearnerConceptMastery(
        student_id="student_1",
        course_id=course.id,
        concept_id=c1.id,
        mastery_probability=0.88,
        observation_count=2,
        correct_count=2,
    )
    # Student 2 mastery and attempt
    m2 = LearnerConceptMastery(
        student_id="student_2",
        course_id=course.id,
        concept_id=c2.id,
        mastery_probability=0.35,
        observation_count=1,
        correct_count=0,
    )
    db_session.add_all([m1, m2])

    a = Assessment(course_id=course.id, title="Multi-student Quiz", total_marks=2.0)
    db_session.add(a)
    db_session.flush()

    q1 = Question(assessment_id=a.id, question_type="mcq", prompt="Q1", correct_answer="A", marks=1.0, concept_id=c1.id)
    q2 = Question(assessment_id=a.id, question_type="mcq", prompt="Q2", correct_answer="B", marks=1.0, concept_id=c2.id)
    db_session.add_all([q1, q2])
    db_session.flush()

    att1 = AssessmentAttempt(assessment_id=a.id, student_id="student_1", status="submitted", score=1.0, max_score=1.0, percentage=100.0)
    att2 = AssessmentAttempt(assessment_id=a.id, student_id="student_2", status="submitted", score=0.0, max_score=1.0, percentage=0.0)
    db_session.add_all([att1, att2])
    db_session.flush()

    ans1 = AttemptAnswer(attempt_id=att1.id, question_id=q1.id, student_answer="A", is_correct=True, marks_awarded=1.0)
    ans2 = AttemptAnswer(attempt_id=att2.id, question_id=q2.id, student_answer="X", is_correct=False, marks_awarded=0.0)
    db_session.add_all([ans1, ans2])
    db_session.commit()

    res1 = client.get(f"/courses/{course.id}/analytics/overview?learner_id=student_1")
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["concepts_completed"] == 1
    assert data1["mastery_breakdown"]["mastered"] == 1
    assert data1["mastery_breakdown"]["struggling"] == 0
    assert data1["assessment_summary"]["overall_accuracy"] == 1.0

    res2 = client.get(f"/courses/{course.id}/analytics/overview?learner_id=student_2")
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["concepts_completed"] == 1
    assert data2["mastery_breakdown"]["mastered"] == 0
    assert data2["mastery_breakdown"]["struggling"] == 1
    assert data2["assessment_summary"]["overall_accuracy"] == 0.0



def test_course_completion_100_percent_and_readiness_upper_bound(populated_course, db_session):
    """
    1. COURSE COMPLETION = 100%:
       Assert that every concept having a completed attempt produces syllabus_completion_rate == 1.0.
    2. READINESS UPPER BOUND:
       When overall_mastery = 1.0, completion_rate = 1.0, and recent_accuracy_rate = 1.0,
       assert readiness_score == 100.0 (bounded upper clamp).
    """
    course = populated_course["course"]
    concepts = populated_course["concepts"]  # 5 concepts
    student_id = "master_student"

    # Set all 5 concepts to mastery 1.0
    for c in concepts:
        m = LearnerConceptMastery(
            student_id=student_id,
            course_id=course.id,
            concept_id=c.id,
            mastery_probability=1.0,
            observation_count=5,
            correct_count=5,
        )
        db_session.add(m)

    # Assessment covering all 5 concepts
    a = Assessment(course_id=course.id, title="Comprehensive Final", total_marks=5.0)
    db_session.add(a)
    db_session.flush()

    questions = []
    for idx, c in enumerate(concepts):
        q = Question(
            assessment_id=a.id,
            question_type="mcq",
            prompt=f"Question {idx+1}",
            correct_answer="A",
            marks=1.0,
            concept_id=c.id,
        )
        questions.append(q)
    db_session.add_all(questions)
    db_session.flush()

    # Completed attempt with 100% score (5.0 / 5.0) submitted recently
    now = datetime.now(timezone.utc)
    attempt = AssessmentAttempt(
        assessment_id=a.id,
        student_id=student_id,
        status="submitted",
        score=5.0,
        max_score=5.0,
        percentage=100.0,
        submitted_at=now,
    )
    db_session.add(attempt)
    db_session.flush()

    answers = []
    for q in questions:
        ans = AttemptAnswer(
            attempt_id=attempt.id,
            question_id=q.id,
            student_answer="A",
            is_correct=True,
            marks_awarded=1.0,
        )
        answers.append(ans)
    db_session.add_all(answers)
    db_session.commit()

    res = client.get(f"/courses/{course.id}/analytics/overview?learner_id={student_id}&trend_days=30")
    assert res.status_code == 200
    data = res.json()

    # Explicit assertion 1: 100% course syllabus completion
    assert data["total_concepts"] == 5
    assert data["concepts_completed"] == 5
    assert data["syllabus_completion_rate"] == 1.0

    # Explicit assertion 2: Readiness upper bound clamp (1.0 * 50 + 1.0 * 30 + 1.0 * 20) = 100.0
    assert data["overall_mastery"] == 1.0
    assert data["assessment_summary"]["overall_accuracy"] == 1.0
    assert data["readiness_score"] == 100.0
    assert data["mastery_breakdown"]["mastered"] == 5
    assert data["mastery_breakdown"]["unassessed"] == 0


def test_mastery_category_exact_boundaries(db_session):
    """
    Explicitly test exact threshold values and boundary behavior:
    - P(L) = 0.85 -> "mastered"
    - P(L) = 0.8499 -> "proficient"
    - P(L) = 0.70 -> "proficient"
    - P(L) = 0.6999 -> "developing"
    - P(L) = 0.40 -> "developing"
    - P(L) = 0.3999 -> "struggling" when concept has at least one completed attempt
    - P(L) = 0.3999 without attempt -> "unassessed"
    """
    course = Course(id=str(uuid.uuid4()), title="Boundary Test Course")
    db_session.add(course)

    topic = Topic(id=str(uuid.uuid4()), course_id=course.id, title="Boundary Topic", order_index=1)
    db_session.add(topic)

    # 7 concepts to test each boundary condition
    c_85 = Concept(id=str(uuid.uuid4()), course_id=course.id, topic_id=topic.id, name="Boundary 0.85", order_index=1)
    c_8499 = Concept(id=str(uuid.uuid4()), course_id=course.id, topic_id=topic.id, name="Boundary 0.8499", order_index=2)
    c_70 = Concept(id=str(uuid.uuid4()), course_id=course.id, topic_id=topic.id, name="Boundary 0.70", order_index=3)
    c_6999 = Concept(id=str(uuid.uuid4()), course_id=course.id, topic_id=topic.id, name="Boundary 0.6999", order_index=4)
    c_40 = Concept(id=str(uuid.uuid4()), course_id=course.id, topic_id=topic.id, name="Boundary 0.40", order_index=5)
    c_3999 = Concept(id=str(uuid.uuid4()), course_id=course.id, topic_id=topic.id, name="Boundary 0.3999 with attempt", order_index=6)
    c_unassessed = Concept(id=str(uuid.uuid4()), course_id=course.id, topic_id=topic.id, name="Boundary 0.3999 without attempt", order_index=7)
    db_session.add_all([c_85, c_8499, c_70, c_6999, c_40, c_3999, c_unassessed])

    student_id = "boundary_student"

    m_85 = LearnerConceptMastery(student_id=student_id, course_id=course.id, concept_id=c_85.id, mastery_probability=0.85)
    m_8499 = LearnerConceptMastery(student_id=student_id, course_id=course.id, concept_id=c_8499.id, mastery_probability=0.8499)
    m_70 = LearnerConceptMastery(student_id=student_id, course_id=course.id, concept_id=c_70.id, mastery_probability=0.70)
    m_6999 = LearnerConceptMastery(student_id=student_id, course_id=course.id, concept_id=c_6999.id, mastery_probability=0.6999)
    m_40 = LearnerConceptMastery(student_id=student_id, course_id=course.id, concept_id=c_40.id, mastery_probability=0.40)
    m_3999 = LearnerConceptMastery(student_id=student_id, course_id=course.id, concept_id=c_3999.id, mastery_probability=0.3999)
    m_unassessed = LearnerConceptMastery(student_id=student_id, course_id=course.id, concept_id=c_unassessed.id, mastery_probability=0.3999)
    db_session.add_all([m_85, m_8499, m_70, m_6999, m_40, m_3999, m_unassessed])

    # Add completed attempts for concepts 1 through 6, leaving concept 7 unassessed
    a = Assessment(course_id=course.id, title="Boundary Assessment", total_marks=6.0)
    db_session.add(a)
    db_session.flush()

    active_concepts = [c_85, c_8499, c_70, c_6999, c_40, c_3999]
    questions = []
    for idx, c in enumerate(active_concepts):
        q = Question(assessment_id=a.id, question_type="mcq", prompt=f"Q{idx}", correct_answer="A", marks=1.0, concept_id=c.id)
        questions.append(q)
    db_session.add_all(questions)
    db_session.flush()

    attempt = AssessmentAttempt(assessment_id=a.id, student_id=student_id, status="submitted", score=5.0, max_score=6.0, percentage=83.33)
    db_session.add(attempt)
    db_session.flush()

    for q in questions:
        ans = AttemptAnswer(attempt_id=attempt.id, question_id=q.id, student_answer="A", is_correct=True, marks_awarded=1.0)
        db_session.add(ans)
    db_session.commit()

    # 1. Verify Topic Analytics Concept-by-Concept Detail Categories
    res_topic = client.get(f"/courses/{course.id}/topics/{topic.id}/analytics?learner_id={student_id}")
    assert res_topic.status_code == 200
    detail = res_topic.json()

    cat_map = {item["concept_id"]: item["mastery_category"] for item in detail["concepts"]}
    assert cat_map[c_85.id] == "mastered"
    assert cat_map[c_8499.id] == "proficient"
    assert cat_map[c_70.id] == "proficient"
    assert cat_map[c_6999.id] == "developing"
    assert cat_map[c_40.id] == "developing"
    assert cat_map[c_3999.id] == "struggling"
    assert cat_map[c_unassessed.id] == "unassessed"

    # 2. Verify Course Overview Breakdown Counts
    res_course = client.get(f"/courses/{course.id}/analytics/overview?learner_id={student_id}")
    assert res_course.status_code == 200
    b = res_course.json()["mastery_breakdown"]
    assert b["mastered"] == 1    # c_85
    assert b["proficient"] == 2  # c_8499, c_70
    assert b["developing"] == 2  # c_6999, c_40
    assert b["struggling"] == 1  # c_3999
    assert b["unassessed"] == 1  # c_unassessed
