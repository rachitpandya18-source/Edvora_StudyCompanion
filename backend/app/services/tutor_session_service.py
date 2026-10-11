"""
Tutor Session & Multi-Turn Conversational Learning Service for Edvora.

Manages persistent TutorThreads and TutorMessages scoped to a Course and Student.
Reuses existing B2 retrieval (search_course_content) and B4 grounding/refusal
evaluations with bounded recent conversation windows.
"""

import logging
from typing import Optional, List, Dict, Any, Callable
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.course import Course
from app.models.source import Source
from app.models.content_unit import ContentUnit
from app.models.tutor_session import TutorThread, TutorMessage
from app.schemas.tutor import TutorStatus, TutorCitation
from app.schemas.tutor_session import (
    TutorThreadSummary,
    TutorThreadDetail,
    TutorMessageResponse,
)
from app.services.retrieval_service import search_course_content
from app.services import llm_service
from app.services.course_tutor_service import (
    CourseNotFoundError,
    SourceNotFoundError,
    SourceCourseMismatchError,
    TutorProviderError,
    NEGATIVE_GROUNDING_PHRASES,
    VERY_LOW_RELEVANCE_THRESHOLD,
    MARGINAL_RELEVANCE_THRESHOLD,
)

logger = logging.getLogger(__name__)

# Max previous message turns to include in conversational prompt
CONVERSATIONAL_WINDOW_LIMIT = 6


def verify_course_exists(db: Session, course_id: str) -> Course:
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Course '{course_id}' not found.",
        )
    return course


def verify_thread_access(
    db: Session,
    course_id: str,
    thread_id: str,
    student_id: str = "default_student",
) -> TutorThread:
    verify_course_exists(db, course_id)
    thread = db.query(TutorThread).filter(TutorThread.id == thread_id).first()
    if not thread:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tutor thread '{thread_id}' not found.",
        )
    if thread.course_id != course_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tutor thread '{thread_id}' does not belong to course '{course_id}'.",
        )
    if thread.student_id != student_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tutor thread '{thread_id}' not found for student '{student_id}'.",
        )
    return thread


def derive_thread_title(first_prompt: Optional[str] = None) -> str:
    """
    Derive a deterministic title snippet (~40 characters) without calling LLM.
    """
    if not first_prompt or not first_prompt.strip():
        return "Study Session"
    clean = first_prompt.strip().replace("\n", " ")
    if len(clean) <= 40:
        return clean
    return clean[:40].rstrip() + "..."


def create_tutor_thread(
    db: Session,
    course_id: str,
    student_id: str = "default_student",
    title: Optional[str] = None,
) -> TutorThreadSummary:
    verify_course_exists(db, course_id)
    effective_title = (title.strip() if title and title.strip() else derive_thread_title(None))

    thread = TutorThread(
        course_id=course_id,
        student_id=student_id,
        title=effective_title,
    )
    db.add(thread)
    db.commit()
    db.refresh(thread)

    return TutorThreadSummary(
        id=thread.id,
        course_id=thread.course_id,
        student_id=thread.student_id,
        title=thread.title,
        message_count=0,
        created_at=thread.created_at,
        updated_at=thread.updated_at,
    )


def list_tutor_threads(
    db: Session,
    course_id: str,
    student_id: str = "default_student",
) -> List[TutorThreadSummary]:
    verify_course_exists(db, course_id)
    threads = (
        db.query(TutorThread)
        .filter(
            TutorThread.course_id == course_id,
            TutorThread.student_id == student_id,
        )
        .order_by(TutorThread.updated_at.desc(), TutorThread.created_at.desc())
        .all()
    )

    results = []
    for t in threads:
        results.append(
            TutorThreadSummary(
                id=t.id,
                course_id=t.course_id,
                student_id=t.student_id,
                title=t.title,
                message_count=len(t.messages),
                created_at=t.created_at,
                updated_at=t.updated_at,
            )
        )
    return results


def get_tutor_thread(
    db: Session,
    course_id: str,
    thread_id: str,
    student_id: str = "default_student",
) -> TutorThreadDetail:
    thread = verify_thread_access(db, course_id, thread_id, student_id)

    message_responses = []
    for m in thread.messages:
        citations = []
        if m.citations_json:
            for c_data in m.citations_json:
                citations.append(TutorCitation(**c_data))
        message_responses.append(
            TutorMessageResponse(
                id=m.id,
                thread_id=m.thread_id,
                role=m.role,
                content=m.content,
                status=m.status,
                citations=citations,
                created_at=m.created_at,
            )
        )

    return TutorThreadDetail(
        id=thread.id,
        course_id=thread.course_id,
        student_id=thread.student_id,
        title=thread.title,
        created_at=thread.created_at,
        updated_at=thread.updated_at,
        messages=message_responses,
    )


def delete_tutor_thread(
    db: Session,
    course_id: str,
    thread_id: str,
    student_id: str = "default_student",
) -> None:
    thread = verify_thread_access(db, course_id, thread_id, student_id)
    db.delete(thread)
    db.commit()


def build_conversational_grounded_prompt(
    recent_history: List[TutorMessage],
    current_question: str,
    evidence_chunks: List[Dict[str, Any]],
) -> str:
    """
    Constructs a multi-turn grounded prompt enforcing:
    1. Study materials as the sole ground truth.
    2. Conversational context from recent turns to resolve follow-up references.
    3. Strict anti-hallucination refusal contract.
    """
    # 1. Format study material evidence
    evidence_parts = []
    for idx, r in enumerate(evidence_chunks, start=1):
        src = r.get("source", {})
        filename = src.get("filename", "unknown")
        page = src.get("page")
        page_str = f"Page: {page}" if page is not None else "Page: N/A"
        evidence_parts.append(
            f"SOURCE {idx}:\n"
            f"File: {filename}\n"
            f"{page_str}\n\n"
            f"CONTENT:\n"
            f"{r.get('text', '').strip()}\n"
        )
    evidence_context = "\n---\n".join(evidence_parts) if evidence_parts else "No evidence found."

    # 2. Format recent conversation turns
    history_parts = []
    for m in recent_history:
        prefix = "Student" if m.role == "user" else "Tutor"
        history_parts.append(f"{prefix}: {m.content.strip()}")
    history_context = "\n".join(history_parts) if history_parts else "No previous messages."

    return f"""You are an AI study tutor for the student's course.

Answer the student's question using ONLY the provided study material below.
You may use the conversation history ONLY to understand what concepts or pronouns the student is referring to (e.g., "explain step 2", "why is that?").
However, any factual statements or explanations in your answer MUST be substantiated by the study material.
If the answer is not present in the material or cannot be directly substantiated by it, clearly say:
"I could not find this information in the provided course material."

Do not invent facts.
Do not use outside knowledge.
Do not fabricate citations or page numbers.
Keep the explanation clear, accurate, and student-friendly.

STUDY MATERIAL:
{evidence_context}

RECENT CONVERSATION HISTORY:
{history_context}

STUDENT QUESTION:
{current_question}

ANSWER:
"""


def build_contextual_retrieval_query(
    current_question: str,
    recent_history: List[TutorMessage],
) -> str:
    """
    Augments the current question for semantic search when follow-ups contain
    deictic or coreferential terms (e.g. 'it', 'step 2', 'that formula', 'why is that').
    """
    clean_q = current_question.strip()
    if not recent_history:
        return clean_q

    # Check for short follow-up or coreference indicators
    coreference_indicators = [
        "step ", "it", "that", "this", "these", "those",
        "why", "how so", "elaborate", "explain again",
        "second", "first", "third", "formula", "example",
    ]
    lower_q = clean_q.lower()
    needs_context = (
        len(clean_q.split()) <= 6
        or any(ind in lower_q for ind in coreference_indicators)
    )

    if not needs_context:
        return clean_q

    # Pick the most recent user question or assistant statement to augment
    context_snippets = []
    for m in reversed(recent_history):
        if m.role == "user":
            context_snippets.append(m.content.strip())
            break
        elif m.role == "assistant":
            # Extract first sentence or snippet of previous assistant reply
            first_line = m.content.strip().split(".")[0]
            if first_line:
                context_snippets.append(first_line)
            break

    if context_snippets:
        combined = f"{' '.join(context_snippets)} {clean_q}"
        return combined[:500]

    return clean_q


def post_thread_message(
    db: Session,
    course_id: str,
    thread_id: str,
    question: str,
    student_id: str = "default_student",
    source_id: Optional[str] = None,
    top_k: int = 3,
    llm_generator: Optional[Callable[[str], str]] = None,
) -> TutorMessageResponse:
    """
    Submits a user message to a thread, performs contextual course retrieval,
    evaluates grounded tutor response, and persists both user and assistant turns.
    """
    clean_question = question.strip() if question else ""
    if not clean_question:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question cannot be empty.",
        )

    # 1. Verify thread access & ownership
    thread = verify_thread_access(db, course_id, thread_id, student_id)

    # 2. Auto-update thread title if default/empty
    if thread.title == "Study Session" and len(thread.messages) == 0:
        thread.title = derive_thread_title(clean_question)

    # 3. Verify source filter if provided
    if source_id:
        src = db.query(Source).filter(Source.id == source_id).first()
        if not src:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Source '{source_id}' not found.",
            )
        if src.course_id != course_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Source '{source_id}' does not belong to course '{course_id}'.",
            )

    # 4. Fetch recent conversation window (last 4-6 messages)
    recent_history: List[TutorMessage] = (
        db.query(TutorMessage)
        .filter(TutorMessage.thread_id == thread_id)
        .order_by(TutorMessage.created_at.desc())
        .limit(CONVERSATIONAL_WINDOW_LIMIT)
        .all()
    )
    # Reverse to chronological order
    recent_history = list(reversed(recent_history))

    # 5. Persist user message immediately
    user_msg = TutorMessage(
        thread_id=thread.id,
        role="user",
        content=clean_question,
        status="answered",
    )
    db.add(user_msg)
    db.flush()

    # 6. Check if course has any uploaded/indexed materials
    unit_query = db.query(ContentUnit).filter(
        ContentUnit.course_id == course_id,
        ContentUnit.embedding.isnot(None),
    )
    if source_id:
        unit_query = unit_query.filter(ContentUnit.source_id == source_id)

    total_units = unit_query.count()
    if total_units == 0:
        no_material_msg = TutorMessage(
            thread_id=thread.id,
            role="assistant",
            content="This course does not have any uploaded or indexed study material yet. Please upload course materials to begin asking questions.",
            status=TutorStatus.NO_COURSE_MATERIAL.value,
            citations_json=[],
        )
        db.add(no_material_msg)
        db.commit()
        db.refresh(no_material_msg)
        return TutorMessageResponse(
            id=no_material_msg.id,
            thread_id=no_material_msg.thread_id,
            role=no_material_msg.role,
            content=no_material_msg.content,
            status=no_material_msg.status,
            citations=[],
            created_at=no_material_msg.created_at,
        )

    # 7. Build contextual query and execute B2 retrieval
    contextual_query = build_contextual_retrieval_query(clean_question, recent_history)
    results = search_course_content(
        db=db,
        course_id=course_id,
        query=contextual_query,
        top_k=top_k,
        source_id=source_id,
    )

    # 8. Handle empty retrieval or extremely low relevance
    if not results or results[0].get("score", 0.0) < VERY_LOW_RELEVANCE_THRESHOLD:
        assistant_msg = TutorMessage(
            thread_id=thread.id,
            role="assistant",
            content="This question is outside the scope of the available course material.",
            status=TutorStatus.OUT_OF_SCOPE.value,
            citations_json=[],
        )
        db.add(assistant_msg)
        db.commit()
        db.refresh(assistant_msg)
        return TutorMessageResponse(
            id=assistant_msg.id,
            thread_id=assistant_msg.thread_id,
            role=assistant_msg.role,
            content=assistant_msg.content,
            status=assistant_msg.status,
            citations=[],
            created_at=assistant_msg.created_at,
        )

    top_score = results[0].get("score", 0.0)

    # 9. Generate grounded response with multi-turn context
    generator = llm_generator or llm_service.generate_response
    prompt = build_conversational_grounded_prompt(recent_history, clean_question, results)

    try:
        raw_answer = generator(prompt)
    except Exception as exc:
        logger.error(f"[TUTOR_SESSION] LLM generator failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"AI Tutor service is temporarily unavailable. Please try again later. ({exc})",
        )

    answer_text = raw_answer.strip() if raw_answer else ""

    # 10. Check for refusal / negative grounding phrases (Reusing B4 logic)
    lower_answer = answer_text.lower()
    is_refusal = any(phrase in lower_answer for phrase in NEGATIVE_GROUNDING_PHRASES)

    if is_refusal:
        resp_status = (
            TutorStatus.OUT_OF_SCOPE.value
            if top_score < MARGINAL_RELEVANCE_THRESHOLD
            else TutorStatus.INSUFFICIENT_EVIDENCE.value
        )
        assistant_msg = TutorMessage(
            thread_id=thread.id,
            role="assistant",
            content=answer_text,
            status=resp_status,
            citations_json=[],
        )
        db.add(assistant_msg)
        db.commit()
        db.refresh(assistant_msg)
        return TutorMessageResponse(
            id=assistant_msg.id,
            thread_id=assistant_msg.thread_id,
            role=assistant_msg.role,
            content=assistant_msg.content,
            status=assistant_msg.status,
            citations=[],
            created_at=assistant_msg.created_at,
        )

    # 11. Supported answer: assemble authentic citations
    citations_list: List[Dict[str, Any]] = []
    citations_models: List[TutorCitation] = []
    for r in results:
        src = r.get("source", {})
        cit = TutorCitation(
            content_unit_id=r.get("id"),
            source_id=src.get("source_id"),
            filename=src.get("filename", ""),
            page=src.get("page"),
            score=r.get("score"),
            content_type=src.get("type", "pdf"),
        )
        citations_models.append(cit)
        citations_list.append(cit.model_dump())

    assistant_msg = TutorMessage(
        thread_id=thread.id,
        role="assistant",
        content=answer_text,
        status=TutorStatus.ANSWERED.value,
        citations_json=citations_list,
    )
    db.add(assistant_msg)
    db.commit()
    db.refresh(assistant_msg)

    return TutorMessageResponse(
        id=assistant_msg.id,
        thread_id=assistant_msg.thread_id,
        role=assistant_msg.role,
        content=assistant_msg.content,
        status=assistant_msg.status,
        citations=citations_models,
        created_at=assistant_msg.created_at,
    )

