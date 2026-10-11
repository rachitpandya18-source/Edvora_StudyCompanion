"""
Learner Analytics & Course Progress Engine Service for Edvora.

Aggregates course-scoped curriculum (B3), assessments (B5), and BKT mastery (B6)
into executive progress dashboards, topic rollups, attempt summaries,
and velocity trends without creating duplicate tracking systems.
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Set, Tuple
from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.course import Course
from app.models.topic import Topic
from app.models.concept import Concept
from app.models.learner_mastery import LearnerConceptMastery, DEFAULT_P_L0
from app.models.assessment import Assessment, Question, AssessmentAttempt, AttemptAnswer
from app.schemas.analytics import (
    MasteryBreakdown,
    AssessmentSummary,
    TopicProgressSummary,
    AttemptTrendPoint,
    CourseAnalyticsOverview,
    ConceptAnalyticsItem,
    TopicAnalyticsDetail,
    VelocityTrendsResponse,
)


def verify_course_exists(db: Session, course_id: str) -> Course:
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(
            status_code=404,
            detail=f"Course '{course_id}' not found."
        )
    return course


def verify_topic_in_course(db: Session, course_id: str, topic_id: str) -> Topic:
    topic = db.query(Topic).filter(Topic.id == topic_id).first()
    if not topic:
        raise HTTPException(
            status_code=404,
            detail=f"Topic '{topic_id}' not found."
        )
    if topic.course_id != course_id:
        raise HTTPException(
            status_code=404,
            detail=f"Topic '{topic_id}' does not belong to course '{course_id}'."
        )
    return topic


def determine_mastery_category(mastery_probability: float, has_completed_attempt: bool) -> str:
    """
    Categorize concept mastery based on exact B9 specification:
    - mastered: P(L) >= 0.85
    - proficient: 0.70 <= P(L) < 0.85
    - developing: 0.40 <= P(L) < 0.70
    - struggling: P(L) < 0.40 AND at least one completed attempt
    - unassessed: no completed attempt
    """
    if mastery_probability >= 0.85:
        return "mastered"
    elif mastery_probability >= 0.70:
        return "proficient"
    elif mastery_probability >= 0.40:
        return "developing"
    elif has_completed_attempt:
        return "struggling"
    else:
        return "unassessed"


def get_course_completed_attempt_data(
    db: Session,
    course_id: str,
    learner_id: str
) -> Tuple[List[AssessmentAttempt], Dict[str, int], Dict[str, datetime]]:
    """
    Fetch all completed assessment attempts for this learner in this course,
    and map concept attempt counts and last attempt timestamps.
    """
    completed_attempts = (
        db.query(AssessmentAttempt)
        .join(Assessment, AssessmentAttempt.assessment_id == Assessment.id)
        .filter(
            Assessment.course_id == course_id,
            AssessmentAttempt.student_id == learner_id,
            AssessmentAttempt.status == "submitted",
        )
        .order_by(AssessmentAttempt.submitted_at.asc(), AssessmentAttempt.created_at.asc())
        .all()
    )

    if not completed_attempts:
        return [], {}, {}

    completed_attempt_ids = [att.id for att in completed_attempts]

    # Query distinct completed answers joined with Question to map concepts
    # to completion count and most recent activity
    answers_query = (
        db.query(
            Question.concept_id,
            AssessmentAttempt.submitted_at,
            AssessmentAttempt.created_at,
        )
        .join(AttemptAnswer, Question.id == AttemptAnswer.question_id)
        .join(AssessmentAttempt, AttemptAnswer.attempt_id == AssessmentAttempt.id)
        .filter(
            AssessmentAttempt.id.in_(completed_attempt_ids),
            Question.concept_id.isnot(None),
        )
        .all()
    )

    concept_completed_counts: Dict[str, int] = {}
    concept_last_practiced: Dict[str, datetime] = {}

    for concept_id, submitted_at, created_at in answers_query:
        if not concept_id:
            continue
        concept_completed_counts[concept_id] = concept_completed_counts.get(concept_id, 0) + 1
        ts = submitted_at or created_at
        if ts:
            current_max = concept_last_practiced.get(concept_id)
            if current_max is None or ts > current_max:
                concept_last_practiced[concept_id] = ts

    return completed_attempts, concept_completed_counts, concept_last_practiced


def get_course_analytics_overview(
    db: Session,
    course_id: str,
    learner_id: str = "default_student",
    trend_days: int = 30,
) -> CourseAnalyticsOverview:
    """
    Computes aggregated overview metrics for the course dashboard.
    """
    course = verify_course_exists(db, course_id)

    # 1. Fetch all topics and concepts in curriculum order
    topics = (
        db.query(Topic)
        .filter(Topic.course_id == course_id)
        .order_by(Topic.order_index, Topic.created_at)
        .all()
    )

    all_concepts = (
        db.query(Concept)
        .filter(Concept.course_id == course_id)
        .order_by(Concept.order_index, Concept.created_at)
        .all()
    )

    total_concepts = len(all_concepts)

    # 2. Fetch learner mastery records for this course & learner
    mastery_records = (
        db.query(LearnerConceptMastery)
        .filter(
            LearnerConceptMastery.course_id == course_id,
            LearnerConceptMastery.student_id == learner_id,
        )
        .all()
    )
    mastery_map: Dict[str, LearnerConceptMastery] = {m.concept_id: m for m in mastery_records}

    # 3. Fetch completed attempts and concept attempt counts
    completed_attempts, concept_completed_counts, _ = get_course_completed_attempt_data(
        db, course_id, learner_id
    )

    # 4. Assessment Summary calculations
    total_completed_attempts = len(completed_attempts)
    total_questions_answered = 0
    total_earned_score = 0.0
    total_possible_score = 0.0
    last_practiced_at: Optional[datetime] = None

    if completed_attempts:
        for att in completed_attempts:
            if att.score is not None and att.max_score is not None and att.max_score > 0:
                total_earned_score += att.score
                total_possible_score += att.max_score
            ts = att.submitted_at or att.created_at
            if ts:
                if last_practiced_at is None or ts > last_practiced_at:
                    last_practiced_at = ts

        # Total questions answered across completed attempts
        completed_attempt_ids = [att.id for att in completed_attempts]
        total_questions_answered = (
            db.query(func.count(AttemptAnswer.id))
            .filter(AttemptAnswer.attempt_id.in_(completed_attempt_ids))
            .scalar() or 0
        )

    overall_accuracy = (
        round(total_earned_score / total_possible_score, 4)
        if total_possible_score > 0
        else 0.0
    )

    assessment_summary = AssessmentSummary(
        total_attempts=total_completed_attempts,
        total_questions_answered=total_questions_answered,
        overall_accuracy=overall_accuracy,
        last_practiced_at=last_practiced_at,
    )

    # 5. Concept-level calculations & Mastery Categories
    mastered_count = 0
    proficient_count = 0
    developing_count = 0
    struggling_count = 0
    unassessed_count = 0

    concepts_completed_count = 0
    total_mastery_sum = 0.0

    concept_mastery_lookup: Dict[str, float] = {}

    for concept in all_concepts:
        m = mastery_map.get(concept.id)
        p_l = m.mastery_probability if m else DEFAULT_P_L0
        concept_mastery_lookup[concept.id] = p_l
        total_mastery_sum += p_l

        has_completed = concept_completed_counts.get(concept.id, 0) > 0
        if has_completed:
            concepts_completed_count += 1

        cat = determine_mastery_category(p_l, has_completed)
        if cat == "mastered":
            mastered_count += 1
        elif cat == "proficient":
            proficient_count += 1
        elif cat == "developing":
            developing_count += 1
        elif cat == "struggling":
            struggling_count += 1
        else:
            unassessed_count += 1

    mastery_breakdown = MasteryBreakdown(
        mastered=mastered_count,
        proficient=proficient_count,
        developing=developing_count,
        struggling=struggling_count,
        unassessed=unassessed_count,
    )

    # Metric 1: Overall course mastery
    if total_concepts > 0:
        overall_mastery = round(total_mastery_sum / total_concepts, 4)
        completion_rate = round(concepts_completed_count / total_concepts, 4)
    else:
        overall_mastery = 0.0
        completion_rate = 0.0

    # Metric 6 & 7: Recent accuracy rate for readiness calculation
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=trend_days)
    recent_earned = 0.0
    recent_possible = 0.0

    for att in completed_attempts:
        ts = att.submitted_at or att.created_at
        # Normalise timezone if necessary
        if ts:
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            if ts >= cutoff:
                if att.score is not None and att.max_score is not None and att.max_score > 0:
                    recent_earned += att.score
                    recent_possible += att.max_score

    recent_accuracy_rate = (
        recent_earned / recent_possible if recent_possible > 0 else 0.0
    )

    # Metric 7: Readiness score
    raw_readiness = (
        0.50 * overall_mastery
        + 0.30 * completion_rate
        + 0.20 * recent_accuracy_rate
    ) * 100.0
    readiness_score = round(max(0.0, min(100.0, raw_readiness)), 2)

    # 6. Topic-level rollups
    topic_summaries: List[TopicProgressSummary] = []
    concepts_by_topic: Dict[str, List[Concept]] = {}
    for c in all_concepts:
        concepts_by_topic.setdefault(c.topic_id, []).append(c)

    for topic in topics:
        topic_concepts = concepts_by_topic.get(topic.id, [])
        t_total = len(topic_concepts)
        t_mastered = 0
        t_sum_mastery = 0.0
        t_completed_concepts = 0

        for tc in topic_concepts:
            p_l = concept_mastery_lookup.get(tc.id, DEFAULT_P_L0)
            t_sum_mastery += p_l
            has_comp = concept_completed_counts.get(tc.id, 0) > 0
            if has_comp:
                t_completed_concepts += 1
            if p_l >= 0.85:
                t_mastered += 1

        if t_total > 0:
            t_avg_mastery = round(t_sum_mastery / t_total, 4)
            t_completion_pct = round((t_completed_concepts / t_total) * 100.0, 2)
        else:
            t_avg_mastery = 0.0
            t_completion_pct = 0.0

        # Topic Status:
        # not_started: no concepts with completed attempts
        # in_progress: some progress but topic average mastery < 0.85
        # mastered: topic average mastery >= 0.85
        if t_completed_concepts == 0:
            status = "not_started"
        elif t_avg_mastery >= 0.85:
            status = "mastered"
        else:
            status = "in_progress"

        topic_summaries.append(
            TopicProgressSummary(
                topic_id=topic.id,
                title=topic.title,
                order_index=topic.order_index,
                total_concepts=t_total,
                mastered_concepts=t_mastered,
                average_mastery=t_avg_mastery,
                completion_percentage=t_completion_pct,
                status=status,
            )
        )

    return CourseAnalyticsOverview(
        course_id=course_id,
        learner_id=learner_id,
        overall_mastery=overall_mastery,
        syllabus_completion_rate=completion_rate,
        readiness_score=readiness_score,
        total_concepts=total_concepts,
        concepts_completed=concepts_completed_count,
        mastery_breakdown=mastery_breakdown,
        assessment_summary=assessment_summary,
        topics=topic_summaries,
    )


def get_topic_analytics_detail(
    db: Session,
    course_id: str,
    topic_id: str,
    learner_id: str = "default_student",
) -> TopicAnalyticsDetail:
    """
    Computes in-depth concept breakdown for a specific topic.
    """
    verify_course_exists(db, course_id)
    topic = verify_topic_in_course(db, course_id, topic_id)

    # Fetch concepts for this topic
    concepts = (
        db.query(Concept)
        .filter(Concept.course_id == course_id, Concept.topic_id == topic_id)
        .order_by(Concept.order_index, Concept.created_at)
        .all()
    )

    mastery_records = (
        db.query(LearnerConceptMastery)
        .filter(
            LearnerConceptMastery.course_id == course_id,
            LearnerConceptMastery.student_id == learner_id,
        )
        .all()
    )
    mastery_map: Dict[str, LearnerConceptMastery] = {m.concept_id: m for m in mastery_records}

    _, concept_completed_counts, concept_last_practiced = get_course_completed_attempt_data(
        db, course_id, learner_id
    )

    t_total = len(concepts)
    t_mastered = 0
    t_sum_mastery = 0.0
    t_completed = 0
    concept_items: List[ConceptAnalyticsItem] = []

    for c in concepts:
        m = mastery_map.get(c.id)
        p_l = m.mastery_probability if m else DEFAULT_P_L0
        t_sum_mastery += p_l

        comp_count = concept_completed_counts.get(c.id, 0)
        has_comp = comp_count > 0
        if has_comp:
            t_completed += 1
        if p_l >= 0.85:
            t_mastered += 1

        cat = determine_mastery_category(p_l, has_comp)
        last_ts = concept_last_practiced.get(c.id) or (m.last_attempt_at if m else None)

        concept_items.append(
            ConceptAnalyticsItem(
                concept_id=c.id,
                name=c.name,
                order_index=c.order_index,
                mastery_probability=round(p_l, 4),
                mastery_category=cat,
                completed_attempts_count=comp_count,
                observation_count=m.observation_count if m else 0,
                correct_count=m.correct_count if m else 0,
                last_practiced_at=last_ts,
            )
        )

    if t_total > 0:
        t_avg_mastery = round(t_sum_mastery / t_total, 4)
        t_completion_pct = round((t_completed / t_total) * 100.0, 2)
    else:
        t_avg_mastery = 0.0
        t_completion_pct = 0.0

    if t_completed == 0:
        status = "not_started"
    elif t_avg_mastery >= 0.85:
        status = "mastered"
    else:
        status = "in_progress"

    return TopicAnalyticsDetail(
        course_id=course_id,
        topic_id=topic_id,
        topic_title=topic.title,
        order_index=topic.order_index,
        learner_id=learner_id,
        total_concepts=t_total,
        mastered_concepts=t_mastered,
        average_mastery=t_avg_mastery,
        completion_percentage=t_completion_pct,
        status=status,
        concepts=concept_items,
    )


def get_learner_velocity_trends(
    db: Session,
    course_id: str,
    learner_id: str = "default_student",
    days: int = 30,
) -> VelocityTrendsResponse:
    """
    Computes chronological day-by-day attempt counts and average scores
    over a configurable window of days.
    """
    if days <= 0 or days > 365:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid parameter 'days': must be between 1 and 365 (got {days})."
        )

    verify_course_exists(db, course_id)

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=days)

    completed_attempts = (
        db.query(AssessmentAttempt)
        .join(Assessment, AssessmentAttempt.assessment_id == Assessment.id)
        .filter(
            Assessment.course_id == course_id,
            AssessmentAttempt.student_id == learner_id,
            AssessmentAttempt.status == "submitted",
        )
        .order_by(AssessmentAttempt.submitted_at.asc(), AssessmentAttempt.created_at.asc())
        .all()
    )

    # Bucket attempts by calendar date (YYYY-MM-DD)
    date_scores: Dict[str, List[float]] = {}

    for att in completed_attempts:
        ts = att.submitted_at or att.created_at
        if not ts:
            continue
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        if ts < cutoff:
            continue

        date_str = ts.strftime("%Y-%m-%d")
        pct = (
            att.percentage
            if att.percentage is not None
            else (
                (att.score / att.max_score * 100.0)
                if (att.score is not None and att.max_score is not None and att.max_score > 0)
                else 0.0
            )
        )
        date_scores.setdefault(date_str, []).append(pct)

    # Sort chronologically
    sorted_dates = sorted(date_scores.keys())
    trend_points: List[AttemptTrendPoint] = []
    for d in sorted_dates:
        scores = date_scores[d]
        avg_score = round(sum(scores) / len(scores), 2) if scores else 0.0
        trend_points.append(
            AttemptTrendPoint(
                date=d,
                attempt_count=len(scores),
                average_score_percentage=avg_score,
            )
        )

    return VelocityTrendsResponse(
        course_id=course_id,
        learner_id=learner_id,
        days=days,
        trends=trend_points,
    )
