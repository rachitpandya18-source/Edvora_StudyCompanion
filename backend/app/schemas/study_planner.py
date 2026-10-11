from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class StudyActionStep(BaseModel):
    """
    Concrete recommended learning action for a concept.
    """
    step: int = Field(..., ge=1, description="Step order sequence")
    title: str = Field(..., description="Actionable title description")
    action_type: str = Field(
        ...,
        description="Type of action: review_material, ask_tutor, practice_quiz"
    )
    details: Optional[str] = Field(None, description="Contextual target, source reference or prompt")


class StudyNextResponse(BaseModel):
    """
    Immediate, single highest-leverage learning recommendation for the student.
    Matches frontend StudyNextCard and CourseStudyNext expectations.
    """
    course_id: str
    concept_id: Optional[str] = None
    concept_name: Optional[str] = None
    topic_id: Optional[str] = None
    topic_title: Optional[str] = None
    priority_category: str = Field(
        ...,
        description="REVISE_WEAK, UNBLOCK_PREREQUISITE, LEARN_NEW, REFRESH_RETENTION, or COURSE_COMPLETED"
    )
    mastery_probability: float = Field(..., ge=0.0, le=1.0)
    status_text: str = Field(..., description="Human-readable status label (e.g. Needs attention, Ready to learn)")
    rationale: str = Field(..., description="Clear pedagogical reasoning for recommendation")
    unblocked_dependents_count: int = Field(0, description="Count of downstream concepts blocked by this concept")
    recommended_actions: List[StudyActionStep] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class PrioritizedConceptItem(BaseModel):
    """
    Concept representation in full study plan with readiness and priority metrics.
    """
    concept_id: str
    concept_name: str
    topic_id: str
    topic_title: str
    order_index: int
    mastery_probability: float
    observation_count: int
    is_ready: bool = Field(..., description="True if all prerequisites are mastered (>= 0.70)")
    priority_score: float = Field(..., description="Composite priority score, higher indicates higher urgency")
    priority_category: str = Field(
        ...,
        description="REVISE_WEAK, UNBLOCK_PREREQUISITE, LEARN_NEW, REFRESH_RETENTION, MASTERED, or BLOCKED"
    )
    unmet_prerequisites: List[str] = Field(default_factory=list, description="Names of unmastered prerequisite concepts")
    last_attempt_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class StudyPlanSummary(BaseModel):
    total_concepts: int
    mastered_concepts: int
    needs_revision: int
    ready_to_learn: int
    blocked_concepts: int


class StudyPlanResponse(BaseModel):
    """
    Complete course-scoped adaptive study plan.
    """
    course_id: str
    student_id: str
    generated_at: datetime
    overall_course_mastery: float = Field(..., ge=0.0, le=1.0)
    top_recommendation: Optional[StudyNextResponse] = None
    prioritized_concepts: List[PrioritizedConceptItem] = Field(default_factory=list)
    summary: StudyPlanSummary

    model_config = ConfigDict(from_attributes=True)

