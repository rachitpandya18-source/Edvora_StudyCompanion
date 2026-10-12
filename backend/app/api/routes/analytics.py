from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.api.deps import get_current_student_id
from app.schemas.analytics import (
    CourseAnalyticsOverview,
    TopicAnalyticsDetail,
    VelocityTrendsResponse,
)
from app.services import analytics_service

router = APIRouter(
    prefix="/courses/{course_id}",
    tags=["Learner Analytics"],
)


@router.get(
    "/analytics/overview",
    response_model=CourseAnalyticsOverview,
    status_code=status.HTTP_200_OK,
    summary="Get overall course progress, mastery breakdown, and assessment summary",
)
def get_course_analytics_overview(
    course_id: str,
    learner_id: Optional[str] = Depends(get_current_student_id),
    trend_days: int = Query(30, ge=1, le=365, description="Lookback window in days for recent accuracy"),
    db: Session = Depends(get_db),
):
    """
    Returns aggregated course-level progress, syllabus completion rate,
    overall BKT mastery, exam readiness score, and topic status rollups.
    """
    effective_learner_id = learner_id or "default_student"
    return analytics_service.get_course_analytics_overview(
        db=db,
        course_id=course_id,
        learner_id=effective_learner_id,
        trend_days=trend_days,
    )


@router.get(
    "/topics/{topic_id}/analytics",
    response_model=TopicAnalyticsDetail,
    status_code=status.HTTP_200_OK,
    summary="Get detailed concept-by-concept analytics for a specific topic",
)
def get_topic_analytics_detail(
    course_id: str,
    topic_id: str,
    learner_id: Optional[str] = Depends(get_current_student_id),
    db: Session = Depends(get_db),
):
    """
    Returns in-depth mastery, observation count, and completion category
    for all concepts within the requested topic.
    """
    effective_learner_id = learner_id or "default_student"
    return analytics_service.get_topic_analytics_detail(
        db=db,
        course_id=course_id,
        topic_id=topic_id,
        learner_id=effective_learner_id,
    )


@router.get(
    "/analytics/trends",
    response_model=VelocityTrendsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get chronological practice velocity and score trends",
)
def get_learner_velocity_trends(
    course_id: str,
    learner_id: Optional[str] = Depends(get_current_student_id),
    days: int = Query(30, description="Lookback window in days"),
    db: Session = Depends(get_db),
):
    """
    Returns daily aggregated attempt volume and average score percentage
    over the requested number of days.
    """
    effective_learner_id = learner_id or "default_student"
    return analytics_service.get_learner_velocity_trends(
        db=db,
        course_id=course_id,
        learner_id=effective_learner_id,
        days=days,
    )


