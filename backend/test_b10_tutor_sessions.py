"""
Milestone B10 Test Suite: Multi-Turn Persistent Tutor & Conversational Learning Engine.

Comprehensive coverage for:
1. Thread lifecycle:
   - Create thread (custom title & default derived title).
   - List threads (ordered by activity, filtered by student_id).
   - Get thread (detail with messages).
   - Delete thread.
2. Multi-turn context:
   - First user question + assistant grounded response.
   - Follow-up question referencing previous context ("Can you explain step 2 again?").
   - Verification that recent history is supplied to LLM prompt.
3. Citation persistence:
   - Assistant citations are stored in database.
   - Citations remain available upon fetching thread detail.
4. Grounding & refusal behavior:
   - Supported question gets grounded response with authentic citations.
   - Unsupported / out-of-scope question preserves refusal contract and status.
   - Zero-material course returns NO_COURSE_MATERIAL without invoking LLM.
5. Isolation:
   - Student A cannot access Student B's thread.
   - Thread from Course A cannot be accessed under Course B.
6. Cascade behavior:
   - Deleting a thread cascades to all associated messages.
   - Deleting a course cascades to all associated threads and messages.
7. Backward compatibility:
   - Existing single-turn POST /courses/{course_id}/tutor/ask remains identical.
8. Edge cases:
   - Missing thread -> 404.
   - Non-existent course -> 404.
   - Empty question -> 400.
   - Long conversation uses bounded sliding window (CONVERSATIONAL_WINDOW_LIMIT).
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

TEST_DB_FILE = f"test_b10_temp_{uuid.uuid4().hex[:8]}.db"
TEST_DATABASE_URL = f"sqlite:///{TEST_DB_FILE}"
os.environ["DATABASE_URL"] = TEST_DATABASE_URL

from app.db.database import Base, get_db
from app.models.course import Course
from app.models.source import Source
from app.models.content_unit import ContentUnit
from app.models.tutor_session import TutorThread, TutorMessage
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


@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def populated_course_with_materials(db_session):
    """
    Creates a course, a source, and 3 indexed content units with mock embeddings.
    """
    course = Course(
        id=str(uuid.uuid4()),
        title="Algorithms 101",
        description="Data structures and algorithms course",
    )
    db_session.add(course)

    source = Source(
        id=str(uuid.uuid4()),
        course_id=course.id,
        filename="Trees.pdf",
        source_type="pdf",
        file_path="data/uploads/Trees.pdf",
        processing_status="completed",
    )
    db_session.add(source)

    from app.services.embedding_service import create_embeddings, serialize_embedding

    t1 = "An AVL tree maintains a balance factor between -1, 0, and +1 at every node. Step 1: Perform regular BST insertion. Step 2: Traverse upwards to rebalance using rotations."
    t2 = "Step 2 details: Left Rotation is applied when the right subtree is right-heavy. Right Rotation is applied when the left subtree is left-heavy."
    t3 = "Red-black trees use colored node bits to maintain approximate balance. No two consecutive red nodes are permitted."

    v1, v2, v3 = create_embeddings([t1, t2, t3])

    # Unit 1: AVL Tree Balance Invariant
    u1 = ContentUnit(
        id=str(uuid.uuid4()),
        course_id=course.id,
        source_id=source.id,
        unit_index=0,
        page_number=42,
        content_type="pdf",
        text=t1,
        embedding=serialize_embedding(v1),
    )

    # Unit 2: Rotations
    u2 = ContentUnit(
        id=str(uuid.uuid4()),
        course_id=course.id,
        source_id=source.id,
        unit_index=1,
        page_number=43,
        content_type="pdf",
        text=t2,
        embedding=serialize_embedding(v2),
    )

    # Unit 3: Red-Black Tree
    u3 = ContentUnit(
        id=str(uuid.uuid4()),
        course_id=course.id,
        source_id=source.id,
        unit_index=2,
        page_number=50,
        content_type="pdf",
        text=t3,
        embedding=serialize_embedding(v3),
    )
    db_session.add_all([u1, u2, u3])
    db_session.commit()

    return {
        "course": course,
        "source": source,
        "units": [u1, u2, u3],
    }


# =====================================================================
# Tests: Thread Lifecycle
# =====================================================================

def test_thread_lifecycle(populated_course_with_materials, db_session):
    course = populated_course_with_materials["course"]
    student_id = "alice"

    # 1. Create thread with explicit title
    res = client.post(
        f"/courses/{course.id}/tutor/threads",
        json={"title": "AVL Trees Discussion", "student_id": student_id},
    )
    assert res.status_code == 201
    thread_data = res.json()
    assert thread_data["title"] == "AVL Trees Discussion"
    assert thread_data["course_id"] == course.id
    assert thread_data["student_id"] == student_id
    assert thread_data["message_count"] == 0
    thread_id = thread_data["id"]

    # 2. List threads
    res_list = client.get(f"/courses/{course.id}/tutor/threads?student_id={student_id}")
    assert res_list.status_code == 200
    threads = res_list.json()
    assert len(threads) == 1
    assert threads[0]["id"] == thread_id

    # 3. Get thread detail (initially empty messages)
    res_get = client.get(f"/courses/{course.id}/tutor/threads/{thread_id}?student_id={student_id}")
    assert res_get.status_code == 200
    detail = res_get.json()
    assert detail["id"] == thread_id
    assert detail["title"] == "AVL Trees Discussion"
    assert len(detail["messages"]) == 0

    # 4. Delete thread
    res_del = client.delete(f"/courses/{course.id}/tutor/threads/{thread_id}?student_id={student_id}")
    assert res_del.status_code == 200

    # 5. Confirm deletion
    res_after = client.get(f"/courses/{course.id}/tutor/threads/{thread_id}?student_id={student_id}")
    assert res_after.status_code == 404


def test_thread_default_derived_title(populated_course_with_materials):
    course = populated_course_with_materials["course"]

    # Create thread with no title
    res = client.post(
        f"/courses/{course.id}/tutor/threads",
        json={"student_id": "bob"},
    )
    assert res.status_code == 201
    assert res.json()["title"] == "Study Session"


# =====================================================================
# Tests: Multi-Turn Context & Bounded Window
# =====================================================================

def test_multi_turn_context_and_citation_persistence(populated_course_with_materials):
    course = populated_course_with_materials["course"]
    student_id = "student_turn_tester"

    # Create thread
    res = client.post(
        f"/courses/{course.id}/tutor/threads",
        json={"student_id": student_id},
    )
    thread_id = res.json()["id"]

    captured_prompts = []

    def mock_llm_turn(prompt: str) -> str:
        captured_prompts.append(prompt)
        if "step 2" in prompt.lower() or "rotation" in prompt.lower():
            return "Based on page 43 of Trees.pdf, Step 2 involves Left and Right Rotations to rebalance the AVL tree."
        return "An AVL tree maintains a balance factor between -1, 0, and +1 by traversing upwards and rotating if needed."

    with patch("app.services.llm_service.generate_response", side_effect=mock_llm_turn):
        # Turn 1: Initial question
        res1 = client.post(
            f"/courses/{course.id}/tutor/threads/{thread_id}/messages",
            json={
                "question": "How does an AVL tree maintain balance?",
                "student_id": student_id,
            },
        )
        assert res1.status_code == 201
        m1 = res1.json()
        assert m1["role"] == "assistant"
        assert m1["status"] == "answered"
        assert len(m1["citations"]) > 0
        assert m1["citations"][0]["filename"] == "Trees.pdf"

        # Verify thread title was auto-updated from initial question
        res_thread = client.get(f"/courses/{course.id}/tutor/threads/{thread_id}?student_id={student_id}")
        assert "How does an AVL tree maintain balance?" in res_thread.json()["title"]

        # Turn 2: Follow-up question referencing Step 2
        res2 = client.post(
            f"/courses/{course.id}/tutor/threads/{thread_id}/messages",
            json={
                "question": "Can you explain step 2 again?",
                "student_id": student_id,
            },
        )
        assert res2.status_code == 201
        m2 = res2.json()
        assert m2["role"] == "assistant"
        assert m2["status"] == "answered"
        assert len(m2["citations"]) > 0

    # Verify that Turn 2 prompt contained recent conversation history
    assert len(captured_prompts) == 2
    prompt_turn2 = captured_prompts[1]
    assert "RECENT CONVERSATION HISTORY:" in prompt_turn2
    assert "How does an AVL tree maintain balance?" in prompt_turn2
    assert "Can you explain step 2 again?" in prompt_turn2

    # Verify thread message history persistence
    res_history = client.get(f"/courses/{course.id}/tutor/threads/{thread_id}?student_id={student_id}")
    history_detail = res_history.json()
    assert len(history_detail["messages"]) == 4  # User1, Assistant1, User2, Assistant2
    assert history_detail["messages"][0]["role"] == "user"
    assert history_detail["messages"][1]["role"] == "assistant"
    assert history_detail["messages"][2]["role"] == "user"
    assert history_detail["messages"][3]["role"] == "assistant"
    # Citations persisted on assistant message
    assert len(history_detail["messages"][1]["citations"]) > 0
    assert history_detail["messages"][1]["citations"][0]["filename"] == "Trees.pdf"


def test_bounded_sliding_window_history(populated_course_with_materials):
    """
    Verify that long conversations never exceed the bounded window (e.g. 6 messages).
    """
    course = populated_course_with_materials["course"]
    student_id = "long_convo_student"

    res = client.post(
        f"/courses/{course.id}/tutor/threads",
        json={"student_id": student_id},
    )
    thread_id = res.json()["id"]

    captured_prompts = []

    def mock_llm(prompt: str) -> str:
        captured_prompts.append(prompt)
        return "AVL trees maintain balance factors between -1 and +1."

    with patch("app.services.llm_service.generate_response", side_effect=mock_llm):
        for i in range(5):  # 5 user questions = 10 total messages
            client.post(
                f"/courses/{course.id}/tutor/threads/{thread_id}/messages",
                json={"question": f"Question number {i+1} about AVL trees", "student_id": student_id},
            )

    # In turn 5, recent conversation history should be bounded (not all 10 messages)
    last_prompt = captured_prompts[-1]
    # Check that the earliest question (Question number 1) has rolled out of the 6-message window
    assert "Question number 1" not in last_prompt
    assert "Question number 4" in last_prompt


# =====================================================================
# Tests: Grounding & Refusal Contracts
# =====================================================================

def test_grounding_refusal_in_threads(populated_course_with_materials):
    course = populated_course_with_materials["course"]
    student_id = "refusal_tester"

    res = client.post(
        f"/courses/{course.id}/tutor/threads",
        json={"student_id": student_id},
    )
    thread_id = res.json()["id"]

    # Mock refusal phrase from LLM
    with patch("app.services.llm_service.generate_response", return_value="I could not find this information in the provided course material."):
        res_msg = client.post(
            f"/courses/{course.id}/tutor/threads/{thread_id}/messages",
            json={
                "question": "What is the capital of Australia?",
                "student_id": student_id,
            },
        )
        assert res_msg.status_code == 201
        msg = res_msg.json()
        assert msg["status"] in ["insufficient_evidence", "out_of_scope"]
        assert msg["citations"] == []


def test_zero_material_course_no_material_status(db_session):
    """
    Course with no uploaded materials returns NO_COURSE_MATERIAL without invoking LLM.
    """
    empty_c = Course(id=str(uuid.uuid4()), title="Empty Material Course")
    db_session.add(empty_c)
    db_session.commit()

    student_id = "empty_student"
    res_t = client.post(
        f"/courses/{empty_c.id}/tutor/threads",
        json={"student_id": student_id},
    )
    thread_id = res_t.json()["id"]

    with patch("app.services.llm_service.generate_response") as mock_llm:
        res_msg = client.post(
            f"/courses/{empty_c.id}/tutor/threads/{thread_id}/messages",
            json={"question": "What is an algorithm?", "student_id": student_id},
        )
        assert res_msg.status_code == 201
        msg = res_msg.json()
        assert msg["status"] == "no_course_material"
        assert "does not have any uploaded or indexed study material" in msg["content"]
        assert mock_llm.call_count == 0  # LLM never invoked


# =====================================================================
# Tests: Student and Course Isolation
# =====================================================================

def test_student_isolation(populated_course_with_materials):
    course = populated_course_with_materials["course"]

    # Student Alice creates thread
    res = client.post(
        f"/courses/{course.id}/tutor/threads",
        json={"title": "Alice's Secret Thread", "student_id": "alice"},
    )
    thread_id = res.json()["id"]

    # Student Bob tries to view Alice's thread -> 404
    res_bob_get = client.get(f"/courses/{course.id}/tutor/threads/{thread_id}?student_id=bob")
    assert res_bob_get.status_code == 404

    # Student Bob tries to post message to Alice's thread -> 404
    res_bob_post = client.post(
        f"/courses/{course.id}/tutor/threads/{thread_id}/messages",
        json={"question": "Hello Alice", "student_id": "bob"},
    )
    assert res_bob_post.status_code == 404

    # Student Bob lists threads -> Alice's thread not present
    res_bob_list = client.get(f"/courses/{course.id}/tutor/threads?student_id=bob")
    assert res_bob_list.status_code == 200
    assert len(res_bob_list.json()) == 0


def test_cross_course_isolation(populated_course_with_materials, db_session):
    c1 = populated_course_with_materials["course"]
    c2 = Course(id=str(uuid.uuid4()), title="Physics 101")
    db_session.add(c2)
    db_session.commit()

    res = client.post(
        f"/courses/{c1.id}/tutor/threads",
        json={"title": "Course 1 Thread", "student_id": "charlie"},
    )
    thread_id = res.json()["id"]

    # Access thread created in Course 1 under Course 2 -> 404
    res_c2 = client.get(f"/courses/{c2.id}/tutor/threads/{thread_id}?student_id=charlie")
    assert res_c2.status_code == 404
    assert "does not belong to course" in res_c2.json()["detail"].lower()


# =====================================================================
# Tests: Cascade Behavior
# =====================================================================

def test_cascade_delete_thread_and_messages(populated_course_with_materials, db_session):
    course = populated_course_with_materials["course"]
    student_id = "cascade_student"

    res = client.post(
        f"/courses/{course.id}/tutor/threads",
        json={"student_id": student_id},
    )
    thread_id = res.json()["id"]

    with patch("app.services.llm_service.generate_response", return_value="Sample answer"):
        client.post(
            f"/courses/{course.id}/tutor/threads/{thread_id}/messages",
            json={"question": "Sample Question", "student_id": student_id},
        )

    assert db_session.query(TutorThread).filter(TutorThread.id == thread_id).count() == 1
    assert db_session.query(TutorMessage).filter(TutorMessage.thread_id == thread_id).count() == 2

    # Delete thread
    client.delete(f"/courses/{course.id}/tutor/threads/{thread_id}?student_id={student_id}")

    # Confirm thread and messages deleted
    assert db_session.query(TutorThread).filter(TutorThread.id == thread_id).count() == 0
    assert db_session.query(TutorMessage).filter(TutorMessage.thread_id == thread_id).count() == 0


def test_cascade_delete_course_removes_threads(populated_course_with_materials, db_session):
    course = populated_course_with_materials["course"]
    student_id = "course_del_student"

    res = client.post(
        f"/courses/{course.id}/tutor/threads",
        json={"student_id": student_id},
    )
    thread_id = res.json()["id"]

    # Delete course via course endpoint
    res_del = client.delete(f"/courses/{course.id}")
    assert res_del.status_code == 200

    assert db_session.query(TutorThread).filter(TutorThread.id == thread_id).count() == 0


# =====================================================================
# Tests: Backward Compatibility with Single-Turn Endpoint
# =====================================================================

def test_single_turn_endpoint_backward_compatibility(populated_course_with_materials):
    course = populated_course_with_materials["course"]

    with patch("app.services.llm_service.generate_response", return_value="AVL trees balance factors are between -1, 0, and +1."):
        res = client.post(
            f"/courses/{course.id}/tutor/ask",
            json={"question": "What is an AVL tree?", "top_k": 3},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "answered"
        assert "AVL trees balance" in data["answer"]
        assert len(data["citations"]) > 0
        assert data["course_id"] == course.id


# =====================================================================
# Tests: Edge Cases
# =====================================================================

def test_missing_thread_and_empty_question(populated_course_with_materials):
    course = populated_course_with_materials["course"]
    fake_id = str(uuid.uuid4())

    res_missing = client.get(f"/courses/{course.id}/tutor/threads/{fake_id}")
    assert res_missing.status_code == 404

    # Create thread
    res_t = client.post(f"/courses/{course.id}/tutor/threads", json={})
    tid = res_t.json()["id"]

    # Empty question
    res_empty = client.post(
        f"/courses/{course.id}/tutor/threads/{tid}/messages",
        json={"question": "   "},
    )
    assert res_empty.status_code == 400
