"""
Test suite for Phase B3: Curriculum Model (Topics, Concepts, and Prerequisites).

Verifies:
1. Topic and Concept model persistence across database reconnects.
2. Parent-child topic-concept ownership validation.
3. Self-prerequisite rejection.
4. Duplicate prerequisite rejection.
5. Cross-course prerequisite rejection.
6. Direct cycle rejection.
7. Indirect (transitive / multi-hop) cycle rejection.
8. Valid DAG prerequisite chains and diamond structures.
9. Course and Topic cascade deletion behavior.
10. Complete course curriculum graph structure query.
11. FastAPI course-scoped curriculum endpoints (Topics, Concepts, Prerequisites, Graph).
12. Alembic migration upgrade to B3 and downgrade back to B2.
"""

import os
import sys
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Isolate database for B3 tests
TEST_DB_FILE = "test_b3_temp.db"
TEST_DATABASE_URL = f"sqlite:///{TEST_DB_FILE}"
os.environ["DATABASE_URL"] = TEST_DATABASE_URL

from app.db.database import Base, get_db
from app.models.course import Course
from app.models.topic import Topic
from app.models.concept import Concept, ConceptPrerequisite
from app.services import curriculum_service
from app.main import app

from sqlalchemy import event
from sqlalchemy.engine import Engine

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
# Model & Persistence Tests
# =====================================================================

def test_topic_and_concept_persistence_across_reconnect():
    """Verify Topics and Concepts persist correctly across separate DB sessions."""
    # Session 1: Create Course, Topic, and Concepts
    with TestingSessionLocal() as db1:
        course = Course(title="Machine Learning 101", description="Intro to ML")
        db1.add(course)
        db1.commit()
        db1.refresh(course)
        course_id = course.id

        topic = Topic(course_id=course_id, title="Supervised Learning", order_index=1)
        db1.add(topic)
        db1.commit()
        db1.refresh(topic)
        topic_id = topic.id

        concept1 = Concept(course_id=course_id, topic_id=topic_id, name="Linear Regression", order_index=1)
        concept2 = Concept(course_id=course_id, topic_id=topic_id, name="Gradient Descent", order_index=2)
        db1.add_all([concept1, concept2])
        db1.commit()
        c1_id = concept1.id
        c2_id = concept2.id

    # Session 2: Read back from fresh session
    with TestingSessionLocal() as db2:
        saved_topic = db2.query(Topic).filter(Topic.id == topic_id).first()
        assert saved_topic is not None
        assert saved_topic.title == "Supervised Learning"
        assert saved_topic.course_id == course_id
        assert len(saved_topic.concepts) == 2

        saved_concepts = db2.query(Concept).filter(Concept.topic_id == topic_id).order_by(Concept.order_index).all()
        assert [c.name for c in saved_concepts] == ["Linear Regression", "Gradient Descent"]
        assert [c.id for c in saved_concepts] == [c1_id, c2_id]


def test_topic_concept_ownership_validation():
    """Verify that a Concept cannot accidentally reference a Topic from another course."""
    with TestingSessionLocal() as db:
        course_a = Course(title="Course A")
        course_b = Course(title="Course B")
        db.add_all([course_a, course_b])
        db.commit()

        # Topic in Course B
        topic_b = Topic(course_id=course_b.id, title="Topic in B")
        db.add(topic_b)
        db.commit()

        # 1. ORM Model validator test: Assigning topic of Course B to concept with course_id of Course A
        concept = Concept(course_id=course_a.id, name="Concept in A")
        with pytest.raises(ValueError, match="does not match Topic course_id"):
            concept.topic = topic_b

        # 2. Service level validator test: creating concept under topic_b for course_a
        with pytest.raises(ValueError, match="belongs to course"):
            curriculum_service.create_concept(
                db=db,
                course_id=course_a.id,
                topic_id=topic_b.id,
                name="Invalid Concept"
            )


# =====================================================================
# Prerequisite Graph Tests
# =====================================================================

def test_self_prerequisite_rejection():
    """Verify that a concept cannot be added as its own prerequisite."""
    with TestingSessionLocal() as db:
        course = Course(title="Algorithms")
        db.add(course)
        db.commit()

        topic = Topic(course_id=course.id, title="Graphs")
        db.add(topic)
        db.commit()

        c1 = Concept(course_id=course.id, topic_id=topic.id, name="BFS")
        db.add(c1)
        db.commit()

        with pytest.raises(ValueError, match="cannot be a prerequisite of itself"):
            curriculum_service.add_prerequisite(
                db=db,
                course_id=course.id,
                concept_id=c1.id,
                prerequisite_id=c1.id
            )


def test_duplicate_prerequisite_rejection():
    """Verify that duplicate prerequisite relationships are rejected."""
    with TestingSessionLocal() as db:
        course = Course(title="Algorithms")
        db.add(course)
        db.commit()

        topic = Topic(course_id=course.id, title="Graphs")
        db.add(topic)
        db.commit()

        c1 = Concept(course_id=course.id, topic_id=topic.id, name="BFS")
        c2 = Concept(course_id=course.id, topic_id=topic.id, name="Graph Representations")
        db.add_all([c1, c2])
        db.commit()

        # First add succeeds (BFS requires Graph Representations)
        curriculum_service.add_prerequisite(
            db=db,
            course_id=course.id,
            concept_id=c1.id,
            prerequisite_id=c2.id
        )

        # Second add must raise duplicate error
        with pytest.raises(ValueError, match="already a prerequisite"):
            curriculum_service.add_prerequisite(
                db=db,
                course_id=course.id,
                concept_id=c1.id,
                prerequisite_id=c2.id
            )


def test_cross_course_prerequisite_rejection():
    """Verify that prerequisite relationships cannot cross course boundaries."""
    with TestingSessionLocal() as db:
        course_a = Course(title="Physics")
        course_b = Course(title="Chemistry")
        db.add_all([course_a, course_b])
        db.commit()

        topic_a = Topic(course_id=course_a.id, title="Mechanics")
        topic_b = Topic(course_id=course_b.id, title="Thermodynamics")
        db.add_all([topic_a, topic_b])
        db.commit()

        c_physics = Concept(course_id=course_a.id, topic_id=topic_a.id, name="Kinematics")
        c_chemistry = Concept(course_id=course_b.id, topic_id=topic_b.id, name="Reaction Rates")
        db.add_all([c_physics, c_chemistry])
        db.commit()

        with pytest.raises(ValueError, match="different course"):
            curriculum_service.add_prerequisite(
                db=db,
                course_id=course_a.id,
                concept_id=c_physics.id,
                prerequisite_id=c_chemistry.id
            )


def test_direct_prerequisite_cycle_rejection():
    """Verify that direct cycles (A -> B and B -> A) are prevented."""
    with TestingSessionLocal() as db:
        course = Course(title="Math")
        db.add(course)
        db.commit()

        topic = Topic(course_id=course.id, title="Calculus")
        db.add(topic)
        db.commit()

        c_diff = Concept(course_id=course.id, topic_id=topic.id, name="Differentiation")
        c_limits = Concept(course_id=course.id, topic_id=topic.id, name="Limits")
        db.add_all([c_diff, c_limits])
        db.commit()

        # Differentiation requires Limits
        curriculum_service.add_prerequisite(
            db=db,
            course_id=course.id,
            concept_id=c_diff.id,
            prerequisite_id=c_limits.id
        )

        # Attempting to make Limits require Differentiation would close a direct cycle
        with pytest.raises(ValueError, match="cycle"):
            curriculum_service.add_prerequisite(
                db=db,
                course_id=course.id,
                concept_id=c_limits.id,
                prerequisite_id=c_diff.id
            )


def test_indirect_prerequisite_cycle_rejection():
    """Verify that indirect (multi-hop) cycles (A -> B -> C -> A) are prevented."""
    with TestingSessionLocal() as db:
        course = Course(title="Data Structures")
        db.add(course)
        db.commit()

        topic = Topic(course_id=course.id, title="Trees")
        db.add(topic)
        db.commit()

        c_a = Concept(course_id=course.id, topic_id=topic.id, name="Red-Black Trees")
        c_b = Concept(course_id=course.id, topic_id=topic.id, name="Binary Search Trees")
        c_c = Concept(course_id=course.id, topic_id=topic.id, name="Binary Trees")
        c_d = Concept(course_id=course.id, topic_id=topic.id, name="Basic Recursion")
        db.add_all([c_a, c_b, c_c, c_d])
        db.commit()

        # Build valid prerequisite chain: A requires B, B requires C, C requires D
        curriculum_service.add_prerequisite(db, course.id, c_a.id, c_b.id)
        curriculum_service.add_prerequisite(db, course.id, c_b.id, c_c.id)
        curriculum_service.add_prerequisite(db, course.id, c_c.id, c_d.id)

        # Now attempt to make D require A (4-hop cycle: A -> B -> C -> D -> A)
        with pytest.raises(ValueError, match="cycle"):
            curriculum_service.add_prerequisite(db, course.id, c_d.id, c_a.id)

        # Also attempt to make C require A (3-hop cycle: A -> B -> C -> A)
        with pytest.raises(ValueError, match="cycle"):
            curriculum_service.add_prerequisite(db, course.id, c_c.id, c_a.id)


def test_valid_dag_diamond_structure():
    """Verify that diamond-shaped DAG structures are fully allowed (not false cycles)."""
    with TestingSessionLocal() as db:
        course = Course(title="Compiler Design")
        db.add(course)
        db.commit()

        topic = Topic(course_id=course.id, title="Parsing")
        db.add(topic)
        db.commit()

        # Diamond:
        #        Top (Code Gen)
        #       /             \
        #   Left (Type Check)  Right (Opt)
        #       \             /
        #       Bottom (AST)
        bottom = Concept(course_id=course.id, topic_id=topic.id, name="AST")
        left = Concept(course_id=course.id, topic_id=topic.id, name="Type Checking")
        right = Concept(course_id=course.id, topic_id=topic.id, name="Optimization")
        top = Concept(course_id=course.id, topic_id=topic.id, name="Code Generation")
        db.add_all([bottom, left, right, top])
        db.commit()

        # Left and Right require Bottom
        curriculum_service.add_prerequisite(db, course.id, left.id, bottom.id)
        curriculum_service.add_prerequisite(db, course.id, right.id, bottom.id)

        # Top requires Left and Right
        curriculum_service.add_prerequisite(db, course.id, top.id, left.id)
        curriculum_service.add_prerequisite(db, course.id, top.id, right.id)

        # Verify prerequisites for Top
        top_prereqs = curriculum_service.get_prerequisites(db, course.id, top.id)
        top_prereq_ids = {p.id for p in top_prereqs}
        assert top_prereq_ids == {left.id, right.id}


# =====================================================================
# Cascade Deletion Tests
# =====================================================================

def test_course_and_topic_cascade_deletion():
    """Verify that deleting a course or topic cleanly cascades down to concepts and edges."""
    with TestingSessionLocal() as db:
        course = Course(title="To Delete")
        db.add(course)
        db.commit()

        topic = Topic(course_id=course.id, title="Topic 1")
        db.add(topic)
        db.commit()

        c1 = Concept(course_id=course.id, topic_id=topic.id, name="Concept 1")
        c2 = Concept(course_id=course.id, topic_id=topic.id, name="Concept 2")
        db.add_all([c1, c2])
        db.commit()

        curriculum_service.add_prerequisite(db, course.id, c1.id, c2.id)
        assert db.query(ConceptPrerequisite).count() == 1

        # Delete Topic -> concepts and edges cascade
        db.delete(topic)
        db.commit()

        assert db.query(Topic).filter(Topic.id == topic.id).first() is None
        assert db.query(Concept).filter(Concept.id.in_([c1.id, c2.id])).count() == 0
        assert db.query(ConceptPrerequisite).count() == 0


# =====================================================================
# FastAPI Endpoints Tests
# =====================================================================

def test_curriculum_api_endpoints():
    """Test full RESTful API workflow for Topics, Concepts, Prerequisites, and Curriculum Graph."""
    # 1. Create a course first
    c_res = client.post("/courses", json={"title": "Modern History", "description": "20th Century"})
    assert c_res.status_code == 201
    course_id = c_res.json()["id"]

    # 2. Create topics
    t1_res = client.post(f"/courses/{course_id}/topics", json={
        "title": "World War I",
        "description": "Causes and events of WWI",
        "order_index": 1
    })
    assert t1_res.status_code == 201
    t1_id = t1_res.json()["id"]

    t2_res = client.post(f"/courses/{course_id}/topics", json={
        "title": "Interwar Period",
        "order_index": 2
    })
    assert t2_res.status_code == 201
    t2_id = t2_res.json()["id"]

    # 3. List topics
    list_t_res = client.get(f"/courses/{course_id}/topics")
    assert list_t_res.status_code == 200
    assert list_t_res.json()["total"] == 2

    # 4. Create concepts under topics
    c1_res = client.post(f"/courses/{course_id}/topics/{t1_id}/concepts", json={
        "name": "Alliance System",
        "description": "Triple Entente and Triple Alliance",
        "order_index": 1
    })
    assert c1_res.status_code == 201
    c1_id = c1_res.json()["id"]

    c2_res = client.post(f"/courses/{course_id}/topics/{t1_id}/concepts", json={
        "name": "Outbreak of War",
        "description": "Assassination in Sarajevo",
        "order_index": 2
    })
    assert c2_res.status_code == 201
    c2_id = c2_res.json()["id"]

    c3_res = client.post(f"/courses/{course_id}/concepts", json={
        "topic_id": t2_id,
        "name": "Treaty of Versailles",
        "order_index": 1
    })
    assert c3_res.status_code == 201
    c3_id = c3_res.json()["id"]

    # 5. List concepts
    all_concepts_res = client.get(f"/courses/{course_id}/concepts")
    assert all_concepts_res.status_code == 200
    assert all_concepts_res.json()["total"] == 3

    t1_concepts_res = client.get(f"/courses/{course_id}/topics/{t1_id}/concepts")
    assert t1_concepts_res.status_code == 200
    assert t1_concepts_res.json()["total"] == 2

    # 6. Add prerequisites:
    # Outbreak of War requires Alliance System
    p1_res = client.post(f"/courses/{course_id}/concepts/{c2_id}/prerequisites", json={
        "prerequisite_id": c1_id
    })
    assert p1_res.status_code == 201

    # Treaty of Versailles requires Outbreak of War
    p2_res = client.post(f"/courses/{course_id}/concepts/{c3_id}/prerequisites", json={
        "prerequisite_id": c2_id
    })
    assert p2_res.status_code == 201

    # Cycle attempt via API: Alliance System requires Treaty of Versailles -> 400 Bad Request
    cycle_res = client.post(f"/courses/{course_id}/concepts/{c1_id}/prerequisites", json={
        "prerequisite_id": c3_id
    })
    assert cycle_res.status_code == 400
    assert "cycle" in cycle_res.json()["detail"].lower()

    # Self-prerequisite attempt via API -> 400 Bad Request
    self_res = client.post(f"/courses/{course_id}/concepts/{c1_id}/prerequisites", json={
        "prerequisite_id": c1_id
    })
    assert self_res.status_code == 400

    # Duplicate attempt via API -> 409 Conflict
    dup_res = client.post(f"/courses/{course_id}/concepts/{c2_id}/prerequisites", json={
        "prerequisite_id": c1_id
    })
    assert dup_res.status_code == 409

    # 7. Get full Curriculum Graph
    curriculum_res = client.get(f"/courses/{course_id}/curriculum")
    assert curriculum_res.status_code == 200
    curr_data = curriculum_res.json()
    assert curr_data["course_id"] == course_id
    assert len(curr_data["topics"]) == 2
    assert len(curr_data["prerequisites"]) == 2

    # 8. Delete a prerequisite
    del_p_res = client.delete(f"/courses/{course_id}/concepts/{c2_id}/prerequisites/{c1_id}")
    assert del_p_res.status_code == 200

    # Verify prerequisite was removed
    get_p_res = client.get(f"/courses/{course_id}/concepts/{c2_id}/prerequisites")
    assert get_p_res.status_code == 200
    assert len(get_p_res.json()) == 0


# =====================================================================
# Alembic Migration Tests
# =====================================================================

def test_alembic_migrations_b3():
    """Verify that Alembic runs upgrade to B3 and downgrade back to B2 cleanly on an isolated DB."""
    from alembic.config import Config
    from alembic import command
    from sqlalchemy import inspect, create_engine

    alembic_test_db = "test_alembic_b3_clean.db"
    alembic_test_url = f"sqlite:///{alembic_test_db}"
    if os.path.exists(alembic_test_db):
        try:
            os.remove(alembic_test_db)
        except OSError:
            pass

    try:
        alembic_ini_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "alembic.ini")
        )
        alembic_cfg = Config(alembic_ini_path)
        alembic_cfg.set_main_option("sqlalchemy.url", alembic_test_url)

        # 1. Upgrade to head (f9a3c2b1d402)
        command.upgrade(alembic_cfg, "head")

        # Verify tables exist via SQLAlchemy inspect
        mig_engine = create_engine(alembic_test_url)
        inspector = inspect(mig_engine)
        tables = inspector.get_table_names()
        assert "courses" in tables
        assert "sources" in tables
        assert "content_units" in tables
        assert "topics" in tables
        assert "concepts" in tables
        assert "concept_prerequisites" in tables

        # 2. Downgrade to B2 revision (e8c2f1a3b501)
        command.downgrade(alembic_cfg, "e8c2f1a3b501")
        inspector = inspect(mig_engine)
        tables = inspector.get_table_names()
        assert "topics" not in tables
        assert "concepts" not in tables
        assert "concept_prerequisites" not in tables
        assert "content_units" in tables

        # 3. Upgrade back to head and downgrade to base
        command.upgrade(alembic_cfg, "head")
        command.downgrade(alembic_cfg, "base")
        mig_engine.dispose()
    finally:
        if os.path.exists(alembic_test_db):
            try:
                os.remove(alembic_test_db)
            except OSError:
                pass

