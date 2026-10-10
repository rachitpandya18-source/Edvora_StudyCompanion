"""
Course-Grounded Tutor service for Edvora.

Provides course-scoped, multi-source RAG question answering with strict
evidence grounding, trustworthy citations, and a deterministic outside-material
response contract.
"""

from typing import Optional, List, Dict, Any, Callable
from sqlalchemy.orm import Session

from app.models.course import Course
from app.models.source import Source
from app.models.content_unit import ContentUnit
from app.schemas.tutor import TutorStatus, TutorCitation
from app.services.retrieval_service import search_course_content
from app.services import llm_service


# =====================================================================
# Domain Exceptions
# =====================================================================

class CourseNotFoundError(ValueError):
    """Raised when the specified course does not exist."""
    pass


class SourceNotFoundError(ValueError):
    """Raised when the specified source does not exist."""
    pass


class SourceCourseMismatchError(ValueError):
    """Raised when the requested source does not belong to the target course."""
    pass


class TutorProviderError(RuntimeError):
    """Raised when the upstream LLM generation service fails."""
    pass


# =====================================================================
# Grounding Patterns & Prompts
# =====================================================================

NEGATIVE_GROUNDING_PHRASES = [
    "could not find this information",
    "cannot find this information",
    "could not find any information",
    "not found in the provided",
    "not present in the provided",
    "not mentioned in the provided",
    "not contained in the provided",
    "not covered in the provided",
    "does not mention",
    "does not provide",
    "insufficient information",
    "insufficient evidence",
    "outside the provided",
    "outside the course material",
    "outside the scope",
]

# Relevance score thresholds for all-MiniLM-L6-v2 cosine similarity
VERY_LOW_RELEVANCE_THRESHOLD = 0.20
MARGINAL_RELEVANCE_THRESHOLD = 0.35


def build_grounded_prompt(question: str, results: List[Dict[str, Any]]) -> str:
    """Build a multi-source context prompt enforcing strict grounding."""
    context_parts = []
    for idx, r in enumerate(results, start=1):
        src = r.get("source", {})
        filename = src.get("filename", "unknown")
        page = src.get("page")
        page_str = f"Page: {page}" if page is not None else "Page: N/A"
        context_parts.append(
            f"SOURCE {idx}:\n"
            f"File: {filename}\n"
            f"{page_str}\n\n"
            f"CONTENT:\n"
            f"{r.get('text', '').strip()}\n"
        )

    context = "\n---\n".join(context_parts)

    return f"""You are an AI study tutor for the student's course.

Answer the student's question using ONLY the provided study material below.
If the answer is not present in the material or cannot be directly substantiated by it, clearly say:
"I could not find this information in the provided course material."

Do not invent facts.
Do not use outside knowledge.
Do not fabricate citations or page numbers.
Keep the explanation clear, accurate, and student-friendly.

STUDY MATERIAL:
{context}

STUDENT QUESTION:
{question}

ANSWER:
"""


# =====================================================================
# Main Course Tutor Answering Service
# =====================================================================

def answer_course_question(
    db: Session,
    course_id: str,
    question: str,
    source_id: Optional[str] = None,
    top_k: int = 3,
    llm_generator: Optional[Callable[[str], str]] = None,
) -> Dict[str, Any]:
    """
    Answer a question grounded in the course's persistent content units.

    Contract guarantees:
    1. Validates course existence (raises CourseNotFoundError if missing).
    2. Validates source ownership (raises SourceCourseMismatchError if mismatch).
    3. Handles empty courses (returns NO_COURSE_MATERIAL status, empty citations).
    4. Enforces course isolation throughout retrieval.
    5. Detects unsupported or out-of-scope questions (OUT_OF_SCOPE / INSUFFICIENT_EVIDENCE, empty citations).
    6. Returns authentic citation metadata tied strictly to chunks used as evidence.
    7. Propagates provider failures safely via TutorProviderError.
    """
    clean_question = question.strip() if question else ""
    if not clean_question:
        raise ValueError("Question cannot be empty.")

    # 1. Verify course exists
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise CourseNotFoundError(f"Course '{course_id}' not found.")

    # 2. Verify source filter if provided
    if source_id:
        src = db.query(Source).filter(Source.id == source_id).first()
        if not src:
            raise SourceNotFoundError(f"Source '{source_id}' not found.")
        if src.course_id != course_id:
            raise SourceCourseMismatchError(
                f"Source '{source_id}' does not belong to course '{course_id}'."
            )

    # 3. Check if course has any uploaded and indexed materials
    unit_query = db.query(ContentUnit).filter(
        ContentUnit.course_id == course_id,
        ContentUnit.embedding.isnot(None)
    )
    if source_id:
        unit_query = unit_query.filter(ContentUnit.source_id == source_id)

    total_units = unit_query.count()
    if total_units == 0:
        return {
            "answer": "This course does not have any uploaded or indexed study material yet. Please upload course materials to begin asking questions.",
            "status": TutorStatus.NO_COURSE_MATERIAL.value,
            "citations": [],
            "course_id": course_id,
        }

    # 4. Multi-source RAG Retrieval via B2 retrieval service
    results = search_course_content(
        db=db,
        course_id=course_id,
        query=clean_question,
        top_k=top_k,
        source_id=source_id,
    )

    # 5. Handle empty retrieval
    if not results:
        return {
            "answer": "This question is outside the scope of the available course material.",
            "status": TutorStatus.OUT_OF_SCOPE.value,
            "citations": [],
            "course_id": course_id,
        }

    # 6. Check for extremely low similarity (completely irrelevant question)
    top_score = results[0].get("score", 0.0)
    if top_score < VERY_LOW_RELEVANCE_THRESHOLD:
        return {
            "answer": "This question is outside the scope of the available course material.",
            "status": TutorStatus.OUT_OF_SCOPE.value,
            "citations": [],
            "course_id": course_id,
        }

    # 7. Generate answer using LLM
    generator = llm_generator or llm_service.generate_response
    prompt = build_grounded_prompt(clean_question, results)

    try:
        raw_answer = generator(prompt)
    except Exception as exc:
        raise TutorProviderError(f"AI generation provider failed: {exc}") from exc

    answer_text = raw_answer.strip() if raw_answer else ""

    # 8. Check for refusal / negative grounding phrases
    lower_answer = answer_text.lower()
    is_refusal = any(phrase in lower_answer for phrase in NEGATIVE_GROUNDING_PHRASES)

    if is_refusal:
        # Determine whether out of scope or insufficient evidence
        status = (
            TutorStatus.OUT_OF_SCOPE.value
            if top_score < MARGINAL_RELEVANCE_THRESHOLD
            else TutorStatus.INSUFFICIENT_EVIDENCE.value
        )
        return {
            "answer": answer_text,
            "status": status,
            "citations": [],
            "course_id": course_id,
        }

    # 9. Supported answer: return citations with actual provenance
    citations: List[TutorCitation] = []
    for r in results:
        src = r.get("source", {})
        citations.append(
            TutorCitation(
                content_unit_id=r.get("id"),
                source_id=src.get("source_id"),
                filename=src.get("filename", ""),
                page=src.get("page"),
                score=r.get("score"),
                content_type=src.get("type", "pdf"),
            )
        )

    return {
        "answer": answer_text,
        "status": TutorStatus.ANSWERED.value,
        "citations": citations,
        "course_id": course_id,
    }

