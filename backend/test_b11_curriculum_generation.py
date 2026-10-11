"""
Milestone B11 Test Suite: Automated Curriculum Ingestion & Knowledge Graph Extraction Engine.

Verifies:
1. Successful curriculum extraction from indexed ContentUnits.
2. Correct topic/concept persistence in database.
3. Structured LLM response parsing (including markdown fences).
4. Malformed LLM output handling (HTTP 502).
5. Duplicate concept normalization (case-insensitive deduplication).
6. Unknown prerequisite reference rejection.
7. Cyclic prerequisite output is sanitized and never persisted.
8. Duplicate prerequisite edges are removed.
9. Atomic rollback on persistence failure.
10. Preview mode does not modify DB.
11. Replace behavior safely updates existing curriculum.
12. Replace mode guards against courses with active student assessment attempts (HTTP 409).
13. Course isolation & missing course 404.
14. Source scoping & cross-course source rejection.
15. Large-course sampling remains bounded.
16. Downstream smoke test: generated curriculum enables B7 Study Planner.
17. Downstream smoke test: generated curriculum enables B8 Adaptive Practice.
18. Downstream smoke test: generated curriculum is visible in B9 Learner Analytics.
19. Status endpoint reports accurate metrics and acyclicity.
"""

import os
import uuid
import json
from unittest.mock import patch, MagicMock
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

TEST_DB_FILE = f"test_b11_temp_{uuid.uuid4().hex[:8]}.db"
TEST_DATABASE_URL = f"sqlite:///{TEST_DB_FILE}"
os.environ["DATABASE_URL"] = TEST_DATABASE_URL

from app.db.database import Base, get_db
from app.models.course import Course
from app.models.source import Source
from app.models.content_unit import ContentUnit
from app.models.topic import Topic
from app.models.concept import Concept, ConceptPrerequisite
from app.models.assessment import Assessment, Question, AssessmentAttempt
from app.services.embedding_service import create_embeddings, serialize_embedding
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
    test_engine.dispose()
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
    Creates a course with 1 completed source and 4 indexed ContentUnits.
    """
    course = Course(
        id=str(uuid.uuid4()),
        title="Algorithms and Data Structures",
        description="Comprehensive computer science fundamentals",
    )
    db_session.add(course)

    source = Source(
        id=str(uuid.uuid4()),
        course_id=course.id,
        filename="DSA_Textbook.pdf",
        source_type="pdf",
        file_path="data/uploads/DSA_Textbook.pdf",
        processing_status="completed",
    )
    db_session.add(source)

    texts = [
        "Chapter 1: Asymptotic Analysis. Big-O notation characterizes the upper bound of algorithm runtime. Recurrence relations describe divide-and-conquer recurrences.",
        "Chapter 2: Linear Data Structures. Stacks follow Last-In-First-Out order. Queues follow First-In-First-Out order.",
        "Chapter 3: Tree Data Structures. Binary Search Trees maintain the BST invariant: left subtree keys are smaller, right subtree keys are larger.",
        "Chapter 4: Balanced Trees. AVL trees maintain balance factors between -1, 0, and +1 using rotations.",
    ]
    vecs = create_embeddings(texts)

    units = []
    for idx, (t, v) in enumerate(zip(texts, vecs)):
        u = ContentUnit(
            id=str(uuid.uuid4()),
            course_id=course.id,
            source_id=source.id,
            unit_index=idx,
            page_number=idx + 1,
            content_type="pdf",
            text=t,
            embedding=serialize_embedding(v),
        )
        units.append(u)

    db_session.add_all(units)
    db_session.commit()

    return {
        "course": course,
        "source": source,
        "units": units,
    }


SAMPLE_VALID_LLM_JSON = json.dumps({
  "topics": [
    {
      "title": "Complexity Analysis",
      "description": "Techniques for analyzing algorithm efficiency",
      "order_index": 0,
      "concepts": [
        {
          "name": "Big-O Notation",
          "description": "Upper bound asymptotic runtime behavior",
          "order_index": 0
        },
        {
          "name": "Recurrence Relations",
          "description": "Equations defining divide and conquer algorithms",
          "order_index": 1
        }
      ]
    },
    {
      "title": "Tree Data Structures",
      "description": "Hierarchical node-based data representations",
      "order_index": 1,
      "concepts": [
        {
          "name": "Binary Search Trees",
          "description": "Binary trees satisfying the left-smaller right-larger invariant",
          "order_index": 0
        },
        {
          "name": "AVL Trees",
          "description": "Self-balancing binary search trees using rotations",
          "order_index": 1
        }
      ]
    }
  ],
  "prerequisites": [
    {
      "concept": "AVL Trees",
      "prerequisite": "Binary Search Trees"
    },
    {
      "concept": "Recurrence Relations",
      "prerequisite": "Big-O Notation"
    }
  ]
})


# =====================================================================
# Test 1 & 2: Successful Extraction, Persistence & Preview Mode
# =====================================================================

def test_successful_curriculum_extraction_and_persistence(populated_course, db_session):
    course = populated_course["course"]

    with patch("app.services.curriculum_generator_service.llm_service.generate_response", return_value=SAMPLE_VALID_LLM_JSON):
        res = client.post(
            f"/courses/{course.id}/curriculum/generate",
            json={
                "max_topics": 5,
                "concepts_per_topic": 4,
                "infer_prerequisites": True,
                "mode": "replace",
            },
        )

    assert res.status_code == 200
    data = res.json()
    assert data["course_id"] == course.id
    assert data["mode"] == "replace"
    assert data["status"] == "completed"
    assert data["topics_count"] == 2
    assert data["concepts_count"] == 4
    assert data["prerequisites_count"] == 2
    assert data["is_acyclic"] is True
    assert len(data["topics"]) == 2

    # Verify DB persistence
    topics = db_session.query(Topic).filter(Topic.course_id == course.id).all()
    assert len(topics) == 2
    assert {t.title for t in topics} == {"Complexity Analysis", "Tree Data Structures"}

    concepts = db_session.query(Concept).filter(Concept.course_id == course.id).all()
    assert len(concepts) == 4

    prereqs = (
        db_session.query(ConceptPrerequisite)
        .join(Concept, ConceptPrerequisite.concept_id == Concept.id)
        .filter(Concept.course_id == course.id)
        .all()
    )
    assert len(prereqs) == 2


def test_preview_mode_does_not_modify_db(populated_course, db_session):
    course = populated_course["course"]

    with patch("app.services.curriculum_generator_service.llm_service.generate_response", return_value=SAMPLE_VALID_LLM_JSON):
        res = client.post(
            f"/courses/{course.id}/curriculum/generate",
            json={
                "max_topics": 5,
                "concepts_per_topic": 4,
                "infer_prerequisites": True,
                "mode": "preview",
            },
        )

    assert res.status_code == 200
    data = res.json()
    assert data["mode"] == "preview"
    assert data["status"] == "preview"
    assert data["topics_count"] == 2
    assert data["concepts_count"] == 4

    # Assert NO database mutation occurred
    assert db_session.query(Topic).filter(Topic.course_id == course.id).count() == 0
    assert db_session.query(Concept).filter(Concept.course_id == course.id).count() == 0
    assert db_session.query(ConceptPrerequisite).count() == 0


# =====================================================================
# Test 3: Empty Course / Material Handling
# =====================================================================

def test_empty_course_material_handling(db_session):
    empty_c = Course(id=str(uuid.uuid4()), title="Empty Material Course")
    db_session.add(empty_c)
    db_session.commit()

    with patch("app.services.curriculum_generator_service.llm_service.generate_response") as mock_llm:
        res = client.post(
            f"/courses/{empty_c.id}/curriculum/generate",
            json={"mode": "preview"},
        )
        assert res.status_code == 400
        assert "No indexed course materials available" in res.json()["detail"]
        assert mock_llm.call_count == 0


# =====================================================================
# Test 4 & 5: Structured JSON Parsing & Malformed LLM Handling
# =====================================================================

def test_structured_llm_json_parsing_with_code_fences(populated_course):
    course = populated_course["course"]
    fenced_json = f"```json\n{SAMPLE_VALID_LLM_JSON}\n```"

    with patch("app.services.curriculum_generator_service.llm_service.generate_response", return_value=fenced_json):
        res = client.post(
            f"/courses/{course.id}/curriculum/generate",
            json={"mode": "preview"},
        )
    assert res.status_code == 200
    assert res.json()["topics_count"] == 2


def test_malformed_llm_output_handling(populated_course):
    course = populated_course["course"]

    with patch("app.services.curriculum_generator_service.llm_service.generate_response", return_value="Not a JSON output at all"):
        res = client.post(
            f"/courses/{course.id}/curriculum/generate",
            json={"mode": "preview"},
        )
    assert res.status_code == 502
    assert "Failed to extract structured curriculum" in res.json()["detail"]


# =====================================================================
# Test 6: Duplicate Concept Normalization
# =====================================================================

def test_duplicate_concept_normalization(populated_course, db_session):
    course = populated_course["course"]

    # LLM returns "Big-O Notation" under Topic 1, and duplicate "big-o notation" under Topic 2
    json_with_duplicates = json.dumps({
        "topics": [
            {
                "title": "Topic 1",
                "concepts": [
                    {"name": "Big-O Notation", "order_index": 0},
                    {"name": "Recursion", "order_index": 1}
                ]
            },
            {
                "title": "Topic 2",
                "concepts": [
                    {"name": "big-o notation", "order_index": 0},
                    {"name": "Merge Sort", "order_index": 1}
                ]
            }
        ],
        "prerequisites": []
    })

    with patch("app.services.curriculum_generator_service.llm_service.generate_response", return_value=json_with_duplicates):
        res = client.post(
            f"/courses/{course.id}/curriculum/generate",
            json={"mode": "replace"},
        )
    assert res.status_code == 200
    data = res.json()
    assert data["concepts_count"] == 3  # Big-O Notation, Recursion, Merge Sort (no duplicate)

    concepts = db_session.query(Concept).filter(Concept.course_id == course.id).all()
    concept_names_lower = [c.name.lower() for c in concepts]
    assert concept_names_lower.count("big-o notation") == 1


# =====================================================================
# Test 7, 8, 9: Prerequisite Validation & Cycle Prevention
# =====================================================================

def test_unknown_and_self_prerequisites_rejected(populated_course, db_session):
    course = populated_course["course"]

    json_with_bad_prereqs = json.dumps({
        "topics": [
            {
                "title": "Topic A",
                "concepts": [
                    {"name": "Concept 1", "order_index": 0},
                    {"name": "Concept 2", "order_index": 1}
                ]
            }
        ],
        "prerequisites": [
            {"concept": "Concept 2", "prerequisite": "Concept 1"},  # Valid
            {"concept": "Concept 1", "prerequisite": "Concept 1"},  # Self-prereq (rejected)
            {"concept": "Concept 2", "prerequisite": "Ghost Concept"},  # Unknown (rejected)
            {"concept": "Unknown Concept", "prerequisite": "Concept 1"}  # Unknown (rejected)
        ]
    })

    with patch("app.services.curriculum_generator_service.llm_service.generate_response", return_value=json_with_bad_prereqs):
        res = client.post(
            f"/courses/{course.id}/curriculum/generate",
            json={"mode": "replace"},
        )
    assert res.status_code == 200
    data = res.json()
    assert data["prerequisites_count"] == 1
    assert data["prerequisites"][0]["concept_name"] == "Concept 2"
    assert data["prerequisites"][0]["prerequisite_name"] == "Concept 1"


def test_cyclic_prerequisite_output_is_never_persisted(populated_course, db_session):
    course = populated_course["course"]

    # Cycle: A requires B, and B requires A
    cyclic_json = json.dumps({
        "topics": [
            {
                "title": "Graph Algorithms",
                "concepts": [
                    {"name": "Concept Alpha", "order_index": 0},
                    {"name": "Concept Beta", "order_index": 1}
                ]
            }
        ],
        "prerequisites": [
            {"concept": "Concept Beta", "prerequisite": "Concept Alpha"},
            {"concept": "Concept Alpha", "prerequisite": "Concept Beta"}  # Causes Cycle
        ]
    })

    with patch("app.services.curriculum_generator_service.llm_service.generate_response", return_value=cyclic_json):
        res = client.post(
            f"/courses/{course.id}/curriculum/generate",
            json={"mode": "replace"},
        )
    assert res.status_code == 200
    data = res.json()
    assert data["is_acyclic"] is True
    # Offending cycle edge dropped, only 1 forward edge preserved
    assert data["prerequisites_count"] == 1


def test_duplicate_prerequisite_edges_removed(populated_course):
    course = populated_course["course"]

    dup_edge_json = json.dumps({
        "topics": [
            {
                "title": "Topic A",
                "concepts": [
                    {"name": "Concept A", "order_index": 0},
                    {"name": "Concept B", "order_index": 1}
                ]
            }
        ],
        "prerequisites": [
            {"concept": "Concept B", "prerequisite": "Concept A"},
            {"concept": "Concept B", "prerequisite": "Concept A"}  # Duplicate
        ]
    })

    with patch("app.services.curriculum_generator_service.llm_service.generate_response", return_value=dup_edge_json):
        res = client.post(
            f"/courses/{course.id}/curriculum/generate",
            json={"mode": "replace"},
        )
    assert res.status_code == 200
    assert res.json()["prerequisites_count"] == 1


# =====================================================================
# Test 10: Atomic Rollback on Persistence Failure
# =====================================================================

def test_atomic_rollback_on_persistence_failure(populated_course, db_session):
    course = populated_course["course"]

    with patch("app.services.curriculum_generator_service.llm_service.generate_response", return_value=SAMPLE_VALID_LLM_JSON):
        # Force a database failure during commit in endpoint
        with patch("sqlalchemy.orm.Session.commit", side_effect=RuntimeError("Simulated DB Disk Crash")):
            res = client.post(
                f"/courses/{course.id}/curriculum/generate",
                json={"mode": "replace"},
            )
            assert res.status_code == 500
            assert "Failed to persist curriculum atomically" in res.json()["detail"]

    # Ensure atomic rollback: zero topics or concepts created
    assert db_session.query(Topic).filter(Topic.course_id == course.id).count() == 0
    assert db_session.query(Concept).filter(Concept.course_id == course.id).count() == 0


# =====================================================================
# Test 11 & 12: Safe Replace Behavior & Guard Against Active Attempts
# =====================================================================

def test_safe_replace_updates_existing_curriculum(populated_course, db_session):
    course = populated_course["course"]

    # 1. Initial Generation
    with patch("app.services.curriculum_generator_service.llm_service.generate_response", return_value=SAMPLE_VALID_LLM_JSON):
        res1 = client.post(
            f"/courses/{course.id}/curriculum/generate",
            json={"mode": "replace"},
        )
    assert res1.status_code == 200
    assert db_session.query(Concept).filter(Concept.course_id == course.id).count() == 4

    # 2. Second Generation with updated topics
    second_json = json.dumps({
        "topics": [
            {
                "title": "Modern Algorithms",
                "concepts": [
                    {"name": "Dynamic Programming", "order_index": 0}
                ]
            }
        ],
        "prerequisites": []
    })

    with patch("app.services.curriculum_generator_service.llm_service.generate_response", return_value=second_json):
        res2 = client.post(
            f"/courses/{course.id}/curriculum/generate",
            json={"mode": "replace"},
        )
    assert res2.status_code == 200
    assert res2.json()["topics_count"] == 1
    assert res2.json()["concepts_count"] == 1

    # Verify previous concepts were cleanly replaced
    topics = db_session.query(Topic).filter(Topic.course_id == course.id).all()
    assert len(topics) == 1
    assert topics[0].title == "Modern Algorithms"


def test_replace_mode_guards_against_active_student_attempts(populated_course, db_session):
    course = populated_course["course"]

    # 1. Populate initial curriculum
    with patch("app.services.curriculum_generator_service.llm_service.generate_response", return_value=SAMPLE_VALID_LLM_JSON):
        client.post(
            f"/courses/{course.id}/curriculum/generate",
            json={"mode": "replace"},
        )

    concept = db_session.query(Concept).filter(Concept.course_id == course.id).first()

    # 2. Create an assessment with a submitted attempt
    assessment = Assessment(
        id=str(uuid.uuid4()),
        course_id=course.id,
        title="Midterm Assessment",
    )
    db_session.add(assessment)
    db_session.flush()

    question = Question(
        id=str(uuid.uuid4()),
        assessment_id=assessment.id,
        question_type="mcq",
        prompt="Sample Question?",
        correct_answer="A",
        concept_id=concept.id,
    )
    db_session.add(question)

    attempt = AssessmentAttempt(
        id=str(uuid.uuid4()),
        assessment_id=assessment.id,
        student_id="student_alice",
        status="submitted",
        score=10.0,
        max_score=10.0,
    )
    db_session.add(attempt)
    db_session.commit()

    # 3. Attempt replace generation -> Must be rejected with 409
    with patch("app.services.curriculum_generator_service.llm_service.generate_response", return_value=SAMPLE_VALID_LLM_JSON):
        res_replace = client.post(
            f"/courses/{course.id}/curriculum/generate",
            json={"mode": "replace"},
        )
    assert res_replace.status_code == 409
    assert "Cannot replace curriculum" in res_replace.json()["detail"]


# =====================================================================
# Test 13 & 14: Course Isolation & Source Scoping
# =====================================================================

def test_course_isolation_and_missing_course_404(populated_course):
    fake_id = str(uuid.uuid4())
    res = client.post(f"/courses/{fake_id}/curriculum/generate", json={})
    assert res.status_code == 404


def test_source_scoping_and_cross_course_source_rejection(populated_course, db_session):
    c1 = populated_course["course"]
    s1 = populated_course["source"]

    # Other Course with its own source
    c2 = Course(id=str(uuid.uuid4()), title="Physics 101")
    s2 = Source(id=str(uuid.uuid4()), course_id=c2.id, filename="Physics.pdf", processing_status="completed")
    db_session.add_all([c2, s2])
    db_session.commit()

    # Request scoping to s1 on course c1 -> Valid
    with patch("app.services.curriculum_generator_service.llm_service.generate_response", return_value=SAMPLE_VALID_LLM_JSON):
        res_valid = client.post(
            f"/courses/{c1.id}/curriculum/generate",
            json={"source_ids": [s1.id], "mode": "preview"},
        )
        assert res_valid.status_code == 200

    # Request scoping with s2 (which belongs to c2) on course c1 -> Rejected with 400
    res_invalid = client.post(
        f"/courses/{c1.id}/curriculum/generate",
        json={"source_ids": [s2.id], "mode": "preview"},
    )
    assert res_invalid.status_code == 400
    assert "does not belong to course" in res_invalid.json()["detail"]


# =====================================================================
# Test 15: Large Course Bounded Sampling
# =====================================================================

def test_large_course_sampling_remains_bounded(db_session):
    course = Course(id=str(uuid.uuid4()), title="Large 200-Page Course")
    source = Source(id=str(uuid.uuid4()), course_id=course.id, filename="BigBook.pdf", processing_status="completed")
    db_session.add_all([course, source])
    db_session.flush()

    # Create 100 ContentUnits of 500 characters each = 50,000 characters total
    units = [
        ContentUnit(
            id=str(uuid.uuid4()),
            course_id=course.id,
            source_id=source.id,
            unit_index=i,
            page_number=i + 1,
            text=f"Chunk {i}: Detailed academic text on computational topics. " * 8,
        )
        for i in range(100)
    ]
    db_session.add_all(units)
    db_session.commit()

    captured_prompt = []

    def mock_llm(prompt: str) -> str:
        captured_prompt.append(prompt)
        return SAMPLE_VALID_LLM_JSON

    with patch("app.services.curriculum_generator_service.llm_service.generate_response", side_effect=mock_llm):
        res = client.post(
            f"/courses/{course.id}/curriculum/generate",
            json={"mode": "preview"},
        )
    assert res.status_code == 200
    assert len(captured_prompt) == 1
    # Verify prompt length is bounded despite 50,000 char source
    assert len(captured_prompt[0]) < 25000


# =====================================================================
# Test 16, 17, 18: Downstream Smoke Tests (B7, B8, B9 Integration)
# =====================================================================

def test_downstream_smoke_tests_enable_b7_b8_b9(populated_course, db_session):
    course = populated_course["course"]

    # 1. Before B11 generation: Study plan is empty, practice fails with 400
    res_plan_before = client.get(f"/courses/{course.id}/study-plan")
    assert res_plan_before.status_code == 200
    assert len(res_plan_before.json()["prioritized_concepts"]) == 0

    res_practice_before = client.post(
        f"/courses/{course.id}/practice/generate",
        json={"mode": "adaptive", "student_id": "test_student"},
    )
    assert res_practice_before.status_code == 400

    # 2. Run B11 Generation with mode="replace"
    with patch("app.services.curriculum_generator_service.llm_service.generate_response", return_value=SAMPLE_VALID_LLM_JSON):
        res_gen = client.post(
            f"/courses/{course.id}/curriculum/generate",
            json={"mode": "replace"},
        )
    assert res_gen.status_code == 200

    # 3. Downstream Smoke Test: B7 Study Planner now produces active recommendations
    res_plan_after = client.get(f"/courses/{course.id}/study-plan")
    assert res_plan_after.status_code == 200
    plan_data = res_plan_after.json()
    assert len(plan_data["prioritized_concepts"]) > 0
    assert plan_data["top_recommendation"] is not None

    # 4. Downstream Smoke Test: B8 Adaptive Practice now generates questions successfully
    mock_q = json.dumps([
        {
            "prompt": "What does Big-O notation signify?",
            "question_type": "mcq",
            "options": ["Upper bound", "Lower bound", "Average", "Exact"],
            "correct_answer": "Upper bound",
            "explanation": "Big-O gives asymptotic upper bound."
        }
    ])
    with patch("app.services.practice_service.llm_service.generate_response", return_value=mock_q):
        res_practice_after = client.post(
            f"/courses/{course.id}/practice/generate",
            json={"mode": "adaptive", "student_id": "test_student"},
        )
    assert res_practice_after.status_code == 201
    assert res_practice_after.json()["total_questions"] > 0
    assert len(res_practice_after.json()["questions"]) > 0

    # 5. Downstream Smoke Test: B9 Learner Analytics sees the generated curriculum
    res_analytics = client.get(f"/courses/{course.id}/analytics/overview?student_id=test_student")
    assert res_analytics.status_code == 200
    analytics_data = res_analytics.json()
    assert len(analytics_data["topics"]) == 2
    assert analytics_data["topics"][0]["total_concepts"] == 2


# =====================================================================
# Test 19: Curriculum Status Endpoint
# =====================================================================

def test_curriculum_status_endpoint(populated_course, db_session):
    course = populated_course["course"]

    # Before generation
    res_status_1 = client.get(f"/courses/{course.id}/curriculum/status")
    assert res_status_1.status_code == 200
    d1 = res_status_1.json()
    assert d1["has_curriculum"] is False
    assert d1["topic_count"] == 0
    assert d1["concept_count"] == 0
    assert d1["indexed_source_count"] == 1

    # Generate curriculum
    with patch("app.services.curriculum_generator_service.llm_service.generate_response", return_value=SAMPLE_VALID_LLM_JSON):
        client.post(
            f"/courses/{course.id}/curriculum/generate",
            json={"mode": "replace"},
        )

    # After generation
    res_status_2 = client.get(f"/courses/{course.id}/curriculum/status")
    assert res_status_2.status_code == 200
    d2 = res_status_2.json()
    assert d2["has_curriculum"] is True
    assert d2["topic_count"] == 2
    assert d2["concept_count"] == 4
    assert d2["prerequisite_edge_count"] == 2
    assert d2["is_acyclic"] is True

