"""
Pydantic schemas for Milestone B11: Automated Curriculum Ingestion & Graph Extraction.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class CurriculumGenerateRequest(BaseModel):
    """
    Request payload to generate a curriculum from indexed course materials.
    """
    source_ids: Optional[List[str]] = Field(
        default=None,
        description="Optional list of source IDs to limit extraction to. If omitted, uses all sources in course."
    )
    max_topics: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Target maximum number of topics to extract (1-10)."
    )
    concepts_per_topic: int = Field(
        default=4,
        ge=1,
        le=10,
        description="Target concepts per topic (1-10)."
    )
    infer_prerequisites: bool = Field(
        default=True,
        description="Whether to deduce directed prerequisite relationships between concepts."
    )
    mode: str = Field(
        default="preview",
        description="Execution mode: 'preview' (dry run, do not persist) or 'replace' (persist atomically)."
    )


class GeneratedConceptItem(BaseModel):
    id: Optional[str] = Field(default=None, description="Assigned concept ID if persisted, or temporary key")
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    order_index: int = 0
    evidence: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Grounding evidence chunks (source filename, page number, excerpt)"
    )


class GeneratedTopicItem(BaseModel):
    id: Optional[str] = Field(default=None, description="Assigned topic ID if persisted, or temporary key")
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    order_index: int = 0
    concepts: List[GeneratedConceptItem] = Field(default_factory=list)


class GeneratedPrerequisiteItem(BaseModel):
    concept_name: str
    prerequisite_name: str
    concept_id: Optional[str] = None
    prerequisite_id: Optional[str] = None


class CurriculumGenerateResponse(BaseModel):
    """
    Response returned by curriculum generation (both preview and replace modes).
    """
    course_id: str
    mode: str
    status: str  # "preview" or "completed"
    topics_count: int
    concepts_count: int
    prerequisites_count: int
    is_acyclic: bool
    topics: List[GeneratedTopicItem]
    prerequisites: List[GeneratedPrerequisiteItem]
    message: str


class CurriculumStatusResponse(BaseModel):
    """
    Status of the curriculum in a course.
    """
    course_id: str
    has_curriculum: bool
    topic_count: int
    concept_count: int
    prerequisite_edge_count: int
    is_acyclic: bool
    indexed_source_count: int

    model_config = ConfigDict(from_attributes=True)

