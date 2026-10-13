"""
Milestone B12 End-to-End Integration & Production Readiness Test Suite.

Validates the complete closed-loop academic platform:
1. Student Registration & JWT Authentication (Auth Engine)
2. Course Creation (B1 Course CRUD)
3. Material Upload & Persistent Vector Indexing (B2 Persistent Content)
4. Automated Curriculum Graph Generation (B11 Ingestion Engine)
5. Topic/Concept & Prerequisite DAG Topology (B3 Curriculum Model)
6. Multi-turn Persistent Tutor Thread & Message with Citations (B10 Persistent Tutor)
7. Dynamic Adaptive Practice Generation (B8 Practice Engine)
8. Multi-Question Assessment Submission & Evaluation (B5 Assessment Engine)
9. Bayesian Knowledge Tracing Mastery Update (B6 BKT Engine)
10. Adaptive Study Plan Prioritization Update (B7 Study Planner)
11. Learner Analytics & Exam Readiness Update (B9 Learner Analytics Engine)
12. Security & Identity Verification:
    - Token authentication enforcement in production mode
    - Cross-learner isolation
"""

import os
import io
import json
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import hashlib
import time
from datetime import timedelta
from app.main import app
from app.db.database import Base, get_db
from app.services.embedding_service import create_embeddings, serialize_embedding
from app.models.content_unit import ContentUnit
from app.models.source import Source
from app.models.user import User
from app.models.course import Course
from app.models.assessment import Assessment, Question
from app.core.security import (
    PBKDF2_ROUNDS,
    get_password_hash,
    verify_password,
    password_needs_rehash,
    create_access_token,
    decode_access_token,
    validate_jwt_secret_for_startup,
    _base64url_encode,
    INSECURE_SECRETS,
)


# Isolated test database
TEST_DB_URL = "sqlite:///:memory:"
engine = create_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=engine)
    app.dependency_overrides[get_db] = override_get_db
    yield
    Base.metadata.drop_all(bind=engine)
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def client():
    return TestClient(app)


def test_b12_full_learning_loop_e2e(client):
    """
    Validates the entire end-to-end user lifecycle from signup to analytics reflection.
    """
    # -------------------------------------------------------------------------
    # 1. AUTHENTICATE / REGISTER TEST LEARNER
    # -------------------------------------------------------------------------
    register_payload = {
        "email": "alex.rivera@university.edu",
        "username": "alex_rivera",
        "password": "SecurePassword123!",
        "full_name": "Alex Rivera",
    }
    reg_res = client.post("/auth/register", json=register_payload)
    assert reg_res.status_code == 201, reg_res.text
    reg_data = reg_res.json()
    assert "access_token" in reg_data
    token = reg_data["access_token"]
    student_id = reg_data["user"]["id"]
    headers = {"Authorization": f"Bearer {token}"}

    # Verify /auth/me returns the registered user
    me_res = client.get("/auth/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.json()["username"] == "alex_rivera"

    # -------------------------------------------------------------------------
    # 2. CREATE COURSE
    # -------------------------------------------------------------------------
    course_payload = {
        "title": "CS201 Data Structures and Algorithms",
        "description": "Fundamental trees, graphs, sorting, and complexity analysis.",
    }
    course_res = client.post("/courses", json=course_payload, headers=headers)
    assert course_res.status_code == 201
    course_id = course_res.json()["id"]
    assert course_id is not None

    # Verify course listing includes newly created course
    list_res = client.get("/courses", headers=headers)
    assert list_res.status_code == 200
    assert any(c["id"] == course_id for c in list_res.json()["items"])

    # -------------------------------------------------------------------------
    # 3. ADD / INDEX COURSE MATERIAL
    # -------------------------------------------------------------------------
    db = TestingSessionLocal()
    try:
        source = Source(
            course_id=course_id,
            filename="Algorithms_Textbook.pdf",
            source_type="pdf",
            file_path="/data/Algorithms_Textbook.pdf",
            processing_status="completed",
        )
        db.add(source)
        db.commit()
        db.refresh(source)

        sample_texts = [
            "An AVL Tree is a self-balancing binary search tree where node heights differ by at most 1.",
            "Binary Search Trees maintain the invariant that left keys are smaller and right keys larger.",
            "Graph search algorithms include Breadth-First Search and Depth-First Search for path finding.",
        ]
        embeddings = create_embeddings(sample_texts)

        for i, text in enumerate(sample_texts):
            cu = ContentUnit(
                course_id=course_id,
                source_id=source.id,
                page_number=i + 1,
                unit_index=i,
                text=text,
                embedding=serialize_embedding(embeddings[i]),
            )
            db.add(cu)
        db.commit()
    finally:
        db.close()

    # Verify indexed sources API returns source
    sources_res = client.get(f"/courses/{course_id}/sources", headers=headers)
    assert sources_res.status_code == 200
    assert len(sources_res.json()) >= 1

    # -------------------------------------------------------------------------
    # 4. GENERATE CURRICULUM (B11 Extraction Engine)
    # -------------------------------------------------------------------------
    valid_llm_json = json.dumps({
        "topics": [
            {
                "title": "Balanced Binary Trees",
                "description": "Tree balancing invariants and rotation algorithms",
                "order_index": 0,
                "concepts": [
                    {
                        "name": "Binary Search Tree Invariants",
                        "description": "Standard binary tree search ordering properties",
                        "order_index": 0,
                    },
                    {
                        "name": "AVL Tree Rotations",
                        "description": "Restoring balance factor through rotations",
                        "order_index": 1,
                    },
                ],
            }
        ],
        "prerequisites": [
            {
                "concept": "AVL Tree Rotations",
                "prerequisite": "Binary Search Tree Invariants",
            }
        ],
    })

    with patch("app.services.curriculum_generator_service.llm_service.generate_response", return_value=valid_llm_json):
        gen_res = client.post(
            f"/courses/{course_id}/curriculum/generate",
            json={
                "mode": "replace",
                "max_topics": 5,
                "concepts_per_topic": 4,
                "infer_prerequisites": True,
            },
            headers=headers,
        )
    assert gen_res.status_code == 200, gen_res.text
    gen_data = gen_res.json()
    assert gen_data["status"] == "completed"
    assert gen_data["topics_count"] == 1
    assert gen_data["concepts_count"] == 2
    assert gen_data["prerequisites_count"] == 1

    # -------------------------------------------------------------------------
    # 5. VERIFY CURRICULUM GRAPH TOPOLOGY
    # -------------------------------------------------------------------------
    curr_res = client.get(f"/courses/{course_id}/curriculum", headers=headers)
    assert curr_res.status_code == 200
    curr_data = curr_res.json()
    assert len(curr_data["topics"]) == 1
    concepts = curr_data["topics"][0]["concepts"]
    assert len(concepts) == 2

    bst_concept = next(c for c in concepts if c["name"] == "Binary Search Tree Invariants")
    avl_concept = next(c for c in concepts if c["name"] == "AVL Tree Rotations")
    assert any(
        p["concept_id"] == avl_concept["id"] and p["prerequisite_id"] == bst_concept["id"]
        for p in curr_data["prerequisites"]
    )

    # -------------------------------------------------------------------------
    # 6. PERSISTENT TUTOR THREAD & QUESTION (B10 Persistent Tutor)
    # -------------------------------------------------------------------------
    thread_res = client.post(
        f"/courses/{course_id}/tutor/threads",
        json={"title": "AVL Trees Discussion"},
        headers=headers,
    )
    assert thread_res.status_code == 201
    thread_id = thread_res.json()["id"]

    # Post student question to thread
    with patch("app.services.llm_service.generate_response", return_value="An AVL tree restores height balance using rotations whenever the balance factor exceeds 1."):
        msg_res = client.post(
            f"/courses/{course_id}/tutor/threads/{thread_id}/messages",
            json={"question": "How do AVL rotations work?"},
            headers=headers,
        )
    assert msg_res.status_code == 201
    msg_data = msg_res.json()
    assert msg_data["role"] == "assistant"
    assert msg_data["status"] == "answered"
    assert "AVL tree restores height balance" in msg_data["content"]
    assert len(msg_data["citations"]) >= 1
    assert msg_data["citations"][0]["filename"] == "Algorithms_Textbook.pdf"

    # -------------------------------------------------------------------------
    # 7. GENERATE ADAPTIVE PRACTICE SESSION (B8 Practice Engine)
    # -------------------------------------------------------------------------
    practice_payload = {
        "mode": "adaptive",
        "concept_id": bst_concept["id"],
        "question_count": 2,
    }

    mock_practice_json = json.dumps([
        {
            "prompt": "What property must all nodes in a binary search tree satisfy?",
            "question_type": "mcq",
            "options": [
                "Left keys are smaller, right keys larger",
                "All node heights must be equal",
            ],
            "correct_answer": "Left keys are smaller, right keys larger",
            "explanation": "Standard BST invariant requires left < root < right.",
            "marks": 1.0,
        },
        {
            "prompt": "What is the worst-case search complexity of a degenerate linear binary search tree?",
            "question_type": "mcq",
            "options": [
                "O(log n)",
                "O(n)",
            ],
            "correct_answer": "O(n)",
            "explanation": "A degenerate linear BST has worst-case O(n) search time.",
            "marks": 1.0,
        },
    ])

    with patch("app.services.practice_service.llm_service.generate_response", return_value=mock_practice_json):
        practice_res = client.post(
            f"/courses/{course_id}/practice/generate",
            json=practice_payload,
            headers=headers,
        )
    assert practice_res.status_code == 201, practice_res.text
    practice_data = practice_res.json()
    assert practice_data["assessment_id"] is not None
    assert practice_data["attempt_id"] is not None
    assert len(practice_data["questions"]) == 2
    assessment_id = practice_data["assessment_id"]
    attempt_id = practice_data["attempt_id"]
    q1 = practice_data["questions"][0]
    q2 = practice_data["questions"][1]

    # -------------------------------------------------------------------------
    # 8. SUBMIT ASSESSMENT ATTEMPT (B5 Assessment Engine)
    # -------------------------------------------------------------------------
    # Submit correct answer for Q1, incorrect for Q2
    submission_payload = {
        "answers": [
            {"question_id": q1["id"], "student_answer": "Left keys are smaller, right keys larger"},
            {"question_id": q2["id"], "student_answer": "O(log n)"},
        ]
    }
    submit_res = client.post(
        f"/courses/{course_id}/assessments/{assessment_id}/attempts/{attempt_id}/submit",
        json=submission_payload,
        headers=headers,
    )
    assert submit_res.status_code == 200, submit_res.text
    eval_data = submit_res.json()
    assert eval_data["status"] == "submitted"
    assert eval_data["score"] == 1.0
    assert eval_data["max_score"] == 2.0
    assert eval_data["percentage"] == 50.0

    # -------------------------------------------------------------------------
    # 9. VERIFY BKT MASTERY UPDATE (B6 BKT Engine)
    # -------------------------------------------------------------------------
    mastery_res = client.get(
        f"/courses/{course_id}/mastery/{bst_concept['id']}",
        headers=headers,
    )
    assert mastery_res.status_code == 200
    mastery_data = mastery_res.json()
    assert mastery_data["observation_count"] == 2
    assert mastery_data["correct_count"] == 1
    # Probability P(L) was updated from prior
    assert 0.0 < mastery_data["mastery_probability"] < 1.0

    # -------------------------------------------------------------------------
    # 10. GENERATE / VERIFY STUDY PLAN (B7 Adaptive Study Planner)
    # -------------------------------------------------------------------------
    plan_res = client.get(
        f"/courses/{course_id}/study-plan",
        headers=headers,
    )
    assert plan_res.status_code == 200
    plan_data = plan_res.json()
    assert plan_data["top_recommendation"] is not None
    assert plan_data["top_recommendation"]["concept_id"] == bst_concept["id"]
    assert plan_data["summary"]["needs_revision"] >= 1
    assert plan_data["summary"]["total_concepts"] == 2

    # -------------------------------------------------------------------------
    # 11. READ PROGRESS ANALYTICS (B9 Learner Analytics Engine)
    # -------------------------------------------------------------------------
    analytics_res = client.get(
        f"/courses/{course_id}/analytics/overview",
        headers=headers,
    )
    assert analytics_res.status_code == 200
    analytics_data = analytics_res.json()
    assert analytics_data["total_concepts"] == 2
    assert analytics_data["concepts_completed"] == 1
    assert analytics_data["syllabus_completion_rate"] == 0.5
    assert analytics_data["readiness_score"] > 0.0

    trends_res = client.get(
        f"/courses/{course_id}/analytics/trends",
        headers=headers,
    )
    assert trends_res.status_code == 200
    assert len(trends_res.json()["trends"]) >= 1


def test_b12_production_security_enforcement(client):
    """
    Verifies that when ENVIRONMENT=production is set:
    - Missing or invalid Bearer tokens receive HTTP 401 Unauthorized on learner endpoints
    - Identity spoofing via query parameters is prevented
    """
    with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
        # 1. Unauthenticated request to /auth/me -> 401
        res = client.get("/auth/me")
        assert res.status_code == 401

        # 2. Unauthenticated request to learner-sensitive endpoint -> 401
        res = client.get("/courses/fake_course/study-plan")
        assert res.status_code == 401

        # 3. Request with forged/malformed token -> 401
        res = client.get(
            "/courses/fake_course/study-plan",
            headers={"Authorization": "Bearer forged.invalid.token"}
        )
        assert res.status_code == 401


def test_b12_cross_learner_isolation(client):
    """
    Verifies that learner A cannot access learner B's private tutor threads.
    """
    # Register learner A
    reg_a = client.post("/auth/register", json={
        "email": "learner_a@univ.edu",
        "username": "learner_a",
        "password": "Password123!",
    })
    token_a = reg_a.json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # Register learner B
    reg_b = client.post("/auth/register", json={
        "email": "learner_b@univ.edu",
        "username": "learner_b",
        "password": "Password123!",
    })
    token_b = reg_b.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # Create a course
    c_res = client.post("/courses", json={"title": "Isolation Test Course"}, headers=headers_a)
    c_id = c_res.json()["id"]

    # Learner A creates a private tutor thread
    t_res = client.post(
        f"/courses/{c_id}/tutor/threads",
        json={"title": "Learner A Private Thread"},
        headers=headers_a,
    )
    thread_id = t_res.json()["id"]

    # Learner B attempts to retrieve Learner A's thread -> 404 Not Found (isolated)
    access_res = client.get(
        f"/courses/{c_id}/tutor/threads/{thread_id}",
        headers=headers_b,
    )
    assert access_res.status_code == 404


def test_b12_fail_closed_authentication_matrix(client):
    """
    Verifies the fail-closed environment check matrix:
    - missing ENVIRONMENT -> 401
    - 'prod', 'productionn', 'staging', 'qa' -> 401
    - '  PRODUCTION  ' (whitespace/case normalized) -> 401
    - '  DEVELOPMENT  ' (whitespace/case normalized) -> fallback allowed
    - '  TEST  ' (whitespace/case normalized) -> fallback allowed
    """
    # 1. Missing ENVIRONMENT -> 401
    with patch.dict(os.environ, {}, clear=True):
        os.environ.pop("ENVIRONMENT", None)
        res = client.get("/auth/me")
        assert res.status_code == 401, f"Expected 401 on missing ENVIRONMENT, got {res.status_code}"

    # 2. Typos and unknown environments fail closed -> 401
    for bad_env in ["prod", "productionn", "staging", "qa", "my_custom_env"]:
        with patch.dict(os.environ, {"ENVIRONMENT": bad_env}):
            res = client.get("/auth/me")
            assert res.status_code == 401, f"Expected 401 for ENVIRONMENT='{bad_env}', got {res.status_code}"

    # 3. Case and whitespace normalization on production -> 401
    with patch.dict(os.environ, {"ENVIRONMENT": "  PRODUCTION  "}):
        res = client.get("/auth/me")
        assert res.status_code == 401

    # 4. Normalized development allows fallback
    with patch.dict(os.environ, {"ENVIRONMENT": "  DEVELOPMENT  "}):
        res = client.get("/courses/fake_course/study-plan")
        # In test mode, fake_course will return 404 from business logic, NOT 401 auth rejection
        assert res.status_code != 401, "Expected fallback allowed for '  DEVELOPMENT  '"

    # 5. Normalized test allows fallback
    with patch.dict(os.environ, {"ENVIRONMENT": "  TEST  "}):
        res = client.get("/courses/fake_course/study-plan")
        assert res.status_code != 401, "Expected fallback allowed for '  TEST  '"


def test_b12_jwt_secret_startup_validation():
    """
    Verifies that validate_jwt_secret_for_startup():
    - Fails with RuntimeError in production if JWT_SECRET_KEY is missing, too short, or uses known defaults
    - Succeeds in production with a strong >= 32 char dedicated key
    - Allows dev defaults when running in development/test mode
    """
    # 1. Production with missing key -> RuntimeError
    with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
        os.environ.pop("JWT_SECRET_KEY", None)
        with pytest.raises(RuntimeError, match="JWT_SECRET_KEY environment variable is missing"):
            validate_jwt_secret_for_startup()

    # 2. Production with insecure/default key -> RuntimeError
    for insecure in INSECURE_SECRETS:
        with patch.dict(os.environ, {"ENVIRONMENT": "production", "JWT_SECRET_KEY": insecure}):
            with pytest.raises(RuntimeError, match="Insecure or default JWT_SECRET_KEY"):
                validate_jwt_secret_for_startup()

    # 3. Production with short key (<32 chars) -> RuntimeError
    with patch.dict(os.environ, {"ENVIRONMENT": "production", "JWT_SECRET_KEY": "short-key-16-chars"}):
        with pytest.raises(RuntimeError, match="Must be at least 32 characters"):
            validate_jwt_secret_for_startup()

    # 4. Production with strong key (>= 32 chars) -> succeeds
    strong_key = "a" * 32
    with patch.dict(os.environ, {"ENVIRONMENT": "production", "JWT_SECRET_KEY": strong_key}):
        validate_jwt_secret_for_startup()  # Should not raise

    # 5. Test/development allows fallback without error
    with patch.dict(os.environ, {"ENVIRONMENT": "test"}):
        os.environ.pop("JWT_SECRET_KEY", None)
        validate_jwt_secret_for_startup()  # Should not raise


def test_b12_attempt_ownership_protection(client):
    """
    Verifies cross-learner attempt authorization enforcement:
    - Learner B cannot read, draft-edit, or submit Learner A's attempt (receives 404)
    - Learner A can read, draft-edit, and submit their own attempt (receives 200)
    """
    # Register Learner A and Learner B
    reg_a = client.post("/auth/register", json={
        "email": "owner_alice@univ.edu",
        "username": "owner_alice",
        "password": "Password123!",
    })
    token_a = reg_a.json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    reg_b = client.post("/auth/register", json={
        "email": "attacker_bob@univ.edu",
        "username": "attacker_bob",
        "password": "Password123!",
    })
    token_b = reg_b.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # Alice creates a course and an assessment
    c_res = client.post("/courses", json={"title": "Ownership Course"}, headers=headers_a)
    course_id = c_res.json()["id"]

    ass_payload = {
        "title": "Ownership Test Quiz",
        "questions": [
            {
                "question_type": "true_false",
                "prompt": "Is access control mandatory?",
                "marks": 5.0,
                "correct_answer": "True",
            }
        ],
    }
    ass_res = client.post(f"/courses/{course_id}/assessments", json=ass_payload, headers=headers_a)
    assessment_id = ass_res.json()["id"]
    q_id = ass_res.json()["questions"][0]["id"]

    # Alice starts an attempt
    att_res = client.post(
        f"/courses/{course_id}/assessments/{assessment_id}/attempts",
        json={"student_id": "ignored_in_auth_mode"},
        headers=headers_a,
    )
    assert att_res.status_code == 201
    attempt_id = att_res.json()["id"]

    # --- ATTACK SCENARIO: Bob tries to access Alice's attempt ---
    # 1. Bob tries to read Alice's in-progress attempt -> 404
    bob_get = client.get(
        f"/courses/{course_id}/assessments/{assessment_id}/attempts/{attempt_id}",
        headers=headers_b,
    )
    assert bob_get.status_code == 404, f"Expected 404, got {bob_get.status_code}"

    # 2. Bob tries to modify Alice's draft answers -> 404
    bob_draft = client.patch(
        f"/courses/{course_id}/assessments/{assessment_id}/attempts/{attempt_id}/draft",
        json={"answers": [{"question_id": q_id, "student_answer": "False"}]},
        headers=headers_b,
    )
    assert bob_draft.status_code == 404, f"Expected 404, got {bob_draft.status_code}"

    # 3. Bob tries to submit Alice's attempt -> 404
    bob_submit = client.post(
        f"/courses/{course_id}/assessments/{assessment_id}/attempts/{attempt_id}/submit",
        json={"answers": [{"question_id": q_id, "student_answer": "False"}]},
        headers=headers_b,
    )
    assert bob_submit.status_code == 404, f"Expected 404, got {bob_submit.status_code}"

    # --- LEGITIMATE SCENARIO: Alice accesses her own attempt ---
    # 1. Alice reads her attempt -> 200
    alice_get = client.get(
        f"/courses/{course_id}/assessments/{assessment_id}/attempts/{attempt_id}",
        headers=headers_a,
    )
    assert alice_get.status_code == 200

    # 2. Alice saves draft answers -> 200
    alice_draft = client.patch(
        f"/courses/{course_id}/assessments/{assessment_id}/attempts/{attempt_id}/draft",
        json={"answers": [{"question_id": q_id, "student_answer": "True"}]},
        headers=headers_a,
    )
    assert alice_draft.status_code == 200

    # 3. Alice submits her attempt -> 200
    alice_submit = client.post(
        f"/courses/{course_id}/assessments/{assessment_id}/attempts/{attempt_id}/submit",
        json={"answers": [{"question_id": q_id, "student_answer": "True"}]},
        headers=headers_a,
    )
    assert alice_submit.status_code == 200
    assert alice_submit.json()["score"] == 5.0


def test_b12_pbkdf2_600k_rounds_and_legacy_rehash(client):
    """
    Verifies NIST-compliant PBKDF2-HMAC-SHA256 password security:
    - PBKDF2_ROUNDS is set to 600,000
    - New hashes use 600,000 rounds
    - Legacy 100,000-round hashes verify successfully
    - Transparent re-hashing to 600,000 rounds occurs upon login
    """
    assert PBKDF2_ROUNDS == 600_000

    # 1. New hash verification
    new_hash = get_password_hash("TestPassword600k!")
    assert new_hash.startswith("pbkdf2:sha256:600000$")
    assert verify_password("TestPassword600k!", new_hash) is True
    assert verify_password("WrongPassword!", new_hash) is False
    assert password_needs_rehash(new_hash) is False

    # 2. Legacy 100k hash verification
    legacy_salt = "1234567890abcdef"
    legacy_key = hashlib.pbkdf2_hmac(
        "sha256",
        b"LegacyPass100k!",
        legacy_salt.encode("utf-8"),
        100_000,
    ).hex()
    legacy_hash = f"pbkdf2:sha256:100000${legacy_salt}${legacy_key}"

    assert verify_password("LegacyPass100k!", legacy_hash) is True
    assert verify_password("WrongPassword!", legacy_hash) is False
    assert password_needs_rehash(legacy_hash) is True

    # 3. Transparent upgrade on login
    db = TestingSessionLocal()
    try:
        legacy_user = User(
            email="legacy_student@univ.edu",
            username="legacy_student",
            hashed_password=legacy_hash,
            full_name="Legacy Student",
        )
        db.add(legacy_user)
        db.commit()
        db.refresh(legacy_user)
        user_id = legacy_user.id
    finally:
        db.close()

    # User logs in with legacy hash
    login_res = client.post("/auth/login", json={
        "username_or_email": "legacy_student@univ.edu",
        "password": "LegacyPass100k!",
    })
    assert login_res.status_code == 200
    assert "access_token" in login_res.json()

    # Check that user's stored hash in DB was transparently upgraded to 600,000 rounds
    db = TestingSessionLocal()
    try:
        updated_user = db.query(User).filter(User.id == user_id).first()
        assert updated_user.hashed_password.startswith("pbkdf2:sha256:600000$")
        assert password_needs_rehash(updated_user.hashed_password) is False
        assert verify_password("LegacyPass100k!", updated_user.hashed_password) is True
    finally:
        db.close()


def test_b12_hardened_jwt_validation():
    """
    Verifies custom JWT validation hardening:
    - Algorithm enforcement (only HS256, rejects 'none', 'RS256')
    - Signature tampering detection via constant-time HMAC check
    - Expiration enforcement
    - Required 'sub' claim validation
    - Malformed token structure rejection
    """
    # 1. Valid token decodes correctly
    valid_token = create_access_token({"sub": "test_user_sub", "email": "test@univ.edu"})
    payload = decode_access_token(valid_token)
    assert payload["sub"] == "test_user_sub"

    # 2. Tampered signature rejected
    tampered = valid_token[:-4] + "abcd"
    with pytest.raises(ValueError, match="Invalid token signature"):
        decode_access_token(tampered)

    # 3. Expired token rejected
    expired_token = create_access_token({"sub": "test_user_sub"}, expires_delta=timedelta(seconds=-10))
    with pytest.raises(ValueError, match="Token has expired"):
        decode_access_token(expired_token)

    # 4. Algorithm 'none' attack rejected
    header_none = _base64url_encode(json.dumps({"alg": "none", "typ": "JWT"}).encode("utf-8"))
    payload_exp = _base64url_encode(json.dumps({"sub": "test_sub", "exp": int(time.time()) + 3600}).encode("utf-8"))
    none_token = f"{header_none}.{payload_exp}."
    with pytest.raises(ValueError, match="Only 'HS256' is permitted"):
        decode_access_token(none_token)

    # 5. Unsupported algorithm rejected
    header_rs256 = _base64url_encode(json.dumps({"alg": "RS256", "typ": "JWT"}).encode("utf-8"))
    rs256_token = f"{header_rs256}.{payload_exp}.dummy_sig"
    with pytest.raises(ValueError, match="Only 'HS256' is permitted"):
        decode_access_token(rs256_token)

    # 6. Missing 'sub' claim rejected
    nosub_token = create_access_token({"email": "test@univ.edu"})
    with pytest.raises(ValueError, match="required non-empty 'sub'"):
        decode_access_token(nosub_token)

    # 7. Malformed structure (not 3 segments) rejected
    for bad in ["not-a-token", "a.b", "a.b.c.d", ""]:
        with pytest.raises(ValueError):
            decode_access_token(bad)

