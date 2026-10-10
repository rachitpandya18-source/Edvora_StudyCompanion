import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime
from sqlalchemy.orm import relationship
from app.db.database import Base


class Course(Base):
    __tablename__ = "courses"

    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True
    )
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
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

    # 1-to-many relationship with Source, cascade delete all associated sources
    sources = relationship(
        "Source",
        back_populates="course",
        cascade="all, delete-orphan",
        passive_deletes=True
    )

    # 1-to-many relationship with ContentUnit, cascade delete all associated units
    content_units = relationship(
        "ContentUnit",
        back_populates="course",
        cascade="all, delete-orphan",
        passive_deletes=True
    )

    # 1-to-many relationship with Topic, cascade delete all associated topics
    topics = relationship(
        "Topic",
        back_populates="course",
        cascade="all, delete-orphan",
        order_by="Topic.order_index"
    )

    # 1-to-many relationship with Concept, cascade delete all associated concepts
    concepts = relationship(
        "Concept",
        back_populates="course",
        cascade="all, delete-orphan",
        order_by="Concept.order_index"
    )

    # 1-to-many relationship with Assessment, cascade delete all associated assessments
    assessments = relationship(
        "Assessment",
        back_populates="course",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="desc(Assessment.created_at)"
    )

    def __repr__(self):
        return f"<Course(id='{self.id}', title='{self.title}')>"

