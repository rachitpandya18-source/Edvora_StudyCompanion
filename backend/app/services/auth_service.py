from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.models.user import User
from app.schemas.auth import UserRegisterRequest
from app.core.security import get_password_hash, verify_password, create_access_token, password_needs_rehash


class UserAlreadyExistsError(Exception):
    pass


class InvalidCredentialsError(Exception):
    pass


def register_user(db: Session, request: UserRegisterRequest) -> User:
    """
    Register a new unique user in the system with securely hashed password.
    """
    normalized_email = request.email.lower().strip()
    normalized_username = request.username.lower().strip()

    existing = db.query(User).filter(
        or_(
            User.email == normalized_email,
            User.username == normalized_username
        )
    ).first()

    if existing:
        if existing.email == normalized_email:
            raise UserAlreadyExistsError("A user with this email address already exists.")
        raise UserAlreadyExistsError("A user with this username already exists.")

    user = User(
        email=normalized_email,
        username=normalized_username,
        hashed_password=get_password_hash(request.password),
        full_name=request.full_name.strip() if request.full_name else None
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, username_or_email: str, password: str) -> User:
    """
    Authenticate a user by username or email and plaintext password.
    """
    identifier = username_or_email.lower().strip()
    user = db.query(User).filter(
        or_(
            User.email == identifier,
            User.username == identifier
        )
    ).first()

    if not user:
        raise InvalidCredentialsError("Invalid username/email or password.")

    if not verify_password(password, user.hashed_password):
        raise InvalidCredentialsError("Invalid username/email or password.")

    # Transparently upgrade legacy password hashes to current work factor (600,000 iterations)
    if password_needs_rehash(user.hashed_password):
        user.hashed_password = get_password_hash(password)
        db.commit()

    return user


def get_user_by_id(db: Session, user_id: str) -> Optional[User]:
    """
    Fetch a user by primary key ID.
    """
    return db.query(User).filter(User.id == user_id).first()

