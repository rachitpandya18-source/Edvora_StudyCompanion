from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict

from app.schemas.tutor import TutorCitation


class TutorThreadCreate(BaseModel):
    title: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Optional thread title. If omitted, derived deterministically from the first question.",
    )
    student_id: str = Field(
        default="default_student",
        max_length=100,
        description="Unique student identifier.",
    )


class TutorMessageCreate(BaseModel):
    question: str = Field(
        ...,
        min_length=1,
        max_length=4000,
        description="The student's question or conversational follow-up.",
    )
    student_id: str = Field(
        default="default_student",
        max_length=100,
        description="Unique student identifier.",
    )
    source_id: Optional[str] = Field(
        default=None,
        description="Optional filter to scope retrieval to a specific Source ID.",
    )
    top_k: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum number of evidence chunks to retrieve.",
    )


class TutorMessageResponse(BaseModel):
    id: str
    thread_id: str
    role: str = Field(..., description="'user' or 'assistant'")
    content: str
    status: str = Field(
        default="answered",
        description="'answered', 'insufficient_evidence', 'out_of_scope', or 'no_course_material'",
    )
    citations: List[TutorCitation] = Field(
        default_factory=list,
        description="Verified source citations for assistant responses.",
    )
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TutorThreadSummary(BaseModel):
    id: str
    course_id: str
    student_id: str
    title: str
    message_count: int = Field(0, description="Total messages in this thread")
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TutorThreadDetail(BaseModel):
    id: str
    course_id: str
    student_id: str
    title: str
    created_at: datetime
    updated_at: datetime
    messages: List[TutorMessageResponse] = Field(
        default_factory=list,
        description="Chronological messages in this thread.",
    )

    model_config = ConfigDict(from_attributes=True)

