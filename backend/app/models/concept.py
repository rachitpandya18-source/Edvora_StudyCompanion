import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    String,
    Text,
    Integer,
    DateTime,
    ForeignKey,
    CheckConstraint,
    Index,
)
from sqlalchemy.orm import relationship, validates
from app.db.database import Base


class ConceptPrerequisite(Base):
    __tablename__ = "concept_prerequisites"

    concept_id = Column(
        String(36),
        ForeignKey("concepts.id", ondelete="CASCADE"),
        primary_key=True,
        index=True
    )
    prerequisite_id = Column(
        String(36),
        ForeignKey("concepts.id", ondelete="CASCADE"),
        primary_key=True,
        index=True
    )
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "concept_id != prerequisite_id",
            name="ck_concept_prerequisite_no_self"
        ),
    )

    def __repr__(self):
        return f"<ConceptPrerequisite(concept_id='{self.concept_id}', prerequisite_id='{self.prerequisite_id}')>"


class Concept(Base):
    __tablename__ = "concepts"

    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True
    )
    course_id = Column(
        String(36),
        ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    topic_id = Column(
        String(36),
        ForeignKey("topics.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    order_index = Column(Integer, nullable=False, default=0)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    course = relationship("Course", back_populates="concepts")
    topic = relationship("Topic", back_populates="concepts")

    # Directed prerequisite relationships (A depends on B -> A is concept_id, B is prerequisite_id)
    prerequisites = relationship(
        "Concept",
        secondary="concept_prerequisites",
        primaryjoin="Concept.id == ConceptPrerequisite.concept_id",
        secondaryjoin="Concept.id == ConceptPrerequisite.prerequisite_id",
        backref="dependents",
        lazy="select"
    )

    # Edge cascade tracking
    prerequisite_edges = relationship(
        "ConceptPrerequisite",
        foreign_keys="[ConceptPrerequisite.concept_id]",
        cascade="all, delete-orphan",
        passive_deletes=True,
        overlaps="dependents,prerequisites"
    )
    postrequisite_edges = relationship(
        "ConceptPrerequisite",
        foreign_keys="[ConceptPrerequisite.prerequisite_id]",
        cascade="all, delete-orphan",
        passive_deletes=True,
        overlaps="dependents,prerequisites"
    )

    # Composite indexes
    __table_args__ = (
        Index("ix_concepts_topic_order", "topic_id", "order_index"),
    )

    @validates("topic")
    def validate_topic_course(self, key, topic):
        if topic and self.course_id and topic.course_id != self.course_id:
            raise ValueError(
                f"Concept course_id '{self.course_id}' does not match "
                f"Topic course_id '{topic.course_id}'."
            )
        return topic

    def __repr__(self):
        return f"<Concept(id='{self.id}', name='{self.name}', topic_id='{self.topic_id}')>"

