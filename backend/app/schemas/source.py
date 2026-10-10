from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class SourceBase(BaseModel):
    filename: str = Field(..., min_length=1, max_length=255)
    source_type: str = Field(default="pdf", max_length=50)
    file_path: Optional[str] = Field(default=None, max_length=500)
    processing_status: str = Field(default="pending", max_length=50)


class SourceCreate(SourceBase):
    pass


class SourceUpdate(BaseModel):
    filename: Optional[str] = Field(default=None, min_length=1, max_length=255)
    source_type: Optional[str] = Field(default=None, max_length=50)
    file_path: Optional[str] = Field(default=None, max_length=500)
    processing_status: Optional[str] = Field(default=None, max_length=50)


class SourceResponse(SourceBase):
    id: str
    course_id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

