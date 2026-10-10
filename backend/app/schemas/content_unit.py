from datetime import datetime
from typing import Optional, Any, Dict
from pydantic import BaseModel, ConfigDict, Field


class ContentUnitBase(BaseModel):
    unit_index: int = Field(default=0)
    content_type: str = Field(default="text")
    text: str
    char_start: Optional[int] = None
    char_end: Optional[int] = None
    page_number: Optional[int] = None
    slide_number: Optional[int] = None
    timestamp_start: Optional[float] = None
    timestamp_end: Optional[float] = None
    metadata_json: Optional[Dict[str, Any]] = None


class ContentUnitResponse(ContentUnitBase):
    id: str
    course_id: str
    source_id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MaterialUploadResponse(BaseModel):
    message: str
    course_id: str
    source_id: str
    filename: str
    processing_status: str
    content_units_count: int
    page_count: int

