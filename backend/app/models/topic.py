import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Integer, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.db.database import Base


class Topic(Base):
    __tablename__ = "topics"

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
    title = Column(String(255), nullable=False)
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
    course = relationship("Course", back_populates="topics")
    concepts = relationship(
        "Concept",
        back_populates="topic",
        cascade="all, delete-orphan",
        order_by="Concept.order_index"
    )

    # Indexes
    __table_args__ = (
        Index("ix_topics_course_order", "course_id", "order_index"),
    )

    def __repr__(self):
        return f"<Topic(id='{self.id}', title='{self.title}', course_id='{self.course_id}')>"

