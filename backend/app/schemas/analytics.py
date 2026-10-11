import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class MasteryBreakdown(BaseModel):
    """
    Distribution of course concepts across defined mastery categories.
    """
    mastered: int = Field(0, description="Count of concepts with P(L) >= 0.85")
    proficient: int = Field(0, description="Count of concepts with 0.70 <= P(L) < 0.85")
    developing: int = Field(0, description="Count of concepts with 0.40 <= P(L) < 0.70")
    struggling: int = Field(0, description="Count of concepts with P(L) < 0.40 and at least one completed attempt")
    unassessed: int = Field(0, description="Count of concepts with zero completed attempts")


class AssessmentSummary(BaseModel):
    """
    Aggregated assessment activity and performance for the learner.
    """
    total_attempts: int = Field(0, description="Total completed assessment attempts")
    total_questions_answered: int = Field(0, description="Total questions evaluated across completed attempts")
    overall_accuracy: float = Field(0.0, description="Aggregate score accuracy between 0.0 and 1.0")
    last_practiced_at: Optional[datetime] = Field(None, description="Timestamp of the most recent completed attempt")


class TopicProgressSummary(BaseModel):
    """
    Rollup progress metrics for a curriculum topic.
    """
    topic_id: str
    title: str
    order_index: int
    total_concepts: int
    mastered_concepts: int
    average_mastery: float
    completion_percentage: float
    status: str = Field(..., description="'not_started', 'in_progress', or 'mastered'")


class AttemptTrendPoint(BaseModel):
    """
    Historical trend data point bucketed by date.
    """
    date: str = Field(..., description="Date formatted as YYYY-MM-DD")
    attempt_count: int = Field(..., description="Number of completed attempts on this day")
    average_score_percentage: float = Field(..., description="Average percentage score [0.0, 100.0] on this day")


class CourseAnalyticsOverview(BaseModel):
    """
    Executive dashboard overview of course progress, mastery, and performance.
    """
    course_id: str
    learner_id: str
    overall_mastery: float = Field(..., description="Average concept mastery probability [0.0, 1.0]")
    syllabus_completion_rate: float = Field(..., description="Completed concepts / total concepts [0.0, 1.0]")
    readiness_score: float = Field(..., description="Composite exam readiness metric [0.0, 100.0]")
    total_concepts: int
    concepts_completed: int = Field(..., description="Concepts with at least one completed attempt")
    mastery_breakdown: MasteryBreakdown
    assessment_summary: AssessmentSummary
    topics: List[TopicProgressSummary]


class ConceptAnalyticsItem(BaseModel):
    """
    Detailed progress metrics for a single concept.
    """
    concept_id: str
    name: str
    order_index: int
    mastery_probability: float
    mastery_category: str = Field(..., description="'mastered', 'proficient', 'developing', 'struggling', or 'unassessed'")
    completed_attempts_count: int
    observation_count: int
    correct_count: int
    last_practiced_at: Optional[datetime]


class TopicAnalyticsDetail(BaseModel):
    """
    In-depth concept-by-concept analytics within a specific topic.
    """
    course_id: str
    topic_id: str
    topic_title: str
    order_index: int
    learner_id: str
    total_concepts: int
    mastered_concepts: int
    average_mastery: float
    completion_percentage: float
    status: str
    concepts: List[ConceptAnalyticsItem]


class VelocityTrendsResponse(BaseModel):
    """
    Chronological progress and performance trajectory over time.
    """
    course_id: str
    learner_id: str
    days: int
    trends: List[AttemptTrendPoint]

