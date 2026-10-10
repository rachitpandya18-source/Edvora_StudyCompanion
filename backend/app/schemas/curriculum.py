from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field


# =====================================================================
# Topic Schemas
# =====================================================================

class TopicBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(default=None)
    order_index: int = Field(default=0, ge=0)


class TopicCreate(TopicBase):
    pass


class TopicUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = Field(default=None)
    order_index: Optional[int] = Field(default=None, ge=0)


class TopicResponse(TopicBase):
    id: str
    course_id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TopicListResponse(BaseModel):
    items: List[TopicResponse]
    total: int


# =====================================================================
# Concept Schemas
# =====================================================================

class ConceptBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(default=None)
    order_index: int = Field(default=0, ge=0)


class ConceptCreate(ConceptBase):
    pass


class CourseConceptCreate(ConceptBase):
    topic_id: str = Field(..., description="ID of the topic this concept belongs to")


class ConceptUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = Field(default=None)
    order_index: Optional[int] = Field(default=None, ge=0)
    topic_id: Optional[str] = Field(default=None, description="New topic ID within the same course")


class ConceptResponse(ConceptBase):
    id: str
    course_id: str
    topic_id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConceptDetailResponse(ConceptResponse):
    prerequisite_ids: List[str] = Field(default_factory=list)


class ConceptListResponse(BaseModel):
    items: List[ConceptResponse]
    total: int


# =====================================================================
# Prerequisite Schemas
# =====================================================================

class PrerequisiteCreate(BaseModel):
    prerequisite_id: str = Field(..., description="ID of the concept that must be understood first")


class PrerequisiteResponse(BaseModel):
    concept_id: str
    prerequisite_id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PrerequisiteEdgeResponse(BaseModel):
    concept_id: str
    prerequisite_id: str

    model_config = ConfigDict(from_attributes=True)


# =====================================================================
# Curriculum Graph / Overview Schemas
# =====================================================================

class TopicWithConceptsResponse(BaseModel):
    id: str
    course_id: str
    title: str
    description: Optional[str] = None
    order_index: int = 0
    concepts: List[ConceptResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class CourseCurriculumResponse(BaseModel):
    course_id: str
    topics: List[TopicWithConceptsResponse] = Field(default_factory=list)
    prerequisites: List[PrerequisiteEdgeResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)

