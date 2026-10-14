from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict, Field


class PracticeQuestionItem(BaseModel):
    """
    Student-facing question item for active practice session.
    Hides correct_answer, explanation, and grading tolerance.
    """
    id: str
    assessment_id: str
    concept_id: Optional[str] = None
    concept_title: Optional[str] = None
    concept_name: Optional[str] = None
    question_type: str
    prompt: str
    order_index: int
    marks: float
    options_json: Optional[List[str]] = None

    model_config = ConfigDict(from_attributes=True)


class PracticeGenerateRequest(BaseModel):
    """
    Request payload to dynamically generate or assemble an adaptive practice session.
    """
    mode: str = Field(
        default="adaptive",
        description="Practice mode: 'adaptive', 'quick', or 'mock_test'"
    )
    concept_id: Optional[str] = Field(
        default=None,
        description="Target concept ID for adaptive practice"
    )
    topic_id: Optional[str] = Field(
        default=None,
        description="Target topic ID (optional filter)"
    )
    question_count: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Number of questions to generate (1 to 20)"
    )
    question_types: Optional[List[str]] = Field(
        default=None,
        description="Allowed question types: 'mcq', 'true_false', 'short_answer', 'numerical'"
    )
    difficulty: Optional[str] = Field(
        default="medium",
        description="Target difficulty level: 'easy', 'medium', 'hard'"
    )
    student_id: str = Field(
        default="default_student",
        description="Student identifier for session attribution and attempt creation"
    )


class PracticeSessionResponse(BaseModel):
    """
    Student-facing launch payload for an active practice session.
    Integrates directly with B5 Assessment & Attempt lifecycle.
    """
    assessment_id: str
    attempt_id: str
    course_id: str
    mode: str
    title: str
    description: Optional[str] = None
    concept_id: Optional[str] = None
    concept_name: Optional[str] = None
    topic_id: Optional[str] = None
    topic_title: Optional[str] = None
    total_questions: int
    time_limit_minutes: Optional[int] = None
    total_marks: float
    questions: List[PracticeQuestionItem] = Field(default_factory=list)
    submit_endpoint: str = Field(
        ...,
        description="B5 REST endpoint URL for submitting the completed attempt"
    )

    model_config = ConfigDict(from_attributes=True)


class PracticeOptionItem(BaseModel):
    id: str
    name: str
    concept_count: Optional[int] = None


class PracticeConfigOptions(BaseModel):
    """
    Available course topics, supported question types, and difficulty options
    for customizing practice sessions.
    """
    course_id: str
    topics: List[PracticeOptionItem]
    question_types: List[Dict[str, str]]
    difficulties: List[Dict[str, str]]
    recommended_concept_id: Optional[str] = None
    recommended_concept_name: Optional[str] = None

