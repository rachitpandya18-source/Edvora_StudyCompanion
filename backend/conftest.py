import os
import pytest

# Ensure tests default to test environment and test JWT secret key
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-development-and-testing-only-32chars")

from app.main import app
from app.api.deps import get_current_student_id, get_current_user
from app.core.security import create_access_token


@pytest.fixture(autouse=True)
def reset_dependency_overrides():
    """
    Ensure dependency overrides are cleaned up after each test to prevent
    leakage across different test cases and milestone suites.
    """
    yield
    app.dependency_overrides.pop(get_current_student_id, None)
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def override_student_id():
    """
    Fixture providing a helper callable to override get_current_student_id.
    Automatically cleaned up after the test.
    """
    def _set(student_id: str):
        app.dependency_overrides[get_current_student_id] = lambda: student_id
    return _set


@pytest.fixture
def test_jwt_token():
    """
    Generates a valid test JWT access token for a default or custom user.
    """
    def _create(user_id: str = "test_user_id", email: str = "test@example.com") -> str:
        return create_access_token(data={"sub": user_id, "email": email})
    return _create


@pytest.fixture
def auth_headers(test_jwt_token):
    """
    Generates Authorization header dict with a valid Bearer token.
    """
    def _headers(user_id: str = "test_user_id", email: str = "test@example.com") -> dict:
        token = test_jwt_token(user_id=user_id, email=email)
        return {"Authorization": f"Bearer {token}"}
    return _headers

