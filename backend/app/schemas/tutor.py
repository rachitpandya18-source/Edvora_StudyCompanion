from typing import Optional, List
from enum import Enum
from pydantic import BaseModel, ConfigDict, Field


class TutorStatus(str, Enum):
    ANSWERED = "answered"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    OUT_OF_SCOPE = "out_of_scope"
    NO_COURSE_MATERIAL = "no_course_material"


class TutorCitation(BaseModel):
    content_unit_id: Optional[str] = Field(
        default=None,
        description="UUID of the persisted ContentUnit"
    )
    source_id: Optional[str] = Field(
        default=None,
        description="UUID of the Source document"
    )
    filename: str = Field(
        ...,
        description="Original filename of the course material"
    )
    page: Optional[int] = Field(
        default=None,
        description="1-based page number where evidence was found"
    )
    score: Optional[float] = Field(
        default=None,
        description="Relevance similarity score (float)"
    )
    content_type: str = Field(
        default="pdf",
        description="Type of source content (pdf, slide, transcript, etc.)"
    )

    model_config = ConfigDict(from_attributes=True)


class CourseTutorAskRequest(BaseModel):
    question: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="The student's study question"
    )
    source_id: Optional[str] = Field(
        default=None,
        description="Optional filter to scope retrieval to a specific Source ID"
    )
    top_k: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum number of evidence chunks to retrieve"
    )


class CourseTutorResponse(BaseModel):
    answer: str = Field(
        ...,
        description="The grounded answer or explicit status explanation"
    )
    status: str = Field(
        ...,
        description="Response contract status: answered, insufficient_evidence, out_of_scope, no_course_material"
    )
    citations: List[TutorCitation] = Field(
        default_factory=list,
        description="List of grounded evidence citations supporting the answer"
    )
    course_id: str = Field(
        ...,
        description="ID of the course queried"
    )

    model_config = ConfigDict(from_attributes=True)

