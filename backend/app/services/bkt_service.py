from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.course import Course
from app.models.concept import Concept
from app.models.assessment import AssessmentAttempt
from app.models.learner_mastery import (
    LearnerConceptMastery,
    DEFAULT_P_L0,
    DEFAULT_P_T,
    DEFAULT_P_G,
    DEFAULT_P_S,
)


# ============================================================================
# Pure BKT Calculation Engine
# ============================================================================

def validate_bkt_parameters(
    p_l0: float,
    p_t: float,
    p_g: float,
    p_s: float,
) -> None:
    """
    Validate that all BKT parameters are legitimate probabilities within [0.0, 1.0],
    and that the cognitive validity condition P(G) + P(S) < 1.0 is strictly satisfied.
    If P(G) + P(S) >= 1.0, the observation of a correct response would counter-intuitively
    decrease mastery or provide non-diagnostic noise.
    """
    params = [
        ("P(L0)", p_l0),
        ("P(T)", p_t),
        ("P(G)", p_g),
        ("P(S)", p_s),
    ]
    for name, val in params:
        if val is None or not (0.0 <= val <= 1.0):
            raise ValueError(f"{name} must be within [0.0, 1.0], got {val}")

    if (p_g + p_s) >= 1.0:
        raise ValueError(
            f"Invalid BKT parameters: Guess + Slip (P(G) + P(S)) must be < 1.0 "
            f"(got P(G)={p_g}, P(S)={p_s}, sum={p_g + p_s:.4f}). "
            f"Higher guess/slip rates invert pedagogical diagnostic validity."
        )


def calculate_bkt_update(
    current_mastery: float,
    is_correct: bool,
    p_t: float = DEFAULT_P_T,
    p_g: float = DEFAULT_P_G,
    p_s: float = DEFAULT_P_S,
) -> float:
    """
    Perform a single standard Bayesian Knowledge Tracing (BKT) update:
    1. Observation update (Bayes' Rule):
       P(L_{t-1} | correct)   = [L_{t-1} * (1 - S)] / [L_{t-1} * (1 - S) + (1 - L_{t-1}) * G]
       P(L_{t-1} | incorrect) = [L_{t-1} * S]       / [L_{t-1} * S       + (1 - L_{t-1}) * (1 - G)]
    2. Learning transition:
       P(L_t) = P(L_{t-1} | obs) + (1 - P(L_{t-1} | obs)) * T

    Returns:
       Updated mastery probability P(L_t) clamped to [0.0, 1.0], rounded to 4 decimals.
    """
    validate_bkt_parameters(p_l0=DEFAULT_P_L0, p_t=p_t, p_g=p_g, p_s=p_s)

    l_prev = max(0.0, min(1.0, float(current_mastery)))

    # Step 1: Observation update (posterior)
    if is_correct:
        numerator = l_prev * (1.0 - p_s)
        denominator = numerator + ((1.0 - l_prev) * p_g)
    else:
        numerator = l_prev * p_s
        denominator = numerator + ((1.0 - l_prev) * (1.0 - p_g))

    if denominator <= 1e-12:
        # Denominator effectively 0 (extreme edge case)
        posterior = 1.0 if numerator > 0 else 0.0
    else:
        posterior = numerator / denominator

    # Step 2: Learning transition update
    l_next = posterior + ((1.0 - posterior) * p_t)

    # Step 3: Clamp to valid probability interval [0.0, 1.0]
    clamped = max(0.0, min(1.0, l_next))
    return round(clamped, 4)


# ============================================================================
# Persistent Learner State Service
# ============================================================================

def get_or_create_mastery(
    db: Session,
    student_id: str,
    course_id: str,
    concept_id: str,
    p_l0: float = DEFAULT_P_L0,
    p_t: float = DEFAULT_P_T,
    p_g: float = DEFAULT_P_G,
    p_s: float = DEFAULT_P_S,
) -> LearnerConceptMastery:
    """
    Retrieve existing learner mastery record for (student_id, concept_id),
    or initialize a new record with prior knowledge probability P(L0).
    """
    validate_bkt_parameters(p_l0, p_t, p_g, p_s)

    mastery = (
        db.query(LearnerConceptMastery)
        .filter(
            LearnerConceptMastery.student_id == student_id,
            LearnerConceptMastery.concept_id == concept_id,
        )
        .first()
    )

    if not mastery:
        mastery = LearnerConceptMastery(
            student_id=student_id,
            course_id=course_id,
            concept_id=concept_id,
            mastery_probability=round(p_l0, 4),
            observation_count=0,
            correct_count=0,
            p_l0=p_l0,
            p_t=p_t,
            p_g=p_g,
            p_s=p_s,
        )
        db.add(mastery)
        db.flush()

    return mastery


def update_mastery_from_attempt(
    db: Session,
    course_id: str,
    attempt: AssessmentAttempt,
) -> List[LearnerConceptMastery]:
    """
    Update learner concept mastery records based on submitted assessment results.
    Rules:
    - If attempt was already processed for BKT, skip immediately (idempotency).
    - If a question has no concept_id, skip it.
    - If a question's concept does not belong to this course, skip it.
    - If a question was unanswered by the student, skip its BKT update.
    - If a question was answered and evaluated, perform the BKT update.
    """
    if attempt.bkt_processed:
        return []

    # Map student answers by question_id
    answers_map = {ans.question_id: ans for ans in attempt.answers}

    # Fetch valid concepts in this course to verify course scoping
    course_concept_ids = {
        c.id for c in db.query(Concept.id).filter(Concept.course_id == course_id).all()
    }

    updated_records: Dict[str, LearnerConceptMastery] = {}

    for question in attempt.assessment.questions:
        # Rule: Skip questions with no concept association
        if not question.concept_id:
            continue

        # Rule: Skip questions associated with concepts outside this course
        if question.concept_id not in course_concept_ids:
            continue

        ans = answers_map.get(question.id)
        if not ans:
            continue

        # Rule: Skip unanswered questions
        if ans.student_answer is None or str(ans.student_answer).strip() == "":
            continue

        # Valid answered question with valid course concept: perform BKT update
        mastery = updated_records.get(question.concept_id)
        if not mastery:
            mastery = get_or_create_mastery(
                db=db,
                student_id=attempt.student_id,
                course_id=course_id,
                concept_id=question.concept_id,
            )
            updated_records[question.concept_id] = mastery

        # Update mastery probability
        new_mastery = calculate_bkt_update(
            current_mastery=mastery.mastery_probability,
            is_correct=bool(ans.is_correct),
            p_t=mastery.p_t,
            p_g=mastery.p_g,
            p_s=mastery.p_s,
        )

        mastery.mastery_probability = new_mastery
        mastery.observation_count += 1
        if ans.is_correct:
            mastery.correct_count += 1
        mastery.last_attempt_at = attempt.submitted_at or datetime.now(timezone.utc)

    attempt.bkt_processed = True
    db.commit()

    return list(updated_records.values())


# ============================================================================
# Course-Scoped API Queries
# ============================================================================

def get_course_learner_masteries(
    db: Session,
    course_id: str,
    student_id: str = "default_student",
) -> List[Dict[str, Any]]:
    """
    Retrieve learner mastery across all concepts in the specified course.
    If a concept has not yet been practiced by the student, returns default initial
    mastery state (P(L0) prior) so downstream recommenders have full concept visibility.
    """
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(
            status_code=404,
            detail=f"Course '{course_id}' not found."
        )

    # Fetch all concepts in the course in curriculum order
    concepts = (
        db.query(Concept)
        .filter(Concept.course_id == course_id)
        .order_by(Concept.order_index)
        .all()
    )

    # Fetch existing mastery records for this student and course
    existing_masteries = (
        db.query(LearnerConceptMastery)
        .filter(
            LearnerConceptMastery.course_id == course_id,
            LearnerConceptMastery.student_id == student_id,
        )
        .all()
    )
    mastery_map = {m.concept_id: m for m in existing_masteries}

    results = []
    for concept in concepts:
        m = mastery_map.get(concept.id)
        if m:
            results.append({
                "id": m.id,
                "student_id": m.student_id,
                "course_id": m.course_id,
                "concept_id": m.concept_id,
                "concept_name": concept.name,
                "topic_id": concept.topic_id,
                "mastery_probability": m.mastery_probability,
                "observation_count": m.observation_count,
                "correct_count": m.correct_count,
                "last_attempt_at": m.last_attempt_at,
                "p_l0": m.p_l0,
                "p_t": m.p_t,
                "p_g": m.p_g,
                "p_s": m.p_s,
                "created_at": m.created_at,
                "updated_at": m.updated_at,
            })
        else:
            # Unpracticed default state
            results.append({
                "id": None,
                "student_id": student_id,
                "course_id": course_id,
                "concept_id": concept.id,
                "concept_name": concept.name,
                "topic_id": concept.topic_id,
                "mastery_probability": DEFAULT_P_L0,
                "observation_count": 0,
                "correct_count": 0,
                "last_attempt_at": None,
                "p_l0": DEFAULT_P_L0,
                "p_t": DEFAULT_P_T,
                "p_g": DEFAULT_P_G,
                "p_s": DEFAULT_P_S,
                "created_at": None,
                "updated_at": None,
            })

    return results


def get_concept_learner_mastery(
    db: Session,
    course_id: str,
    concept_id: str,
    student_id: str = "default_student",
) -> Dict[str, Any]:
    """
    Retrieve learner mastery for a specific concept in a course.
    Enforces course scoping: validates course exists and concept belongs to course.
    """
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(
            status_code=404,
            detail=f"Course '{course_id}' not found."
        )

    concept = (
        db.query(Concept)
        .filter(Concept.id == concept_id, Concept.course_id == course_id)
        .first()
    )
    if not concept:
        raise HTTPException(
            status_code=404,
            detail=f"Concept '{concept_id}' not found in course '{course_id}'."
        )

    mastery = (
        db.query(LearnerConceptMastery)
        .filter(
            LearnerConceptMastery.concept_id == concept_id,
            LearnerConceptMastery.student_id == student_id,
        )
        .first()
    )

    if mastery:
        return {
            "id": mastery.id,
            "student_id": mastery.student_id,
            "course_id": mastery.course_id,
            "concept_id": mastery.concept_id,
            "concept_name": concept.name,
            "topic_id": concept.topic_id,
            "mastery_probability": mastery.mastery_probability,
            "observation_count": mastery.observation_count,
            "correct_count": mastery.correct_count,
            "last_attempt_at": mastery.last_attempt_at,
            "p_l0": mastery.p_l0,
            "p_t": mastery.p_t,
            "p_g": mastery.p_g,
            "p_s": mastery.p_s,
            "created_at": mastery.created_at,
            "updated_at": mastery.updated_at,
        }

    return {
        "id": None,
        "student_id": student_id,
        "course_id": course_id,
        "concept_id": concept.id,
        "concept_name": concept.name,
        "topic_id": concept.topic_id,
        "mastery_probability": DEFAULT_P_L0,
        "observation_count": 0,
        "correct_count": 0,
        "last_attempt_at": None,
        "p_l0": DEFAULT_P_L0,
        "p_t": DEFAULT_P_T,
        "p_g": DEFAULT_P_G,
        "p_s": DEFAULT_P_S,
        "created_at": None,
        "updated_at": None,
    }


def initialize_concept_mastery(
    db: Session,
    course_id: str,
    concept_id: str,
    student_id: str = "default_student",
    p_l0: Optional[float] = None,
    p_t: Optional[float] = None,
    p_g: Optional[float] = None,
    p_s: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Initialize or reset learner state for a concept with validated parameters.
    """
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(
            status_code=404,
            detail=f"Course '{course_id}' not found."
        )

    concept = (
        db.query(Concept)
        .filter(Concept.id == concept_id, Concept.course_id == course_id)
        .first()
    )
    if not concept:
        raise HTTPException(
            status_code=404,
            detail=f"Concept '{concept_id}' not found in course '{course_id}'."
        )

    init_l0 = p_l0 if p_l0 is not None else DEFAULT_P_L0
    init_t = p_t if p_t is not None else DEFAULT_P_T
    init_g = p_g if p_g is not None else DEFAULT_P_G
    init_s = p_s if p_s is not None else DEFAULT_P_S

    try:
        validate_bkt_parameters(p_l0=init_l0, p_t=init_t, p_g=init_g, p_s=init_s)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    mastery = (
        db.query(LearnerConceptMastery)
        .filter(
            LearnerConceptMastery.concept_id == concept_id,
            LearnerConceptMastery.student_id == student_id,
        )
        .first()
    )

    if mastery:
        mastery.mastery_probability = round(init_l0, 4)
        mastery.observation_count = 0
        mastery.correct_count = 0
        mastery.p_l0 = init_l0
        mastery.p_t = init_t
        mastery.p_g = init_g
        mastery.p_s = init_s
        mastery.last_attempt_at = None
    else:
        mastery = LearnerConceptMastery(
            student_id=student_id,
            course_id=course_id,
            concept_id=concept_id,
            mastery_probability=round(init_l0, 4),
            observation_count=0,
            correct_count=0,
            p_l0=init_l0,
            p_t=init_t,
            p_g=init_g,
            p_s=init_s,
        )
        db.add(mastery)

    db.commit()
    db.refresh(mastery)

    return {
        "id": mastery.id,
        "student_id": mastery.student_id,
        "course_id": mastery.course_id,
        "concept_id": mastery.concept_id,
        "concept_name": concept.name,
        "topic_id": concept.topic_id,
        "mastery_probability": mastery.mastery_probability,
        "observation_count": mastery.observation_count,
        "correct_count": mastery.correct_count,
        "last_attempt_at": mastery.last_attempt_at,
        "p_l0": mastery.p_l0,
        "p_t": mastery.p_t,
        "p_g": mastery.p_g,
        "p_s": mastery.p_s,
        "created_at": mastery.created_at,
        "updated_at": mastery.updated_at,
    }

