import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from app.db.database import Base


class Source(Base):
    __tablename__ = "sources"

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
    filename = Column(String(255), nullable=False)
    source_type = Column(String(50), nullable=False, default="pdf")
    file_path = Column(String(500), nullable=True)
    processing_status = Column(
        String(50),
        nullable=False,
        default="pending"
    )  # pending, completed, failed
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

    # Many-to-one relationship back to Course
    course = relationship("Course", back_populates="sources")

    # 1-to-many relationship with ContentUnit, cascade delete all associated units
    content_units = relationship(
        "ContentUnit",
        back_populates="source",
        cascade="all, delete-orphan",
        passive_deletes=True
    )

    def __repr__(self):
        return f"<Source(id='{self.id}', filename='{self.filename}', status='{self.processing_status}')>"

