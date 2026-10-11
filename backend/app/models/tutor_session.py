import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    String,
    Text,
    DateTime,
    ForeignKey,
    JSON,
    Index,
)
from sqlalchemy.orm import relationship
from app.db.database import Base


class TutorThread(Base):
    """
    Persistent course-scoped conversation thread between a learner and the AI Tutor.
    Contains ordered messages with multi-turn conversational context.
    """
    __tablename__ = "tutor_threads"

    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )
    course_id = Column(
        String(36),
        ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    student_id = Column(
        String(100),
        nullable=False,
        default="default_student",
        index=True,
    )
    title = Column(String(255), nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    course = relationship("Course", back_populates="tutor_threads")
    messages = relationship(
        "TutorMessage",
        back_populates="thread",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="TutorMessage.created_at",
    )

    __table_args__ = (
        Index("ix_tutor_threads_course_student", "course_id", "student_id"),
    )

    def __repr__(self):
        return f"<TutorThread(id='{self.id}', title='{self.title}', course_id='{self.course_id}', student='{self.student_id}')>"


class TutorMessage(Base):
    """
    Individual message turn within a TutorThread.
    Supports user prompts and grounded assistant responses with persisted citations.
    """
    __tablename__ = "tutor_messages"

    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )
    thread_id = Column(
        String(36),
        ForeignKey("tutor_threads.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role = Column(String(20), nullable=False)  # "user" | "assistant"
    content = Column(Text, nullable=False)
    status = Column(
        String(32),
        nullable=False,
        default="answered",
    )  # answered, insufficient_evidence, out_of_scope, no_course_material
    citations_json = Column(JSON, nullable=True)  # List of grounded citations
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    thread = relationship("TutorThread", back_populates="messages")

    __table_args__ = (
        Index("ix_tutor_messages_thread_created", "thread_id", "created_at"),
    )

    def __repr__(self):
        return f"<TutorMessage(id='{self.id}', thread_id='{self.thread_id}', role='{self.role}', status='{self.status}')>"

