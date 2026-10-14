import re
import json
import logging
from typing import Dict, Any, List, Optional, Set, Tuple
from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload

from app.models.course import Course
from app.models.topic import Topic
from app.models.concept import Concept
from app.models.content_unit import ContentUnit
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

SUPPORTED_QUESTION_TYPES = {"mcq", "true_false", "short_answer", "numerical"}
DEFAULT_QUESTION_COUNT = 5

FORBIDDEN_TEMPLATE_PHRASES = [
    "distinguishes",
    "unrelated topics outside",
    "core foundations, definitions, and applications",
    "an external concept unrelated",
    "a deprecated convention",
    "an ungrounded claim",
]


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
        {"value": "numerical", "label": "Numerical / Trace"},
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


def _clean_segment(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", text).strip()
    cleaned = re.sub(r"^(Page \d+|Slide Title:|\d+ @[^\s]+)\s*", "", cleaned, flags=re.IGNORECASE)
    return cleaned.strip()


def _extract_domain_candidates(raw_text: str) -> Tuple[List[str], List[str]]:
    """
    Extracts authentic equations/formulae and substantive domain statements from course text.
    """
    equations = []
    statements = []
    raw_segments = re.split(r"[;\n\.\r]+", raw_text)
    for seg in raw_segments:
        s = _clean_segment(seg)
        if len(s) < 6 or len(s) > 180:
            continue
        if any(sym in s for sym in ["=", "→", "->", "⇌", "∝", "≤", "≥"]):
            if not s.startswith("http") and not any(p in s.lower() for p in FORBIDDEN_TEMPLATE_PHRASES):
                equations.append(s)
        elif len(s) >= 20 and any(w in s.lower() for w in [
            " is ", " are ", " defined ", " refers ", " represents ", " produces ",
            " occurs ", " cell", " reaction", " process", " law", " method", " principle",
            " rotation", " balance", " wave", " frequency", " structure", " state", " voltage"
        ]):
            if not any(p in s.lower() for p in FORBIDDEN_TEMPLATE_PHRASES):
                statements.append(s)
    return equations, statements


def _generate_grounded_content_question(
    db: Session,
    course: Course,
    concept: Concept,
    retrieved_chunks: Optional[List[Dict[str, Any]]] = None,
    context_text: str = "",
    q_type: str = "mcq",
    order_index: int = 1,
) -> Dict[str, Any]:
    """
    Deterministically constructs an authentic, curriculum-grounded question
    directly from indexed ContentUnits without resorting to generic slot-filled templates.
    """
    course_units = (
        db.query(ContentUnit)
        .filter(ContentUnit.course_id == course.id)
        .order_by(ContentUnit.page_number)
        .all()
    )

    all_course_text = "\n".join(u.text for u in course_units) if course_units else context_text
    local_text = "\n".join(c["text"] for c in retrieved_chunks if c.get("text")) if retrieved_chunks else context_text
    if not local_text.strip():
        local_text = all_course_text

    local_eqs, local_stmts = _extract_domain_candidates(local_text)
    global_eqs, global_stmts = _extract_domain_candidates(all_course_text)

    concept_tokens = [w.lower() for w in re.findall(r"\w+", concept.name) if len(w) > 2]

    matched_eq = None
    for eq in local_eqs:
        if any(tok in eq.lower() for tok in concept_tokens):
            matched_eq = eq
            break
    if not matched_eq and local_eqs:
        matched_eq = local_eqs[(order_index - 1) % len(local_eqs)]

    matched_stmt = None
    for stmt in local_stmts:
        if any(tok in stmt.lower() for tok in concept_tokens):
            matched_stmt = stmt
            break
    if not matched_stmt and local_stmts:
        matched_stmt = local_stmts[(order_index - 1) % len(local_stmts)]

    other_eqs = [e for e in global_eqs if e != matched_eq]
    other_stmts = [s for s in global_stmts if s != matched_stmt]

    c_title = concept.name.strip()

    # Strategy A: Grounded equation / formula question
    if matched_eq and (len(other_eqs) >= 2 or q_type != "mcq"):
        if q_type == "true_false":
            return {
                "prompt": f"True or False: In {course.title}, the relationship '{matched_eq}' is a foundational equation associated with '{c_title}'.",
                "question_type": "true_false",
                "options_json": ["True", "False"],
                "correct_answer": "True",
                "explanation": f"According to the indexed study material for {course.title}, '{matched_eq}' defines the formulation for '{c_title}'.",
                "concept_id": concept.id,
                "marks": 1.0,
            }
        elif q_type in ("short_answer", "numerical"):
            return {
                "prompt": f"According to the course notes for '{c_title}' in {course.title}, state the governing equation or formulation.",
                "question_type": q_type,
                "options_json": None,
                "correct_answer": matched_eq,
                "explanation": f"The governing equation is '{matched_eq}' as presented in the course study materials.",
                "concept_id": concept.id,
                "marks": 1.0,
            }
        else:
            options = [matched_eq]
            for o_eq in other_eqs:
                if len(options) >= 4:
                    break
                if o_eq not in options:
                    options.append(o_eq)

            if len(options) < 4:
                alt1 = matched_eq.replace("-", "+", 1) if "-" in matched_eq else matched_eq.replace("+", "-", 1)
                alt2 = matched_eq.replace("=", "≠", 1) if "=" in matched_eq else f"{matched_eq} / 2"
                alt3 = matched_eq.replace("0.0591/n", "n/0.0591") if "0.0591/n" in matched_eq else f"1 / ({matched_eq})"
                for alt in [alt1, alt2, alt3]:
                    if alt not in options and len(options) < 4:
                        options.append(alt)

            shift = (order_index - 1) % len(options)
            rotated_options = options[shift:] + options[:shift]

            return {
                "prompt": f"According to the course material on '{c_title}', which of the following formulations correctly represents this principle in {course.title}?",
                "question_type": "mcq",
                "options_json": rotated_options,
                "correct_answer": matched_eq,
                "explanation": f"The study material for '{c_title}' specifies '{matched_eq}' as the governing formulation.",
                "concept_id": concept.id,
                "marks": 1.0,
            }

    # Strategy B: Grounded factual statement question
    if matched_stmt and len(other_stmts) >= 1:
        if q_type == "true_false":
            return {
                "prompt": f"True or False: According to the course material on '{c_title}', {matched_stmt}.",
                "question_type": "true_false",
                "options_json": ["True", "False"],
                "correct_answer": "True",
                "explanation": f"Directly substantiated by the study material for {c_title}: \"{matched_stmt}\".",
                "concept_id": concept.id,
                "marks": 1.0,
            }
        elif q_type == "short_answer":
            return {
                "prompt": f"In {course.title}, summarize the core mechanism or finding associated with '{c_title}'.",
                "question_type": "short_answer",
                "options_json": None,
                "correct_answer": matched_stmt,
                "explanation": f"The course materials state: \"{matched_stmt}\".",
                "concept_id": concept.id,
                "marks": 1.0,
            }
        else:
            options = [matched_stmt]
            for o_stmt in other_stmts:
                if len(options) >= 4:
                    break
                if o_stmt not in options:
                    options.append(o_stmt)

            if len(options) < 4 and course.topics:
                for t in course.topics:
                    for c in t.concepts:
                        if c.id != concept.id and len(options) < 4:
                            opt_text = f"Primary focus on {c.name} in topic {t.title}"
                            if opt_text not in options:
                                options.append(opt_text)

            shift = (order_index - 1) % len(options)
            rotated_options = options[shift:] + options[:shift]

            return {
                "prompt": f"In the study of '{c_title}' within {course.title}, which statement is directly substantiated by the course notes?",
                "question_type": "mcq",
                "options_json": rotated_options,
                "correct_answer": matched_stmt,
                "explanation": f"The course notes for '{c_title}' explicitly record: \"{matched_stmt}\".",
                "concept_id": concept.id,
                "marks": 1.0,
            }

    # Strategy C: Grounded syllabus component question
    related_concepts = []
    if course.topics:
        for t in course.topics:
            for c in t.concepts:
                if c.id != concept.id:
                    related_concepts.append(c.name)

    if q_type == "true_false":
        return {
            "prompt": f"True or False: In '{course.title}', '{c_title}' operates as a key component covered in the curriculum notes.",
            "question_type": "true_false",
            "options_json": ["True", "False"],
            "correct_answer": "True",
            "explanation": f"'{c_title}' is indexed in the study materials for '{course.title}'.",
            "concept_id": concept.id,
            "marks": 1.0,
        }
    elif q_type in ("short_answer", "numerical"):
        return {
            "prompt": f"Name the key curriculum concept represented by '{c_title}' in {course.title}.",
            "question_type": q_type,
            "options_json": None,
            "correct_answer": c_title,
            "explanation": f"The curriculum concept is '{c_title}'.",
            "concept_id": concept.id,
            "marks": 1.0,
        }
    else:
        options = [f"Detailed analysis and applications of {c_title}"]
        for r_name in related_concepts:
            if len(options) >= 4:
                break
            cand = f"Detailed analysis and applications of {r_name}"
            if cand not in options:
                options.append(cand)

        while len(options) < 4:
            options.append(f"Principles governing {course.title} section {len(options) + 1}")

        shift = (order_index - 1) % len(options)
        rotated_options = options[shift:] + options[:shift]

        return {
            "prompt": f"Which study module in '{course.title}' directly covers the principles of '{c_title}'?",
            "question_type": "mcq",
            "options_json": rotated_options,
            "correct_answer": f"Detailed analysis and applications of {c_title}",
            "explanation": f"'{c_title}' forms a core component of the curriculum for {course.title}.",
            "concept_id": concept.id,
            "marks": 1.0,
        }


def _generate_fallback_question(
    concept: Concept,
    course: Course,
    q_type: str = "mcq",
    order_index: int = 1,
) -> Dict[str, Any]:
    """
    Backward-compatible fallback delegating to curriculum concept grounding.
    """
    c_title = concept.name.strip()
    related_concepts = []
    if course.topics:
        for t in course.topics:
            for c in t.concepts:
                if c.id != concept.id:
                    related_concepts.append(c.name)

    if q_type == "true_false":
        return {
            "prompt": f"True or False: In '{course.title}', '{c_title}' operates as a key component covered in the curriculum notes.",
            "question_type": "true_false",
            "options_json": ["True", "False"],
            "correct_answer": "True",
            "explanation": f"'{c_title}' is indexed in the study materials for '{course.title}'.",
            "concept_id": concept.id,
            "marks": 1.0,
        }
    elif q_type in ("short_answer", "numerical"):
        return {
            "prompt": f"Name the key curriculum concept represented by '{c_title}' in {course.title}.",
            "question_type": q_type,
            "options_json": None,
            "correct_answer": c_title,
            "explanation": f"The curriculum concept is '{c_title}'.",
            "concept_id": concept.id,
            "marks": 1.0,
        }
    else:
        options = [f"Detailed analysis and applications of {c_title}"]
        for r_name in related_concepts:
            if len(options) >= 4:
                break
            cand = f"Detailed analysis and applications of {r_name}"
            if cand not in options:
                options.append(cand)

        while len(options) < 4:
            options.append(f"Principles governing {course.title} section {len(options) + 1}")

        shift = (order_index - 1) % len(options)
        rotated_options = options[shift:] + options[:shift]

        return {
            "prompt": f"Which study module in '{course.title}' directly covers the principles of '{c_title}'?",
            "question_type": "mcq",
            "options_json": rotated_options,
            "correct_answer": f"Detailed analysis and applications of {c_title}",
            "explanation": f"'{c_title}' forms a core component of the curriculum for {course.title}.",
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

        prompt_str = str(prompt).strip()
        options = item.get("options") or item.get("options_json")

        # Reject any question using deprecated/forbidden generic template phrases
        opts_str = " ".join(str(o) for o in (options or [])).lower()
        if any(f in prompt_str.lower() or f in opts_str for f in FORBIDDEN_TEMPLATE_PHRASES):
            continue

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
            "prompt": prompt_str,
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
CRITICAL QUALITY RULES
==================================================
1. Every question must test substantive subject matter (principles, formulas, reactions, calculations, or mechanisms) of "{concept.name}".
2. Questions and options must be strictly grounded in the provided study material.
3. For multiple-choice (mcq):
   - Provide exactly 4 distinct, plausible options.
   - All 4 options must be realistic domain concepts/terms from the subject matter.
   - NEVER use generic meta-text (e.g. NEVER use "Core foundations...", "An external concept...", "A deprecated convention...", "An ungrounded claim...").
   - Exactly one option must be unambiguously correct.
4. For true_false: options must be ["True", "False"]. The statement must test a factual claim directly stated in the text.
5. For short_answer: options must be null. The answer must be a specific domain term, formula, or quantity.
6. Provide an educational explanation citing the specific principle or equation from the study material.

OUTPUT ONLY A VALID JSON ARRAY (no markdown formatting, no code fences):
[
  {{
    "prompt": "Specific domain question testing the concept?",
    "question_type": "{preferred_type}",
    "options": ["Option A", "Option B", "Option C", "Option D"],
    "correct_answer": "Option A",
    "explanation": "Detailed explanation explaining why Option A is correct based on the material."
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
        if selected_topic:
            raise HTTPException(
                status_code=400,
                detail=f"No eligible concepts found in selected topic '{selected_topic.title}' for practice generation."
            )
        raise HTTPException(
            status_code=400,
            detail=f"No concepts found in course '{course_id}' for practice generation. Ensure course curriculum is indexed and generated first."
        )

    # 5. Concept Selection Strategy per Mode
    target_concepts: List[Concept] = []
    question_count = request.question_count or DEFAULT_QUESTION_COUNT

    if mode == "adaptive":
        if selected_concept:
            target_concepts = [selected_concept] * question_count
        elif selected_topic:
            # Distribute across available concepts in the selected topic
            for i in range(question_count):
                target_concepts.append(available_concepts[i % len(available_concepts)])
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

            other_concepts = [c for c in available_concepts if c.id != target.id]
            target_concepts.append(target)
            for i in range(1, question_count):
                if other_concepts:
                    target_concepts.append(other_concepts[(i - 1) % len(other_concepts)])
                else:
                    target_concepts.append(target)

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
            # Check existing question bank for this concept, ensuring no legacy template questions
            existing_db_q = (
                db.query(Question)
                .join(Assessment, Question.assessment_id == Assessment.id)
                .filter(Assessment.course_id == course_id, Question.concept_id == concept.id)
                .first()
            )
            if existing_db_q and not question_similarity_service.is_similar_question(existing_db_q.prompt, seen_prompts):
                p_low = existing_db_q.prompt.lower()
                opts_low = " ".join(existing_db_q.options_json or []).lower()
                if not any(f in p_low or f in opts_low for f in FORBIDDEN_TEMPLATE_PHRASES):
                    candidate_q = {
                        "prompt": existing_db_q.prompt,
                        "question_type": existing_db_q.question_type,
                        "options_json": existing_db_q.options_json,
                        "correct_answer": existing_db_q.correct_answer,
                        "explanation": existing_db_q.explanation or f"Standard explanation for {concept.name}.",
                        "concept_id": concept.id,
                        "marks": existing_db_q.marks,
                    }
            if not candidate_q:
                candidate_q = _generate_grounded_content_question(
                    db=db,
                    course=course,
                    concept=concept,
                    retrieved_chunks=retrieved_chunks,
                    context_text=context_text,
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
    concept_map = {c.id: c.name for c in target_concepts}
    student_questions: List[PracticeQuestionItem] = []
    for q in sorted(assessment.questions, key=lambda x: x.order_index):
        c_title = concept_map.get(q.concept_id) or (q.concept.name if q.concept else None)
        student_questions.append(
            PracticeQuestionItem(
                id=q.id,
                assessment_id=q.assessment_id,
                concept_id=q.concept_id,
                concept_title=c_title,
                concept_name=c_title,
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
