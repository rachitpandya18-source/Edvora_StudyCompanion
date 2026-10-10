import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    String,
    Text,
    DateTime,
    ForeignKey,
    Integer,
    Float,
    Boolean,
    JSON,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from app.db.database import Base


class Assessment(Base):
    """
    Persistent course assessment (quiz, exam, mock test, or mixed test).
    Contains a collection of ordered questions and student attempts.
    """
    __tablename__ = "assessments"

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
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    assessment_type = Column(String(50), nullable=False, default="mixed")
    time_limit_minutes = Column(Integer, nullable=True)
    total_marks = Column(Float, nullable=False, default=0.0)
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
    course = relationship("Course", back_populates="assessments")
    questions = relationship(
        "Question",
        back_populates="assessment",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="Question.order_index",
    )
    attempts = relationship(
        "AssessmentAttempt",
        back_populates="assessment",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="desc(AssessmentAttempt.created_at)",
    )

    def __repr__(self):
        return f"<Assessment(id='{self.id}', title='{self.title}', course_id='{self.course_id}')>"


class Question(Base):
    """
    Individual question within an assessment.
    Supports mcq, true_false, short_answer, and numerical types.
    """
    __tablename__ = "questions"

    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )
    assessment_id = Column(
        String(36),
        ForeignKey("assessments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    question_type = Column(String(32), nullable=False)  # mcq, true_false, short_answer, numerical
    prompt = Column(Text, nullable=False)
    order_index = Column(Integer, nullable=False, default=0)
    marks = Column(Float, nullable=False, default=1.0)
    options_json = Column(JSON, nullable=True)  # List of choices for MCQ
    correct_answer = Column(Text, nullable=False)  # Encrypted/hidden from student prior to submission
    tolerance = Column(Float, nullable=True)  # Allowed delta for numerical questions
    explanation = Column(Text, nullable=True)  # Pedagogical explanation revealed post-submission
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
    assessment = relationship("Assessment", back_populates="questions")
    attempt_answers = relationship(
        "AttemptAnswer",
        back_populates="question",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self):
        return f"<Question(id='{self.id}', type='{self.question_type}', order={self.order_index})>"


class AssessmentAttempt(Base):
    """
    Student attempt on an assessment.
    Tracks attempt lifecycle: in_progress -> submitted.
    """
    __tablename__ = "assessment_attempts"

    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )
    assessment_id = Column(
        String(36),
        ForeignKey("assessments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    student_id = Column(String(100), nullable=False, default="default_student", index=True)
    status = Column(String(32), nullable=False, default="in_progress")  # in_progress, submitted
    score = Column(Float, nullable=True)
    max_score = Column(Float, nullable=True)
    percentage = Column(Float, nullable=True)
    submitted_at = Column(DateTime(timezone=True), nullable=True)
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
    assessment = relationship("Assessment", back_populates="attempts")
    answers = relationship(
        "AttemptAnswer",
        back_populates="attempt",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self):
        return f"<AssessmentAttempt(id='{self.id}', assessment_id='{self.assessment_id}', status='{self.status}')>"


class AttemptAnswer(Base):
    """
    Student answer for a specific question within an attempt.
    Stores draft student answer and post-submission evaluation result.
    """
    __tablename__ = "attempt_answers"

    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )
    attempt_id = Column(
        String(36),
        ForeignKey("assessment_attempts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    question_id = Column(
        String(36),
        ForeignKey("questions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    student_answer = Column(Text, nullable=True)
    is_correct = Column(Boolean, nullable=True)  # Null while in_progress; boolean on submission
    marks_awarded = Column(Float, nullable=False, default=0.0)
    feedback = Column(Text, nullable=True)
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

    __table_args__ = (
        UniqueConstraint("attempt_id", "question_id", name="uq_attempt_question"),
    )

    # Relationships
    attempt = relationship("AssessmentAttempt", back_populates="answers")
    question = relationship("Question", back_populates="attempt_answers")

    def __repr__(self):
        return f"<AttemptAnswer(attempt_id='{self.attempt_id}', question_id='{self.question_id}')>"

