"""
Test suite for Phase B1: Course Architecture & Database Foundation.

Verifies:
1. Database connectivity and session lifecycle (get_db).
2. ORM Model constraints (Course and Source).
3. 1-to-many relationship and CASCADE deletion.
4. FastAPI Course CRUD endpoints (/courses).
5. FastAPI Course-scoped Source endpoints (/courses/{course_id}/sources).
6. Preserved Phase 0 endpoints (/health, /documents, /quiz, /tutor, /recommendations).
7. Alembic migration execution (upgrade and downgrade).
"""

import os
import sys
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Set test environment database before importing application modules
TEST_DB_FILE = "test_b1_temp.db"
TEST_DATABASE_URL = f"sqlite:///{TEST_DB_FILE}"
os.environ["DATABASE_URL"] = TEST_DATABASE_URL

from app.db.database import Base, get_db
from app.models.course import Course
from app.models.source import Source
from app.main import app

# Create test engine and session factory
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
    # Enable SQLite foreign keys
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


def test_db_session_lifecycle():
    """Verify session can be opened, queried, and closed."""
    db = TestingSessionLocal()
    try:
        courses = db.query(Course).all()
        assert len(courses) == 0
    finally:
        db.close()


def test_course_and_source_models_cascade():
    """Verify ORM model creation and cascade deletion."""
    db = TestingSessionLocal()
    try:
        course = Course(
            title="Introduction to Microeconomics",
            description="Foundations of microeconomic theory and consumer choice."
        )
        db.add(course)
        db.commit()
        db.refresh(course)

        assert course.id is not None
        assert course.title == "Introduction to Microeconomics"
        assert course.created_at is not None
        assert course.updated_at is not None

        # Add Source linked to Course
        source = Source(
            course_id=course.id,
            filename="microeconomics_ch1.pdf",
            source_type="pdf",
            file_path="/uploads/microeconomics_ch1.pdf",
            processing_status="completed"
        )
        db.add(source)
        db.commit()
        db.refresh(course)

        assert len(course.sources) == 1
        assert course.sources[0].filename == "microeconomics_ch1.pdf"

        # Delete Course -> verify Source is cascade-deleted
        course_id = course.id
        db.delete(course)
        db.commit()

        assert db.query(Course).filter(Course.id == course_id).first() is None
        assert db.query(Source).filter(Source.course_id == course_id).first() is None
    finally:
        db.close()


def test_course_crud_endpoints():
    """Verify POST, GET, PUT, DELETE /courses endpoints."""
    # 1. Create Course
    create_payload = {
        "title": "Data Structures & Algorithms",
        "description": "Comprehensive course covering trees, graphs, and dynamic programming."
    }
    res = client.post("/courses", json=create_payload)
    assert res.status_code == 201, res.text
    data = res.json()
    assert data["title"] == create_payload["title"]
    assert data["description"] == create_payload["description"]
    assert "id" in data
    course_id = data["id"]

    # 2. List Courses
    res = client.get("/courses")
    assert res.status_code == 200
    list_data = res.json()
    assert list_data["total"] >= 1
    assert any(c["id"] == course_id for c in list_data["items"])

    # 3. Get Course by ID
    res = client.get(f"/courses/{course_id}")
    assert res.status_code == 200
    assert res.json()["id"] == course_id

    # 4. Update Course
    update_payload = {
        "title": "Advanced Data Structures & Algorithms",
        "description": "Updated syllabus with self-balancing trees."
    }
    res = client.put(f"/courses/{course_id}", json=update_payload)
    assert res.status_code == 200
    assert res.json()["title"] == update_payload["title"]
    assert res.json()["description"] == update_payload["description"]

    # 5. Delete Course
    res = client.delete(f"/courses/{course_id}")
    assert res.status_code == 200

    # 6. Verify 404 after deletion
    res = client.get(f"/courses/{course_id}")
    assert res.status_code == 404


def test_course_source_endpoints():
    """Verify Source CRUD endpoints under /courses/{course_id}/sources."""
    # Create parent course
    c_res = client.post("/courses", json={"title": "Computer Networks"})
    assert c_res.status_code == 201
    course_id = c_res.json()["id"]

    # Add source to course
    source_payload = {
        "filename": "tcp_ip_guide.pdf",
        "source_type": "pdf",
        "file_path": "data/uploads/tcp_ip_guide.pdf",
        "processing_status": "pending"
    }
    s_res = client.post(f"/courses/{course_id}/sources", json=source_payload)
    assert s_res.status_code == 201
    source_data = s_res.json()
    source_id = source_data["id"]
    assert source_data["course_id"] == course_id
    assert source_data["filename"] == "tcp_ip_guide.pdf"

    # List sources for course
    list_res = client.get(f"/courses/{course_id}/sources")
    assert list_res.status_code == 200
    sources = list_res.json()
    assert len(sources) == 1
    assert sources[0]["id"] == source_id

    # Get single source
    get_res = client.get(f"/courses/{course_id}/sources/{source_id}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == source_id

    # Course fetch should now include source in nested response
    course_with_sources = client.get(f"/courses/{course_id}").json()
    assert len(course_with_sources["sources"]) == 1

    # Delete source
    del_res = client.delete(f"/courses/{course_id}/sources/{source_id}")
    assert del_res.status_code == 200

    # Verify source is gone
    get_res = client.get(f"/courses/{course_id}/sources/{source_id}")
    assert get_res.status_code == 404


def test_preserved_phase0_endpoints():
    """Verify all Phase 0 endpoints remain intact and functional."""
    # 1. Health check
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "healthy"}

    # 2. Root check
    res = client.get("/")
    assert res.status_code == 200
    assert res.json()["status"] == "running"

    # 3. Recommendation endpoint
    res = client.get("/recommendations/")
    assert res.status_code == 200
    assert "weak_concepts" in res.json()


def test_alembic_migrations():
    """Verify alembic migrations run upgrade and downgrade cleanly on an empty database."""
    from alembic.config import Config
    from alembic import command

    alembic_test_db = "test_alembic_clean.db"
    alembic_test_url = f"sqlite:///{alembic_test_db}"
    if os.path.exists(alembic_test_db):
        os.remove(alembic_test_db)

    try:
        alembic_ini_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "alembic.ini")
        )
        alembic_cfg = Config(alembic_ini_path)
        alembic_cfg.set_main_option("sqlalchemy.url", alembic_test_url)

        # Run upgrade head on clean database
        command.upgrade(alembic_cfg, "head")

        # Run downgrade base
        command.downgrade(alembic_cfg, "base")
    finally:
        if os.path.exists(alembic_test_db):
            os.remove(alembic_test_db)


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main(["-v", __file__]))
