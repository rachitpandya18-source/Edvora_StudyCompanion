from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator, ConfigDict


# ============================================================================
# Question Schemas
# ============================================================================

VALID_QUESTION_TYPES = {"mcq", "true_false", "short_answer", "numerical"}


class QuestionCreate(BaseModel):
    question_type: str = Field(..., description="Type: mcq, true_false, short_answer, numerical")
    prompt: str = Field(..., min_length=1, description="Question prompt/text")
    order_index: int = Field(default=0, ge=0, description="Display order index")
    marks: float = Field(default=1.0, gt=0, description="Marks awarded for correct answer")
    options_json: Optional[List[str]] = Field(default=None, description="Option choices for MCQ")
    correct_answer: str = Field(..., min_length=1, description="Answer key for evaluation")
    tolerance: Optional[float] = Field(default=None, description="Tolerance for numerical answers")
    explanation: Optional[str] = Field(default=None, description="Explanation shown after submission")

    @field_validator("question_type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        clean = v.strip().lower()
        if clean not in VALID_QUESTION_TYPES:
            raise ValueError(f"question_type must be one of {sorted(VALID_QUESTION_TYPES)}")
        return clean

    @field_validator("options_json")
    @classmethod
    def validate_options(cls, v: Optional[List[str]], values) -> Optional[List[str]]:
        return v


class QuestionResponse(BaseModel):
    """
    Student-facing question payload: intentionally omits correct_answer,
    tolerance, and explanation prior to attempt submission.
    """
    model_config = ConfigDict(from_attributes=True)

    id: str
    assessment_id: str
    question_type: str
    prompt: str
    order_index: int
    marks: float
    options_json: Optional[List[str]] = None


class QuestionDetailResponse(BaseModel):
    """
    Full question detail including answer key and pedagogical explanation.
    Used for post-submission review and administrative audit.
    """
    model_config = ConfigDict(from_attributes=True)

    id: str
    assessment_id: str
    question_type: str
    prompt: str
    order_index: int
    marks: float
    options_json: Optional[List[str]] = None
    correct_answer: str
    tolerance: Optional[float] = None
    explanation: Optional[str] = None


# ============================================================================
# Assessment Schemas
# ============================================================================

class AssessmentCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255, description="Assessment title")
    description: Optional[str] = Field(default=None, description="Assessment instructions or overview")
    assessment_type: str = Field(default="mixed", description="Assessment type: mcq, true_false, short_answer, numerical, mixed, mock_test")
    time_limit_minutes: Optional[int] = Field(default=None, ge=1, description="Time limit in minutes")
    questions: List[QuestionCreate] = Field(default_factory=list, description="Questions included in the assessment")


class AssessmentSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    course_id: str
    title: str
    description: Optional[str] = None
    assessment_type: str
    time_limit_minutes: Optional[int] = None
    total_marks: float
    question_count: int
    created_at: datetime
    updated_at: datetime


class AssessmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    course_id: str
    title: str
    description: Optional[str] = None
    assessment_type: str
    time_limit_minutes: Optional[int] = None
    total_marks: float
    questions: List[QuestionResponse] = []
    created_at: datetime
    updated_at: datetime


# ============================================================================
# Attempt and Answer Schemas
# ============================================================================

class AnswerDraftItem(BaseModel):
    question_id: str
    student_answer: Optional[str] = None


class SaveDraftRequest(BaseModel):
    answers: List[AnswerDraftItem] = Field(..., description="Draft answers to persist")


class SubmitAttemptRequest(BaseModel):
    answers: Optional[List[AnswerDraftItem]] = Field(
        default=None,
        description="Optional final answers to save before triggering submission evaluation"
    )


class AttemptAnswerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    attempt_id: str
    question_id: str
    student_answer: Optional[str] = None
    is_correct: Optional[bool] = None
    marks_awarded: float = 0.0
    feedback: Optional[str] = None
    question_prompt: Optional[str] = None
    question_type: Optional[str] = None
    question_marks: Optional[float] = None
    options_json: Optional[List[str]] = None
    correct_answer: Optional[str] = None
    explanation: Optional[str] = None


class StartAttemptRequest(BaseModel):
    student_id: Optional[str] = Field(default="default_student", description="Student identifier")


class AssessmentAttemptResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    assessment_id: str
    student_id: str
    status: str
    score: Optional[float] = None
    max_score: Optional[float] = None
    percentage: Optional[float] = None
    submitted_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    answers: List[AttemptAnswerResponse] = []

