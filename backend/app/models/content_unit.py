import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    String,
    Text,
    Integer,
    Float,
    DateTime,
    ForeignKey,
    LargeBinary,
    JSON,
    Index,
)
from sqlalchemy.orm import relationship, validates
from app.db.database import Base


class ContentUnit(Base):
    __tablename__ = "content_units"

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
    source_id = Column(
        String(36),
        ForeignKey("sources.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    unit_index = Column(
        Integer,
        nullable=False,
        default=0
    )
    content_type = Column(
        String(50),
        nullable=False,
        default="text"
    )  # text, slide, transcript, diagram
    text = Column(
        Text,
        nullable=False
    )
    char_start = Column(
        Integer,
        nullable=True
    )
    char_end = Column(
        Integer,
        nullable=True
    )
    page_number = Column(
        Integer,
        nullable=True
    )  # 1-based PDF page number
    slide_number = Column(
        Integer,
        nullable=True
    )  # PPT/PPTX slide number
    timestamp_start = Column(
        Float,
        nullable=True
    )  # Video start time in seconds
    timestamp_end = Column(
        Float,
        nullable=True
    )  # Video end time in seconds
    metadata_json = Column(
        JSON,
        nullable=True
    )
    embedding = Column(
        LargeBinary,
        nullable=True
    )  # Serialized 384-dimensional float32 vector (1536 bytes)
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
    course = relationship("Course", back_populates="content_units")
    source = relationship("Source", back_populates="content_units")

    # Table indexes for fast course-scoped retrieval and sequential ordered chunking
    __table_args__ = (
        Index("ix_content_units_course_source", "course_id", "source_id"),
        Index("ix_content_units_source_unit_index", "source_id", "unit_index"),
    )

    @validates("source")
    def validate_source_course(self, key, source):
        if source and self.course_id and source.course_id != self.course_id:
            raise ValueError(
                f"ContentUnit course_id '{self.course_id}' does not match "
                f"Source course_id '{source.course_id}'."
            )
        return source

    def to_dict(self):
        return {
            "id": self.id,
            "course_id": self.course_id,
            "source_id": self.source_id,
            "unit_index": self.unit_index,
            "content_type": self.content_type,
            "text": self.text,
            "char_start": self.char_start,
            "char_end": self.char_end,
            "page_number": self.page_number,
            "slide_number": self.slide_number,
            "timestamp_start": self.timestamp_start,
            "timestamp_end": self.timestamp_end,
            "metadata_json": self.metadata_json,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return (
            f"<ContentUnit(id='{self.id}', course_id='{self.course_id}', "
            f"source_id='{self.source_id}', unit_index={self.unit_index}, "
            f"page={self.page_number})>"
        )

