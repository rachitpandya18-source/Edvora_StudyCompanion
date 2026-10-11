import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    String,
    Float,
    Integer,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import relationship

from app.db.database import Base


# Default standard BKT parameters
DEFAULT_P_L0 = 0.10  # Initial knowledge prior
DEFAULT_P_T = 0.10   # Learning transition rate
DEFAULT_P_G = 0.20   # Guess rate
DEFAULT_P_S = 0.10   # Slip rate


class LearnerConceptMastery(Base):
    """
    Persistent course-scoped Bayesian Knowledge Tracing (BKT) learner state
    for a specific student and concept.
    """
    __tablename__ = "learner_concept_mastery"

    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )
    student_id = Column(
        String(100),
        nullable=False,
        index=True,
    )
    course_id = Column(
        String(36),
        ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    concept_id = Column(
        String(36),
        ForeignKey("concepts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Current estimated probability of mastery L_t in [0.0, 1.0]
    mastery_probability = Column(Float, nullable=False, default=DEFAULT_P_L0)

    # Observation tracking
    observation_count = Column(Integer, nullable=False, default=0)
    correct_count = Column(Integer, nullable=False, default=0)

    # Stored BKT parameters for reproducible updates
    p_l0 = Column(Float, nullable=False, default=DEFAULT_P_L0)
    p_t = Column(Float, nullable=False, default=DEFAULT_P_T)
    p_g = Column(Float, nullable=False, default=DEFAULT_P_G)
    p_s = Column(Float, nullable=False, default=DEFAULT_P_S)

    last_attempt_at = Column(DateTime(timezone=True), nullable=True)
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
        UniqueConstraint("student_id", "concept_id", name="uq_student_concept_mastery"),
        Index("ix_learner_concept_mastery_student_course", "student_id", "course_id"),
    )

    # Relationships
    course = relationship("Course", back_populates="learner_masteries")
    concept = relationship("Concept", back_populates="learner_masteries")

    def __repr__(self):
        return (
            f"<LearnerConceptMastery(student='{self.student_id}', "
            f"concept='{self.concept_id}', mastery={self.mastery_probability:.4f})>"
        )

