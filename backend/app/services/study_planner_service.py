"""
Adaptive Study Planner Service for Edvora.

Bridges BKT learner mastery estimates, prerequisite knowledge graphs,
assessment history, and course materials to construct an actionable,
explainable study plan.
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Set
from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload

from app.models.course import Course
from app.models.topic import Topic
from app.models.concept import Concept, ConceptPrerequisite
from app.models.learner_mastery import LearnerConceptMastery, DEFAULT_P_L0
from app.models.assessment import Assessment, Question
from app.models.content_unit import ContentUnit


MASTERY_THRESHOLD = 0.70      # Concept considered mastered
WEAK_THRESHOLD = 0.50         # Concept needs immediate revision
RETENTION_DECAY_DAYS = 7      # Days without practice before suggesting retention refresh


def verify_course_exists(db: Session, course_id: str, student_id: Optional[str] = None) -> Course:
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(
            status_code=404,
            detail=f"Course '{course_id}' not found."
        )
    if student_id and course.owner_id is not None and course.owner_id != student_id:
        raise HTTPException(
            status_code=404,
            detail=f"Course '{course_id}' not found."
        )
    return course


def calculate_study_plan_data(
    db: Session,
    course_id: str,
    student_id: str = "default_student",
) -> Dict[str, Any]:
    """
    Core planning engine: evaluates prerequisite DAG readiness,
    computes multi-factor priority scores, and synthesizes study plans.
    """
    course = verify_course_exists(db, course_id, student_id=student_id)

    # 1. Fetch all topics and concepts for this course in order
    topics = (
        db.query(Topic)
        .options(joinedload(Topic.concepts))
        .filter(Topic.course_id == course_id)
        .order_by(Topic.order_index, Topic.created_at)
        .all()
    )

    all_concepts: List[Concept] = []
    concept_to_topic: Dict[str, Topic] = {}
    for t in topics:
        for c in t.concepts:
            all_concepts.append(c)
            concept_to_topic[c.id] = t

    concept_map: Dict[str, Concept] = {c.id: c for c in all_concepts}

    # 2. Fetch prerequisite relationships in this course
    prereq_edges = (
        db.query(ConceptPrerequisite)
        .join(Concept, ConceptPrerequisite.concept_id == Concept.id)
        .filter(Concept.course_id == course_id)
        .all()
    )

    # direct_prereqs: concept_id -> set of prerequisite concept_ids
    # direct_dependents: prerequisite_id -> set of downstream dependent concept_ids
    direct_prereqs: Dict[str, Set[str]] = {c.id: set() for c in all_concepts}
    direct_dependents: Dict[str, Set[str]] = {c.id: set() for c in all_concepts}

    for edge in prereq_edges:
        if edge.concept_id in direct_prereqs and edge.prerequisite_id in concept_map:
            direct_prereqs[edge.concept_id].add(edge.prerequisite_id)
        if edge.prerequisite_id in direct_dependents and edge.concept_id in concept_map:
            direct_dependents[edge.prerequisite_id].add(edge.concept_id)

    # 3. Fetch learner's current BKT masteries
    mastery_records = (
        db.query(LearnerConceptMastery)
        .filter(
            LearnerConceptMastery.course_id == course_id,
            LearnerConceptMastery.student_id == student_id,
        )
        .all()
    )
    mastery_map: Dict[str, LearnerConceptMastery] = {m.concept_id: m for m in mastery_records}

    now = datetime.now(timezone.utc)

    # 4. Evaluate each concept's mastery, readiness, and category
    concept_analysis = []
    total_mastery_sum = 0.0

    for c in all_concepts:
        m = mastery_map.get(c.id)
        p_l = m.mastery_probability if m else DEFAULT_P_L0
        obs_count = m.observation_count if m else 0
        last_attempt = m.last_attempt_at if m else None

        total_mastery_sum += p_l

        # Check prerequisite satisfaction: every prereq must have P(L) >= MASTERY_THRESHOLD
        unmet_prereq_names = []
        is_ready = True
        for prereq_id in direct_prereqs.get(c.id, set()):
            prereq_m = mastery_map.get(prereq_id)
            prereq_pl = prereq_m.mastery_probability if prereq_m else DEFAULT_P_L0
            if prereq_pl < MASTERY_THRESHOLD:
                is_ready = False
                unmet_prereq_names.append(concept_map[prereq_id].name)

        # Count unmastered downstream concepts blocked by this concept
        unblocked_dependents = 0
        for dep_id in direct_dependents.get(c.id, set()):
            dep_m = mastery_map.get(dep_id)
            dep_pl = dep_m.mastery_probability if dep_m else DEFAULT_P_L0
            if dep_pl < MASTERY_THRESHOLD:
                unblocked_dependents += 1

        # Classify priority category
        if p_l >= MASTERY_THRESHOLD:
            # Mastered, but check if spaced retention refresh is recommended
            if last_attempt:
                attempt_dt = last_attempt if last_attempt.tzinfo else last_attempt.replace(tzinfo=timezone.utc)
                if (now - attempt_dt).days >= RETENTION_DECAY_DAYS:
                    category = "REFRESH_RETENTION"
                else:
                    category = "MASTERED"
            else:
                category = "MASTERED"
        elif not is_ready:
            category = "BLOCKED"
        elif obs_count > 0 and p_l < WEAK_THRESHOLD:
            category = "REVISE_WEAK"
        elif unblocked_dependents > 0:
            category = "UNBLOCK_PREREQUISITE"
        else:
            category = "LEARN_NEW"

        # Multi-factor Priority Scoring Engine:
        # S(c) = w_deficit*(1 - P(L)) + w_blocker*BlockerScore + w_recency*DecayScore + w_order*OrderScore
        if not is_ready:
            priority_score = 0.0
        elif category == "MASTERED":
            priority_score = 0.05
        else:
            deficit_weight = 0.50 * (1.0 - p_l)
            blocker_weight = 0.30 * min(1.0, unblocked_dependents / 3.0)

            # Recency / decay bonus if practiced before and forgotten
            recency_weight = 0.0
            if last_attempt:
                attempt_dt = last_attempt if last_attempt.tzinfo else last_attempt.replace(tzinfo=timezone.utc)
                if (now - attempt_dt).days >= RETENTION_DECAY_DAYS:
                    days_factor = min(30, (now - attempt_dt).days) / 30.0
                    recency_weight = 0.15 * days_factor

            # Earlier curriculum order progression factor (tie-breaker)
            topic_order = concept_to_topic[c.id].order_index
            order_weight = 0.05 * (1.0 / (1.0 + topic_order * 5 + c.order_index))

            # Bonus for struggling weak concept vs brand new
            struggle_bonus = 0.10 if (obs_count > 0 and p_l < WEAK_THRESHOLD) else 0.0

            priority_score = round(
                deficit_weight + blocker_weight + recency_weight + order_weight + struggle_bonus,
                4
            )

        concept_analysis.append({
            "concept_id": c.id,
            "concept_name": c.name,
            "topic_id": concept_to_topic[c.id].id,
            "topic_title": concept_to_topic[c.id].title,
            "order_index": c.order_index,
            "mastery_probability": round(p_l, 4),
            "observation_count": obs_count,
            "is_ready": is_ready,
            "priority_score": priority_score,
            "priority_category": category,
            "unmet_prerequisites": sorted(unmet_prereq_names),
            "unblocked_dependents_count": unblocked_dependents,
            "last_attempt_at": last_attempt,
        })

    # Sort prioritized concepts descending by priority_score
    concept_analysis.sort(key=lambda x: (x["priority_score"], -x["mastery_probability"]), reverse=True)

    total_concepts = len(all_concepts)
    overall_mastery = round(total_mastery_sum / total_concepts, 4) if total_concepts > 0 else 0.0

    # Summary metrics
    mastered_count = sum(1 for c in concept_analysis if c["priority_category"] == "MASTERED")
    needs_revision_count = sum(1 for c in concept_analysis if c["priority_category"] in ("REVISE_WEAK", "REFRESH_RETENTION"))
    ready_to_learn_count = sum(1 for c in concept_analysis if c["priority_category"] in ("LEARN_NEW", "UNBLOCK_PREREQUISITE"))
    blocked_count = sum(1 for c in concept_analysis if c["priority_category"] == "BLOCKED")

    summary = {
        "total_concepts": total_concepts,
        "mastered_concepts": mastered_count,
        "needs_revision": needs_revision_count,
        "ready_to_learn": ready_to_learn_count,
        "blocked_concepts": blocked_count,
    }

    # 5. Top recommendation synthesis
    top_recommendation = None
    if total_concepts > 0:
        top_cand = concept_analysis[0]

        # All concepts mastered edge case
        if top_cand["priority_category"] == "MASTERED" and top_cand["priority_score"] <= 0.05:
            top_recommendation = {
                "course_id": course_id,
                "concept_id": top_cand["concept_id"],
                "concept_name": top_cand["concept_name"],
                "topic_id": top_cand["topic_id"],
                "topic_title": top_cand["topic_title"],
                "priority_category": "COURSE_COMPLETED",
                "mastery_probability": top_cand["mastery_probability"],
                "status_text": "All concepts mastered",
                "rationale": "Outstanding achievement! You have achieved high mastery across all curriculum concepts.",
                "unblocked_dependents_count": 0,
                "recommended_actions": [
                    {
                        "step": 1,
                        "title": f"Take a comprehensive mock exam for {course.title}",
                        "action_type": "practice_quiz",
                        "details": "Verify overall course retention with a mixed assessment."
                    }
                ]
            }
        else:
            # Fetch contextual resources for top candidate: content units & assessments
            unit = (
                db.query(ContentUnit)
                .filter(ContentUnit.course_id == course_id)
                .first()
            )
            has_question = (
                db.query(Question)
                .join(Assessment, Question.assessment_id == Assessment.id)
                .filter(Assessment.course_id == course_id, Question.concept_id == top_cand["concept_id"])
                .first()
            )

            actions = generate_recommended_actions(
                concept_name=top_cand["concept_name"],
                topic_title=top_cand["topic_title"],
                category=top_cand["priority_category"],
                has_assessment=has_question is not None,
                sample_unit=unit
            )

            rationale, status_text = generate_rationale(
                concept_name=top_cand["concept_name"],
                category=top_cand["priority_category"],
                mastery=top_cand["mastery_probability"],
                blocked_count=top_cand["unblocked_dependents_count"]
            )

            top_recommendation = {
                "course_id": course_id,
                "concept_id": top_cand["concept_id"],
                "concept_name": top_cand["concept_name"],
                "topic_id": top_cand["topic_id"],
                "topic_title": top_cand["topic_title"],
                "priority_category": top_cand["priority_category"],
                "mastery_probability": top_cand["mastery_probability"],
                "status_text": status_text,
                "rationale": rationale,
                "unblocked_dependents_count": top_cand["unblocked_dependents_count"],
                "recommended_actions": actions,
            }

    return {
        "course_id": course_id,
        "student_id": student_id,
        "generated_at": now,
        "overall_course_mastery": overall_mastery,
        "top_recommendation": top_recommendation,
        "prioritized_concepts": concept_analysis,
        "summary": summary,
    }


def generate_rationale(
    concept_name: str,
    category: str,
    mastery: float,
    blocked_count: int
) -> (str, str):
    """Generate clear, pedagogically grounded rationale."""
    pct = int(round(mastery * 100))

    if category == "REVISE_WEAK":
        status_text = "Needs attention"
        rationale = (
            f"Current mastery for '{concept_name}' is {pct}%. "
            f"All prerequisites are satisfied, but recent practice indicates difficulty."
        )
    elif category == "UNBLOCK_PREREQUISITE":
        status_text = "High leverage unblocker"
        dependents_str = "downstream concept" if blocked_count == 1 else "downstream concepts"
        rationale = (
            f"Mastering '{concept_name}' ({pct}% mastery) directly unblocks {blocked_count} {dependents_str} "
            f"in the course curriculum."
        )
    elif category == "REFRESH_RETENTION":
        status_text = "Retention refresh"
        rationale = (
            f"You previously demonstrated high mastery ({pct}%) in '{concept_name}', "
            f"but have not practiced it in over {RETENTION_DECAY_DAYS} days. A quick review prevents knowledge decay."
        )
    elif category == "LEARN_NEW":
        status_text = "Ready to learn"
        rationale = (
            f"All prerequisite concepts for '{concept_name}' are mastered. "
            f"You are cognitively ready to learn this new concept."
        )
    else:
        status_text = "In progress"
        rationale = f"Continue progressing on '{concept_name}'."

    return rationale, status_text


def generate_recommended_actions(
    concept_name: str,
    topic_title: str,
    category: str,
    has_assessment: bool,
    sample_unit: Optional[ContentUnit]
) -> List[Dict[str, Any]]:
    """Synthesize concrete next steps for the student."""
    unit_ref = f"Page {sample_unit.page_number}" if sample_unit and sample_unit.page_number else "Course Material"

    step_1 = {
        "step": 1,
        "title": f"Review source notes for {concept_name}",
        "action_type": "review_material",
        "details": f"{topic_title} — {unit_ref}"
    }
    step_2 = {
        "step": 2,
        "title": f"Ask AI Tutor: Clarify core mechanisms of {concept_name}",
        "action_type": "ask_tutor",
        "details": f"Explain key principles and common pitfalls of {concept_name}"
    }
    step_3 = {
        "step": 3,
        "title": f"Complete targeted practice for {concept_name}",
        "action_type": "practice_quiz",
        "details": "Assessment questions available" if has_assessment else "Self-check practice quiz"
    }

    return [step_1, step_2, step_3]
