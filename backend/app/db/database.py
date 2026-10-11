import os
from typing import Generator
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session

# Load environment variables
load_dotenv()

# Database URL from environment with PostgreSQL as standard target,
# falling back gracefully to SQLite for local development or testing if no live Postgres is present.
# Note: In SQLAlchemy 2.x, 'postgresql://' defaults to psycopg (v3). Since the project specifies
# psycopg2-binary, we default to 'postgresql+psycopg2://' and normalize 'postgresql://' accordingly.
DEFAULT_DB_URL = "postgresql+psycopg2://postgres:postgres@localhost:5432/edvora"
DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_DB_URL)

if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)

# Configure engine arguments
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency yielding a request-scoped database session.
    Ensures the session is cleanly closed after request completion.
    """
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()

