from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.source import SourceResponse


class CourseBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(default=None)


class CourseCreate(CourseBase):
    pass


class CourseUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = Field(default=None)


class CourseResponse(CourseBase):
    id: str
    created_at: datetime
    updated_at: datetime
    sources: List[SourceResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class CourseListResponse(BaseModel):
    items: List[CourseResponse]
    total: int

