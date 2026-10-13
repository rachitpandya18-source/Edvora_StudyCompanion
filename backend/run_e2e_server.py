"""
Dedicated Isolated E2E Test Server Runner.

Enforces strict database isolation, dedicated test ports, fail-closed
safety guards against targeting development/production databases, and
a verifiable E2E health check endpoint.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

backend_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(backend_dir))

# Load existing environment variables (e.g. GEMINI_API_KEY)
load_dotenv(backend_dir / ".env")


def validate_e2e_database_url(url: str) -> str:
    """
    Fail-closed validation to prevent E2E tests from ever targeting
    production, external, or ordinary developer databases.
    Restricts E2E strictly to a dedicated SQLite file inside the expected test directory.
    """
    if not url or not url.strip():
        raise ValueError("SAFETY BLOCK: E2E database URL cannot be empty.")

    url_lower = url.lower().strip()

    # 1. Enforce SQLite dialect strictly - reject external database engines
    if not url_lower.startswith("sqlite"):
        raise ValueError(
            f"SAFETY BLOCK: E2E test server is strictly restricted to isolated SQLite files. "
            f"External database connection rejected: '{url}'"
        )

    # 2. Reject production host/environment indicators
    forbidden_host_indicators = [
        "production",
        "edvora_production",
        "prod",
        "live",
        "staging",
        "edvora.db",
        "development.db",
        "dev.db",
    ]
    for indicator in forbidden_host_indicators:
        if indicator in url_lower:
            raise ValueError(
                f"SAFETY BLOCK: E2E database URL targets forbidden/production resource '{indicator}'. "
                f"Refusing to initialize database: {url}"
            )

    # 3. Enforce explicit E2E / test naming markers
    clean_path = url.split("sqlite:///")[-1].split("?")[0]
    db_filename = Path(clean_path).name.lower()
    if not ("test_playwright_e2e" in db_filename or "e2e_test" in db_filename):
        raise ValueError(
            f"SAFETY BLOCK: SQLite E2E database filename must contain 'test_playwright_e2e' or 'e2e_test'. "
            f"Got filename: '{db_filename}'"
        )

    return url


# Resolve and validate target database URL
default_e2e_sqlite = backend_dir / "test_playwright_e2e.db"
target_db_url = os.getenv("E2E_DATABASE_URL", f"sqlite:///{default_e2e_sqlite}")
validated_db_url = validate_e2e_database_url(target_db_url)

# Clean up dedicated SQLite file if requested or stale from prior run
if "test_playwright_e2e.db" in validated_db_url and default_e2e_sqlite.exists():
    try:
        default_e2e_sqlite.unlink()
    except Exception as cleanup_err:
        print(f"[E2E Server] Note: Existing SQLite file cleanup skipped: {cleanup_err}")

# Set isolated environment variables before importing database engine
os.environ["DATABASE_URL"] = validated_db_url
os.environ["ENVIRONMENT"] = "development"  # Explicit non-production test mode
os.environ["JWT_SECRET_KEY"] = os.getenv(
    "E2E_JWT_SECRET_KEY",
    "edvora_playwright_e2e_secret_key_32_chars_min_safe_test"
)
os.environ["ALLOWED_ORIGINS"] = (
    "http://localhost:5174,http://127.0.0.1:5174,"
    "http://localhost:5173,http://127.0.0.1:5173"
)

# Now safely import database and app models
import uvicorn
from app.db.database import Base, engine
import app.models  # Registers all SQLAlchemy models
from app.main import app


# Add verifiable E2E health route to guarantee server identity
@app.get("/health/e2e")
def health_e2e():
    """Verifiable health check confirming this instance is the isolated E2E server."""
    return {
        "status": "healthy",
        "service": "edvora_e2e_backend",
        "isolated": True,
        "database": "sqlite_e2e",
    }


def main():
    Base.metadata.create_all(bind=engine)
    port = int(os.getenv("PORT", "8001"))
    print(f"[E2E Server] Starting verified isolated server on 127.0.0.1:{port}")
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")


if __name__ == "__main__":
    main()
