import re
import string
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple
from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.course import Course
from app.models.assessment import Assessment, Question, AssessmentAttempt, AttemptAnswer
from app.schemas.assessment import (
    AssessmentCreate,
    AssessmentSummary,
    AnswerDraftItem,
)


# ============================================================================
# Deterministic Grading Engine
# ============================================================================

def _clean_text(text: str) -> str:
    """Normalize text by trimming, lowercasing, and stripping outer punctuation."""
    if not text:
        return ""
    text = text.strip().lower()
    # Strip common punctuation like trailing dots, commas, exclamation marks
    text = text.strip(string.punctuation + " \t\r\n")
    # Collapse multiple whitespaces
    text = re.sub(r"\s+", " ", text)
    return text


def evaluate_single_answer(
    question_type: str,
    correct_answer: str,
    student_answer: Optional[str],
    marks: float,
    tolerance: Optional[float] = None,
    options_json: Optional[List[str]] = None,
    explanation: Optional[str] = None,
) -> Tuple[bool, float, str]:
    """
    Deterministically evaluate a single question answer.

    Returns:
        (is_correct: bool, marks_awarded: float, feedback: str)
    """
    if student_answer is None or str(student_answer).strip() == "":
        return False, 0.0, "No answer provided."

    s_raw = str(student_answer).strip()
    c_raw = str(correct_answer).strip()
    s_clean = _clean_text(s_raw)
    c_clean = _clean_text(c_raw)

    qtype = question_type.strip().lower()

    # 1. Multiple Choice Questions (MCQ)
    if qtype == "mcq":
        # Direct string equality (case and whitespace normalized)
        if s_clean == c_clean:
            return True, marks, "Correct choice."

        # Check against options list (e.g., student answers "A" or option text)
        if options_json and isinstance(options_json, list):
            letter_map = {chr(ord('a') + i): i for i in range(min(26, len(options_json)))}
            digit_map = {str(i): i for i in range(len(options_json))}

            # Find matching option index for student answer
            student_idx = None
            if s_clean in letter_map:
                student_idx = letter_map[s_clean]
            elif s_clean in digit_map:
                student_idx = digit_map[s_clean]
            else:
                for idx, opt in enumerate(options_json):
                    if _clean_text(opt) == s_clean or _clean_text(opt).startswith(f"{s_clean})"):
                        student_idx = idx
                        break

            # Find matching option index for correct answer
            correct_idx = None
            if c_clean in letter_map:
                correct_idx = letter_map[c_clean]
            elif c_clean in digit_map:
                correct_idx = digit_map[c_clean]
            else:
                for idx, opt in enumerate(options_json):
                    if _clean_text(opt) == c_clean or _clean_text(opt).startswith(f"{c_clean})"):
                        correct_idx = idx
                        break

            if student_idx is not None and correct_idx is not None and student_idx == correct_idx:
                return True, marks, "Correct choice."

        return False, 0.0, "Incorrect choice."

    # 2. True / False Questions
    elif qtype == "true_false":
        true_tokens = {"true", "t", "1", "yes", "y"}
        false_tokens = {"false", "f", "0", "no", "n"}

        s_bool = None
        if s_clean in true_tokens:
            s_bool = True
        elif s_clean in false_tokens:
            s_bool = False

        c_bool = None
        if c_clean in true_tokens:
            c_bool = True
        elif c_clean in false_tokens:
            c_bool = False

        if s_bool is None:
            return False, 0.0, f"Invalid True/False response '{s_raw}'."

        if s_bool == c_bool:
            return True, marks, "Correct answer."
        return False, 0.0, "Incorrect choice."

    # 3. Numerical Questions
    elif qtype == "numerical":
        try:
            student_val = float(s_raw.replace(",", ""))
        except ValueError:
            return False, 0.0, f"Invalid numerical value: '{s_raw}'."

        try:
            correct_val = float(c_raw.replace(",", ""))
        except ValueError:
            # Fallback if correct answer string cannot be converted
            return False, 0.0, "System error: correct answer is not a valid float."

        tol = tolerance if (tolerance is not None and tolerance >= 0) else 1e-4

        if abs(student_val - correct_val) <= (tol + 1e-9):
            return True, marks, f"Correct numerical value (within tolerance ±{tol})."
        return False, 0.0, f"Value {student_val} does not match expected {correct_val} (within tolerance ±{tol})."

    # 4. Short Answer Questions (Deterministic MVP Criteria)
    elif qtype == "short_answer":
        # Supports multiple acceptable answers separated by ';' or '|'
        delimiters = [";", "|"]
        correct_candidates = [c_clean]
        for delim in delimiters:
            if delim in c_raw:
                correct_candidates = [_clean_text(cand) for cand in c_raw.split(delim)]
                break

        # Check exact equality against any candidate
        for cand in correct_candidates:
            if cand and s_clean == cand:
                return True, marks, "Correct short answer."

        # Check semantic phrase containment: if key phrase is present in student's response
        for cand in correct_candidates:
            if len(cand) >= 3 and cand in s_clean:
                return True, marks, "Correct short answer (contains key concept)."

        return False, 0.0, "Answer does not match expected criteria."

    else:
        # Fallback for unrecognized question types
        if s_clean == c_clean:
            return True, marks, "Correct answer."
        return False, 0.0, "Incorrect answer."


# ============================================================================
# Assessment Service CRUD & Verification
# ============================================================================

def get_verified_course(db: Session, course_id: str) -> Course:
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(
            status_code=404,
            detail=f"Course '{course_id}' not found."
        )
    return course


def create_assessment(db: Session, course_id: str, data: AssessmentCreate) -> Assessment:
    get_verified_course(db, course_id)

    total_marks = sum(q.marks for q in data.questions)

    assessment = Assessment(
        course_id=course_id,
        title=data.title,
        description=data.description,
        assessment_type=data.assessment_type,
        time_limit_minutes=data.time_limit_minutes,
        total_marks=total_marks,
    )
    db.add(assessment)
    db.flush()

    for idx, q_data in enumerate(data.questions):
        question = Question(
            assessment_id=assessment.id,
            question_type=q_data.question_type,
            prompt=q_data.prompt,
            order_index=q_data.order_index if q_data.order_index is not None else idx,
            marks=q_data.marks,
            options_json=q_data.options_json,
            correct_answer=q_data.correct_answer,
            tolerance=q_data.tolerance,
            explanation=q_data.explanation,
        )
        db.add(question)

    db.commit()
    db.refresh(assessment)
    return assessment


def list_assessments(db: Session, course_id: str) -> List[Dict[str, Any]]:
    get_verified_course(db, course_id)

    assessments = (
        db.query(Assessment)
        .filter(Assessment.course_id == course_id)
        .order_by(desc(Assessment.created_at))
        .all()
    )

    summaries = []
    for a in assessments:
        summaries.append({
            "id": a.id,
            "course_id": a.course_id,
            "title": a.title,
            "description": a.description,
            "assessment_type": a.assessment_type,
            "time_limit_minutes": a.time_limit_minutes,
            "total_marks": a.total_marks,
            "question_count": len(a.questions),
            "created_at": a.created_at,
            "updated_at": a.updated_at,
        })
    return summaries


def get_assessment(db: Session, course_id: str, assessment_id: str) -> Assessment:
    get_verified_course(db, course_id)

    assessment = (
        db.query(Assessment)
        .filter(Assessment.id == assessment_id, Assessment.course_id == course_id)
        .first()
    )
    if not assessment:
        raise HTTPException(
            status_code=404,
            detail=f"Assessment '{assessment_id}' not found in course '{course_id}'."
        )
    return assessment


def delete_assessment(db: Session, course_id: str, assessment_id: str) -> None:
    assessment = get_assessment(db, course_id, assessment_id)
    db.delete(assessment)
    db.commit()


# ============================================================================
# Assessment Attempt & Evaluation Lifecycle
# ============================================================================

def start_attempt(
    db: Session,
    course_id: str,
    assessment_id: str,
    student_id: str = "default_student",
) -> AssessmentAttempt:
    assessment = get_assessment(db, course_id, assessment_id)

    attempt = AssessmentAttempt(
        assessment_id=assessment.id,
        student_id=student_id or "default_student",
        status="in_progress",
    )
    db.add(attempt)
    db.flush()

    # Pre-populate empty draft answers for all questions in order
    for question in assessment.questions:
        ans = AttemptAnswer(
            attempt_id=attempt.id,
            question_id=question.id,
            student_answer=None,
            is_correct=None,
            marks_awarded=0.0,
            feedback=None,
        )
        db.add(ans)

    db.commit()
    db.refresh(attempt)
    return attempt


def get_attempt(
    db: Session,
    course_id: str,
    assessment_id: str,
    attempt_id: str,
) -> AssessmentAttempt:
    # Verify course and assessment exist
    get_assessment(db, course_id, assessment_id)

    attempt = (
        db.query(AssessmentAttempt)
        .filter(
            AssessmentAttempt.id == attempt_id,
            AssessmentAttempt.assessment_id == assessment_id,
        )
        .first()
    )
    if not attempt:
        raise HTTPException(
            status_code=404,
            detail=f"Attempt '{attempt_id}' not found for assessment '{assessment_id}'."
        )
    return attempt


def list_attempts(
    db: Session,
    course_id: str,
    assessment_id: str,
    student_id: Optional[str] = None,
) -> List[AssessmentAttempt]:
    get_assessment(db, course_id, assessment_id)

    query = db.query(AssessmentAttempt).filter(
        AssessmentAttempt.assessment_id == assessment_id
    )
    if student_id:
        query = query.filter(AssessmentAttempt.student_id == student_id)

    return query.order_by(desc(AssessmentAttempt.created_at)).all()


def save_draft_answers(
    db: Session,
    course_id: str,
    assessment_id: str,
    attempt_id: str,
    draft_answers: List[AnswerDraftItem],
) -> AssessmentAttempt:
    attempt = get_attempt(db, course_id, assessment_id, attempt_id)

    if attempt.status != "in_progress":
        raise HTTPException(
            status_code=400,
            detail="Cannot update draft answers: assessment attempt has already been submitted."
        )

    # Valid questions in this assessment
    valid_q_ids = {q.id for q in attempt.assessment.questions}

    # Index existing answer records by question_id
    existing_map = {ans.question_id: ans for ans in attempt.answers}

    for item in draft_answers:
        if item.question_id not in valid_q_ids:
            raise HTTPException(
                status_code=400,
                detail=f"Question '{item.question_id}' does not belong to assessment '{assessment_id}'."
            )

        if item.question_id in existing_map:
            existing_map[item.question_id].student_answer = item.student_answer
        else:
            new_ans = AttemptAnswer(
                attempt_id=attempt.id,
                question_id=item.question_id,
                student_answer=item.student_answer,
                is_correct=None,
                marks_awarded=0.0,
            )
            db.add(new_ans)

    db.commit()
    db.refresh(attempt)
    return attempt


def submit_attempt(
    db: Session,
    course_id: str,
    assessment_id: str,
    attempt_id: str,
    final_answers: Optional[List[AnswerDraftItem]] = None,
) -> AssessmentAttempt:
    attempt = get_attempt(db, course_id, assessment_id, attempt_id)

    # Idempotent re-submission check
    if attempt.status == "submitted":
        return attempt

    # Save any inline answers provided at submission time
    if final_answers:
        valid_q_ids = {q.id for q in attempt.assessment.questions}
        existing_map = {ans.question_id: ans for ans in attempt.answers}

        for item in final_answers:
            if item.question_id not in valid_q_ids:
                raise HTTPException(
                    status_code=400,
                    detail=f"Question '{item.question_id}' does not belong to assessment '{assessment_id}'."
                )
            if item.question_id in existing_map:
                existing_map[item.question_id].student_answer = item.student_answer
            else:
                new_ans = AttemptAnswer(
                    attempt_id=attempt.id,
                    question_id=item.question_id,
                    student_answer=item.student_answer,
                )
                db.add(new_ans)
                existing_map[item.question_id] = new_ans

        db.flush()

    # Re-index answers
    existing_map = {ans.question_id: ans for ans in attempt.answers}

    total_score = 0.0
    total_max = 0.0

    # Evaluate each question
    for question in attempt.assessment.questions:
        total_max += question.marks

        ans = existing_map.get(question.id)
        if not ans:
            ans = AttemptAnswer(
                attempt_id=attempt.id,
                question_id=question.id,
                student_answer=None,
            )
            db.add(ans)
            existing_map[question.id] = ans

        is_corr, marks_awd, feedback = evaluate_single_answer(
            question_type=question.question_type,
            correct_answer=question.correct_answer,
            student_answer=ans.student_answer,
            marks=question.marks,
            tolerance=question.tolerance,
            options_json=question.options_json,
            explanation=question.explanation,
        )

        ans.is_correct = is_corr
        ans.marks_awarded = marks_awd
        ans.feedback = feedback
        total_score += marks_awd

    attempt.score = total_score
    attempt.max_score = total_max
    attempt.percentage = round((total_score / total_max) * 100, 2) if total_max > 0 else 0.0
    attempt.status = "submitted"
    attempt.submitted_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(attempt)
    return attempt


# ============================================================================
# Security-Compliant View Formatting Helpers
# ============================================================================

def format_assessment_for_student(assessment: Assessment) -> Dict[str, Any]:
    """
    Format assessment payload for student view, stripping answer keys,
    tolerances, and explanations before attempt submission.
    """
    questions = []
    for q in sorted(assessment.questions, key=lambda x: x.order_index):
        questions.append({
            "id": q.id,
            "assessment_id": q.assessment_id,
            "question_type": q.question_type,
            "prompt": q.prompt,
            "order_index": q.order_index,
            "marks": q.marks,
            "options_json": q.options_json,
        })

    return {
        "id": assessment.id,
        "course_id": assessment.course_id,
        "title": assessment.title,
        "description": assessment.description,
        "assessment_type": assessment.assessment_type,
        "time_limit_minutes": assessment.time_limit_minutes,
        "total_marks": assessment.total_marks,
        "questions": questions,
        "created_at": assessment.created_at,
        "updated_at": assessment.updated_at,
    }


def format_attempt_view(attempt: AssessmentAttempt) -> Dict[str, Any]:
    """
    Format attempt view.
    If 'in_progress':
        Hides correct_answer, explanation, is_correct, marks_awarded, and feedback.
    If 'submitted':
        Reveals evaluated score, per-question correctness, feedback,
        correct_answer, and explanation.
    """
    is_submitted = (attempt.status == "submitted")

    # Map question details
    q_map = {q.id: q for q in attempt.assessment.questions}

    answers = []
    # Sort answers by question order_index
    sorted_answers = sorted(
        attempt.answers,
        key=lambda a: q_map.get(a.question_id).order_index if q_map.get(a.question_id) else 0
    )

    for ans in sorted_answers:
        q = q_map.get(ans.question_id)
        item: Dict[str, Any] = {
            "id": ans.id,
            "attempt_id": ans.attempt_id,
            "question_id": ans.question_id,
            "student_answer": ans.student_answer,
            "question_prompt": q.prompt if q else None,
            "question_type": q.question_type if q else None,
            "question_marks": q.marks if q else None,
            "options_json": q.options_json if q else None,
        }

        if is_submitted:
            item["is_correct"] = ans.is_correct
            item["marks_awarded"] = ans.marks_awarded
            item["feedback"] = ans.feedback
            item["correct_answer"] = q.correct_answer if q else None
            item["explanation"] = q.explanation if q else None
        else:
            item["is_correct"] = None
            item["marks_awarded"] = 0.0
            item["feedback"] = None
            item["correct_answer"] = None
            item["explanation"] = None

        answers.append(item)

    return {
        "id": attempt.id,
        "assessment_id": attempt.assessment_id,
        "student_id": attempt.student_id,
        "status": attempt.status,
        "score": attempt.score if is_submitted else None,
        "max_score": attempt.max_score if is_submitted else None,
        "percentage": attempt.percentage if is_submitted else None,
        "submitted_at": attempt.submitted_at if is_submitted else None,
        "created_at": attempt.created_at,
        "updated_at": attempt.updated_at,
        "answers": answers,
    }

