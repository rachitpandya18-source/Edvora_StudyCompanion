from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


class LearnerMasteryInitRequest(BaseModel):
    student_id: Optional[str] = Field(default="default_student", description="Student identifier")
    p_l0: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Custom prior probability P(L0)")
    p_t: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Custom transition probability P(T)")
    p_g: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Custom guess probability P(G)")
    p_s: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Custom slip probability P(S)")


class LearnerConceptMasteryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: Optional[str] = None
    student_id: str
    course_id: str
    concept_id: str
    concept_name: Optional[str] = None
    topic_id: Optional[str] = None
    mastery_probability: float
    observation_count: int
    correct_count: int
    last_attempt_at: Optional[datetime] = None
    p_l0: float
    p_t: float
    p_g: float
    p_s: float
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class LearnerCourseMasteryListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    course_id: str
    student_id: str
    masteries: List[LearnerConceptMasteryResponse]

