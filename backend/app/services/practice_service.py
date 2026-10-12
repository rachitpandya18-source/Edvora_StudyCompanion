import json
import logging
from typing import Dict, Any, List, Optional, Set
from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload

from app.models.course import Course
from app.models.topic import Topic
from app.models.concept import Concept
from app.models.assessment import Assessment, Question, AssessmentAttempt
from app.models.learner_mastery import LearnerConceptMastery, DEFAULT_P_L0
from app.schemas.practice import (
    PracticeGenerateRequest,
    PracticeSessionResponse,
    PracticeQuestionItem,
    PracticeConfigOptions,
    PracticeOptionItem,
)
from app.services import (
    assessment_service,
    bkt_service,
    study_planner_service,
    retrieval_service,
    llm_service,
    question_similarity_service,
    question_grounding_service,
)

logger = logging.getLogger(__name__)

SUPPORTED_QUESTION_TYPES = {"mcq", "true_false", "short_answer"}
DEFAULT_QUESTION_COUNT = 5


def _verify_course_exists(db: Session, course_id: str, student_id: Optional[str] = None) -> Course:
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


def get_practice_options(db: Session, course_id: str, student_id: Optional[str] = None) -> PracticeConfigOptions:
    """
    Returns available course topics with concept counts, supported question types,
    difficulties, and recommended concept based on study planner analysis.
    """
    _verify_course_exists(db, course_id, student_id=student_id)

    topics = (
        db.query(Topic)
        .options(joinedload(Topic.concepts))
        .filter(Topic.course_id == course_id)
        .order_by(Topic.order_index, Topic.created_at)
        .all()
    )

    topic_options = [
        PracticeOptionItem(
            id=t.id,
            name=t.title,
            concept_count=len(t.concepts),
        )
        for t in topics
    ]

    question_types = [
        {"value": "mcq", "label": "Multiple Choice"},
        {"value": "true_false", "label": "True / False"},
        {"value": "short_answer", "label": "Short Answer"},
    ]

    difficulties = [
        {"value": "easy", "label": "Easy"},
        {"value": "medium", "label": "Medium"},
        {"value": "hard", "label": "Hard"},
    ]

    rec_concept_id = None
    rec_concept_name = None
    try:
        plan_data = study_planner_service.calculate_study_plan_data(
            db=db,
            course_id=course_id,
            student_id="default_student",
        )
        top_rec = plan_data.get("top_recommendation")
        if top_rec:
            rec_concept_id = top_rec.get("concept_id")
            rec_concept_name = top_rec.get("concept_name")
    except Exception as e:
        logger.warning(f"Failed to fetch study planner recommendation: {e}")

    return PracticeConfigOptions(
        course_id=course_id,
        topics=topic_options,
        question_types=question_types,
        difficulties=difficulties,
        recommended_concept_id=rec_concept_id,
        recommended_concept_name=rec_concept_name,
    )


def _generate_fallback_question(
    concept: Concept,
    course: Course,
    q_type: str = "mcq",
    order_index: int = 1,
) -> Dict[str, Any]:
    """
    Deterministically constructs a curriculum-grounded fallback question
    for when LLM is unavailable, offline, or returns invalid format.
    """
    if q_type == "true_false":
        prompts_tf = [
            f"True or False: In '{course.title}', understanding '{concept.name}' is an essential curriculum objective.",
            f"True or False: The concept '{concept.name}' operates as a key component within '{course.title}'.",
            f"True or False: Study materials for '{course.title}' explicitly define and analyze '{concept.name}'.",
        ]
        return {
            "prompt": prompts_tf[(order_index - 1) % len(prompts_tf)],
            "question_type": "true_false",
            "options_json": ["True", "False"],
            "correct_answer": "True",
            "explanation": f"'{concept.name}' is formally indexed in the syllabus for '{course.title}'.",
            "concept_id": concept.id,
            "marks": 1.0,
        }
    elif q_type == "short_answer":
        prompts_sa = [
            f"Identify the subject concept related to '{concept.name}' in {course.title}.",
            f"Name the key conceptual unit governing '{concept.name}' within {course.title}.",
            f"State the foundational topic represented by '{concept.name}' in {course.title}.",
        ]
        return {
            "prompt": prompts_sa[(order_index - 1) % len(prompts_sa)],
            "question_type": "short_answer",
            "options_json": None,
            "correct_answer": concept.name,
            "explanation": f"The core subject concept is '{concept.name}'.",
            "concept_id": concept.id,
            "marks": 1.0,
        }
    else:  # default mcq
        prompts_mcq = [
            f"Which statement best characterizes the core principle of '{concept.name}' in '{course.title}'?",
            f"In '{course.title}', how is the concept '{concept.name}' primarily applied in practice?",
            f"What distinguishes '{concept.name}' from unrelated topics outside of '{course.title}'?",
            f"Which of the following scenarios best demonstrates the function of '{concept.name}' in '{course.title}'?",
            f"Why is understanding '{concept.name}' considered critical to mastering '{course.title}'?",
        ]
        return {
            "prompt": prompts_mcq[(order_index - 1) % len(prompts_mcq)],
            "question_type": "mcq",
            "options_json": [
                f"Core foundations, definitions, and applications of {concept.name}",
                f"An external concept unrelated to the curriculum of {course.title}",
                f"A deprecated convention excluded from modern study of {course.title}",
                f"An ungrounded claim not supported by course learning materials",
            ],
            "correct_answer": f"Core foundations, definitions, and applications of {concept.name}",
            "explanation": f"'{concept.name}' establishes the fundamental mechanisms and concepts taught in {course.title}.",
            "concept_id": concept.id,
            "marks": 1.0,
        }


def _extract_questions_from_llm_json(raw_text: str) -> List[Dict[str, Any]]:
    """Clean markdown fences and parse list of question objects."""
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()

    try:
        data = json.loads(cleaned)
    except Exception:
        return []

    if isinstance(data, dict):
        if "questions" in data and isinstance(data["questions"], list):
            data = data["questions"]
        else:
            data = [data]

    if not isinstance(data, list):
        return []

    valid_questions = []
    for item in data:
        if not isinstance(item, dict):
            continue
        prompt = item.get("prompt") or item.get("question")
        correct_answer = item.get("correct_answer")
        q_type = str(item.get("question_type", "mcq")).lower()
        if not prompt or not correct_answer:
            continue

        options = item.get("options") or item.get("options_json")
        if q_type == "mcq":
            if not isinstance(options, list) or len(options) < 2:
                continue
            # Ensure correct answer matches one option
            if str(correct_answer).strip() not in [str(o).strip() for o in options]:
                # If correct_answer is 'A', 'B', etc. map it
                letter_map = {"a": 0, "b": 1, "c": 2, "d": 3}
                c_clean = str(correct_answer).strip().lower()
                if c_clean in letter_map and letter_map[c_clean] < len(options):
                    correct_answer = options[letter_map[c_clean]]
                else:
                    options.append(str(correct_answer).strip())

        elif q_type == "true_false":
            options = ["True", "False"]
            if str(correct_answer).strip().lower() in ("true", "t", "1"):
                correct_answer = "True"
            else:
                correct_answer = "False"
        else:
            options = None

        valid_questions.append({
            "prompt": str(prompt).strip(),
            "question_type": q_type if q_type in SUPPORTED_QUESTION_TYPES else "mcq",
            "options_json": options,
            "correct_answer": str(correct_answer).strip(),
            "explanation": str(item.get("explanation", "Course grounded explanation.")).strip(),
            "marks": float(item.get("marks", 1.0)),
        })

    return valid_questions


def _generate_candidate_questions_via_llm(
    course: Course,
    concept: Concept,
    context_text: str,
    target_count: int,
    difficulty: str,
    allowed_types: List[str],
) -> List[Dict[str, Any]]:
    """
    Calls LLM with structured prompt to generate grounded practice questions.
    """
    preferred_type = allowed_types[0] if allowed_types else "mcq"

    prompt = f"""You are an educational assessment expert for the course: "{course.title}".
Generate {target_count} {preferred_type} practice questions testing the concept: "{concept.name}".
Difficulty Level: {difficulty}

==================================================
STUDY MATERIAL / CONTEXT
==================================================
{context_text}

==================================================
RULES
==================================================
1. Every question must test understanding of "{concept.name}".
2. Questions must be grounded in the course material provided.
3. For multiple-choice (mcq), provide exactly 4 options. The correct answer must be one of the 4 options.
4. For true_false, options must be ["True", "False"].
5. For short_answer, options must be null.
6. Provide a concise, educational explanation.

OUTPUT ONLY JSON (no markdown formatting, no code blocks):
[
  {{
    "prompt": "Question text here?",
    "question_type": "{preferred_type}",
    "options": ["Option 1", "Option 2", "Option 3", "Option 4"],
    "correct_answer": "Option 1",
    "explanation": "Explanation here."
  }}
]
"""
    try:
        response = llm_service.generate_response(prompt)
        candidates = _extract_questions_from_llm_json(response)
        return candidates
    except Exception as e:
        logger.warning(f"LLM question generation failed: {e}")
        return []


def generate_practice_session(
    db: Session,
    course_id: str,
    request: PracticeGenerateRequest,
) -> PracticeSessionResponse:
    """
    Assembles a course-grounded practice session, persists it as an Assessment,
    and initiates an active AssessmentAttempt for the student.
    """
    course = _verify_course_exists(db, course_id, student_id=request.student_id)

    # 1. Validate Mode
    mode = request.mode.strip().lower()
    if mode not in ("adaptive", "quick", "mock_test"):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid practice mode '{request.mode}'. Supported modes: 'adaptive', 'quick', 'mock_test'."
        )

    # 2. Validate Topic if provided
    selected_topic: Optional[Topic] = None
    if request.topic_id:
        selected_topic = (
            db.query(Topic)
            .filter(Topic.id == request.topic_id, Topic.course_id == course_id)
            .first()
        )
        if not selected_topic:
            # Check if topic belongs to another course or does not exist
            other_topic = db.query(Topic).filter(Topic.id == request.topic_id).first()
            if other_topic:
                raise HTTPException(
                    status_code=400,
                    detail=f"Topic '{request.topic_id}' does not belong to course '{course_id}'."
                )
            raise HTTPException(
                status_code=404,
                detail=f"Topic '{request.topic_id}' not found."
            )

    # 3. Validate Concept if provided
    selected_concept: Optional[Concept] = None
    if request.concept_id:
        selected_concept = (
            db.query(Concept)
            .join(Topic, Concept.topic_id == Topic.id)
            .filter(Concept.id == request.concept_id, Topic.course_id == course_id)
            .first()
        )
        if not selected_concept:
            other_concept = db.query(Concept).filter(Concept.id == request.concept_id).first()
            if other_concept:
                raise HTTPException(
                    status_code=400,
                    detail=f"Concept '{request.concept_id}' does not belong to course '{course_id}'."
                )
            raise HTTPException(
                status_code=404,
                detail=f"Concept '{request.concept_id}' not found."
            )

        if selected_topic and selected_concept.topic_id != selected_topic.id:
            raise HTTPException(
                status_code=400,
                detail=f"Concept '{selected_concept.id}' does not belong to topic '{selected_topic.id}'."
            )

    # 4. Fetch Course Concepts pool
    concept_query = (
        db.query(Concept)
        .join(Topic, Concept.topic_id == Topic.id)
        .filter(Topic.course_id == course_id)
    )
    if selected_topic:
        concept_query = concept_query.filter(Topic.id == selected_topic.id)

    available_concepts = concept_query.order_by(Topic.order_index, Concept.order_index).all()
    if not available_concepts:
        raise HTTPException(
            status_code=400,
            detail=f"No concepts found in course '{course_id}' for practice generation."
        )

    # 5. Concept Selection Strategy per Mode
    target_concepts: List[Concept] = []
    question_count = request.question_count or DEFAULT_QUESTION_COUNT

    if mode == "adaptive":
        if selected_concept:
            target_concepts = [selected_concept] * question_count
        else:
            # Check B7 Study Planner top recommendation
            recommended_id = None
            try:
                plan = study_planner_service.calculate_study_plan_data(
                    db=db,
                    course_id=course_id,
                    student_id=request.student_id,
                )
                if plan.get("top_recommendation"):
                    recommended_id = plan["top_recommendation"].get("concept_id")
            except Exception:
                pass

            target = None
            if recommended_id:
                target = next((c for c in available_concepts if c.id == recommended_id), None)
            if not target:
                target = available_concepts[0]
            target_concepts = [target] * question_count

    elif mode == "quick":
        # Mixed practice from concepts with mastery below 0.70
        try:
            masteries = bkt_service.get_course_learner_masteries(
                db=db,
                course_id=course_id,
                student_id=request.student_id,
            )
            weak_concept_ids = {
                m["concept_id"]
                for m in masteries
                if m["mastery_probability"] < 0.70
            }
        except Exception:
            weak_concept_ids = set()

        weak_pool = [c for c in available_concepts if c.id in weak_concept_ids]
        pool = weak_pool if weak_pool else available_concepts

        # Distribute question_count across pool
        for i in range(question_count):
            target_concepts.append(pool[i % len(pool)])

    else:  # mock_test
        # Broader curriculum sampling
        for i in range(question_count):
            target_concepts.append(available_concepts[i % len(available_concepts)])

    # 6. Question Types Filtering
    allowed_types = ["mcq"]
    if request.question_types:
        filtered = [t.lower().strip() for t in request.question_types if t.lower().strip() in SUPPORTED_QUESTION_TYPES]
        if filtered:
            allowed_types = filtered

    difficulty = request.difficulty or "medium"

    # 7. Generate or Assemble Questions
    assembled_questions: List[Dict[str, Any]] = []
    seen_prompts: List[str] = []

    for idx, concept in enumerate(target_concepts):
        q_type = allowed_types[idx % len(allowed_types)]

        # Step 7A: Retrieve persistent ContentUnits for grounding
        context_text = ""
        try:
            retrieved_chunks = retrieval_service.search_course_content(
                db=db,
                course_id=course_id,
                query=f"{concept.name} {concept.description or ''}",
                top_k=2,
            )
            if retrieved_chunks:
                context_text = "\n\n".join(c["text"] for c in retrieved_chunks)
        except Exception as e:
            logger.debug(f"Retrieval error for concept '{concept.name}': {e}")

        if not context_text.strip():
            context_text = f"Concept: {concept.name}\nDescription: {concept.description or 'Core curricular concept.'}"

        # Step 7B: Attempt LLM generation
        candidate_q: Optional[Dict[str, Any]] = None
        candidates = _generate_candidate_questions_via_llm(
            course=course,
            concept=concept,
            context_text=context_text,
            target_count=1,
            difficulty=difficulty,
            allowed_types=[q_type],
        )

        for cand in candidates:
            cand_prompt = cand["prompt"]
            if question_similarity_service.is_similar_question(cand_prompt, seen_prompts):
                continue
            cand["concept_id"] = concept.id
            candidate_q = cand
            break

        # Step 7C: Fallback if LLM produced no valid candidate
        if not candidate_q:
            # Check existing question bank for this concept
            existing_db_q = (
                db.query(Question)
                .join(Assessment, Question.assessment_id == Assessment.id)
                .filter(Assessment.course_id == course_id, Question.concept_id == concept.id)
                .first()
            )
            if existing_db_q and not question_similarity_service.is_similar_question(existing_db_q.prompt, seen_prompts):
                candidate_q = {
                    "prompt": existing_db_q.prompt,
                    "question_type": existing_db_q.question_type,
                    "options_json": existing_db_q.options_json,
                    "correct_answer": existing_db_q.correct_answer,
                    "explanation": existing_db_q.explanation or f"Standard explanation for {concept.name}.",
                    "concept_id": concept.id,
                    "marks": existing_db_q.marks,
                }
            else:
                candidate_q = _generate_fallback_question(
                    concept=concept,
                    course=course,
                    q_type=q_type,
                    order_index=idx + 1,
                )

        seen_prompts.append(candidate_q["prompt"])
        assembled_questions.append(candidate_q)

    # 8. Persist Assessment & Questions into B5 Schema
    target_primary_concept = target_concepts[0] if target_concepts else None
    if mode == "adaptive" and target_primary_concept:
        title = f"Adaptive Practice: {target_primary_concept.name}"
        desc = f"Targeted concept practice on '{target_primary_concept.name}'."
    elif mode == "quick":
        title = f"Quick Practice ({course.title})"
        desc = f"Dynamic revision focusing on weak and unmastered concepts."
    else:
        title = f"Mock Exam ({course.title})"
        desc = f"Comprehensive curriculum review across course topics."

    total_marks = sum(q.get("marks", 1.0) for q in assembled_questions)

    assessment = Assessment(
        course_id=course_id,
        title=title,
        description=desc,
        assessment_type="practice",
        time_limit_minutes=len(assembled_questions) * 2,
        total_marks=total_marks,
    )
    db.add(assessment)
    db.flush()

    for idx, q_data in enumerate(assembled_questions):
        question = Question(
            assessment_id=assessment.id,
            concept_id=q_data.get("concept_id"),
            question_type=q_data.get("question_type", "mcq"),
            prompt=q_data["prompt"],
            options_json=q_data.get("options_json"),
            correct_answer=q_data["correct_answer"],
            explanation=q_data.get("explanation"),
            order_index=idx + 1,
            marks=q_data.get("marks", 1.0),
        )
        db.add(question)

    db.commit()
    db.refresh(assessment)

    # 9. Start Attempt via B5 Lifecycle
    attempt = assessment_service.start_attempt(
        db=db,
        course_id=course_id,
        assessment_id=assessment.id,
        student_id=request.student_id,
    )

    # 10. Build Student-Safe Response
    student_questions: List[PracticeQuestionItem] = []
    for q in sorted(assessment.questions, key=lambda x: x.order_index):
        student_questions.append(
            PracticeQuestionItem(
                id=q.id,
                assessment_id=q.assessment_id,
                concept_id=q.concept_id,
                question_type=q.question_type,
                prompt=q.prompt,
                order_index=q.order_index,
                marks=q.marks,
                options_json=q.options_json,
            )
        )

    submit_endpoint = f"/courses/{course_id}/assessments/{assessment.id}/attempts/{attempt.id}/submit"

    topic_title = None
    if selected_topic:
        topic_title = selected_topic.title
    elif target_primary_concept and target_primary_concept.topic:
        topic_title = target_primary_concept.topic.title

    return PracticeSessionResponse(
        assessment_id=assessment.id,
        attempt_id=attempt.id,
        course_id=course_id,
        mode=mode,
        title=assessment.title,
        description=assessment.description,
        concept_id=target_primary_concept.id if (mode == "adaptive" and target_primary_concept) else None,
        concept_name=target_primary_concept.name if (mode == "adaptive" and target_primary_concept) else None,
        topic_id=selected_topic.id if selected_topic else None,
        topic_title=topic_title,
        total_questions=len(student_questions),
        time_limit_minutes=assessment.time_limit_minutes,
        total_marks=assessment.total_marks,
        questions=student_questions,
        submit_endpoint=submit_endpoint,
    )
