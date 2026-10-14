"""
Tutor Session & Multi-Turn Conversational Learning Service for Edvora.

Manages persistent TutorThreads and TutorMessages scoped to a Course and Student.
Reuses existing B2 retrieval (search_course_content) and B4 grounding/refusal
evaluations with bounded recent conversation windows.
"""

import re
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
    synthesize_grounded_tutor_explanation,
)

logger = logging.getLogger(__name__)

# Max previous message turns to include in conversational prompt
CONVERSATIONAL_WINDOW_LIMIT = 6


def verify_course_exists(db: Session, course_id: str, student_id: Optional[str] = None) -> Course:
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Course '{course_id}' not found.",
        )
    if student_id and course.owner_id is not None and course.owner_id != student_id:
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
    verify_course_exists(db, course_id, student_id=student_id)
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
    verify_course_exists(db, course_id, student_id=student_id)
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
    verify_course_exists(db, course_id, student_id=student_id)
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
    1. Direct answer first.
    2. Active step-by-step deduction for application and mathematical word problems.
    3. Conversational context from recent turns only to resolve ambiguous follow-up references.
    4. Strict anti-hallucination refusal contract for out-of-scope queries.
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

Instructions:
1. Answer the student's question directly and clearly. State the final answer or conclusion first.
2. For problem-solving, mathematical, counting, or logical questions (such as Pigeonhole Principle applications, probability, or chemical formulas):
   - Actively solve the problem step-by-step.
   - Ground your method and definitions in the concepts, theorems, and formulas present in the provided study material.
   - Map problem elements to the course concepts (for example, identifying the pigeons and pigeonholes).
   - Do NOT say "I could not find this information" simply because the specific numbers or items (e.g. socks, cards, dice) in the student's problem are an application exercise of the course's principles.
3. For factual and conceptual questions:
   - Provide an accurate, well-structured explanation grounded in the study material.
   - Do NOT introduce unrelated topics (e.g., do not discuss sequences or summations when answering a question on the Pigeonhole Principle or electrochemistry).
4. Refusal contract:
   - If the student's question is completely unrelated to any topic in the course material (e.g., asking about chemistry in a math course), respond with:
     "I could not find this information in the provided course material."
5. Tone:
   - Clear, student-friendly, and educational.

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
    Augments the current question for semantic search only when follow-ups contain
    explicit deictic or coreferential terms (e.g. 'why is that', 'step 2', 'what does it mean').
    Never pollutes standalone queries (like 'what is oxidation' or word problems like the sock drawer problem)
    with prior conversational context.
    """
    clean_q = current_question.strip()
    if not recent_history or not clean_q:
        return clean_q

    lower_q = clean_q.lower()

    stop_words = {
        "what", "is", "the", "how", "does", "why", "are", "explain", "describe",
        "tell", "me", "about", "a", "an", "in", "of", "to", "and", "or", "for", "with",
        "can", "you", "which", "when", "where", "who", "whom", "this", "that", "these", "those",
        "have", "has", "had", "will", "would", "shall", "should", "could"
    }
    content_words = [w for w in re.findall(r"\b[a-zA-Z]{3,}\b", lower_q) if w not in stop_words]

    # Explicit problem statements or rich questions with multiple distinct domain words are standalone
    is_word_problem = bool(re.match(
        r"^(a|an|suppose|consider|if|in|given|assume|how\s+many|what\s+is\s+the\s+minimum|calculate|find)\b",
        lower_q
    ))
    if is_word_problem and len(content_words) >= 4:
        return clean_q

    if len(content_words) >= 6:
        # A rich question with 6+ substantive words is self-contained
        return clean_q

    # Explicit coreference phrases that clearly indicate a follow-up
    deictic_phrases = [
        "why is that", "how so", "elaborate", "explain more", "tell me more",
        "explain again", "step 1", "step 2", "step 3", "first step", "second step",
        "third step", "that formula", "this formula", "an example of that",
        "an example of this", "what about it", "what does that mean", "why does that",
        "how does that", "why did you say", "in this case", "for that", "what does it mean"
    ]
    has_phrase = any(p in lower_q for p in deictic_phrases)

    # Conjunctions vs demonstratives for "that":
    # "that" preceded by verbs like guarantee, assume, show, prove, ensure is a conjunction, not a pronoun
    lower_without_conjunctions = re.sub(
        r"\b(guarantee|guaranteed|ensure|ensures|assume|assumes|show|shows|prove|proves|stated|state|states|know|knows)\s+that\b",
        "",
        lower_q
    )
    has_demonstrative = bool(re.search(r"\b(it|its|this|these|those|former|latter)\b", lower_without_conjunctions))
    if not has_demonstrative and bool(re.search(r"\bthat\b", lower_without_conjunctions)):
        # If "that" is used alone or as demonstrative (e.g. "what is that", "why that", or very short queries)
        if re.search(r"\b(what|why|how|explain|about|with|for|like)\s+that\b", lower_q) or len(content_words) <= 2:
            has_demonstrative = True

    # Standalone subject question check (e.g., "what is oxidation", "define cell potential")
    standalone_subject_match = re.search(
        r"^(what\s+is|what\s+are|define|explain|describe|tell\s+me\s+about)\s+([a-zA-Z0-9_\-\s]{3,})$",
        lower_q
    )
    if standalone_subject_match:
        subject = standalone_subject_match.group(2).strip()
        if not re.fullmatch(r"(it|that|this|these|those|the same|something|anything)", subject):
            return clean_q

    # If it is not a deictic phrase and does not use a demonstrative, keep clean
    if not has_phrase and not has_demonstrative:
        return clean_q

    # Pick the most recent relevant turn to augment
    context_snippets = []
    for m in reversed(recent_history):
        if m.role == "user":
            context_snippets.append(m.content.strip())
            break
        elif m.role == "assistant":
            first_line = m.content.strip().split(".")[0]
            if first_line and not any(p in first_line.lower() for p in ["outside the scope", "could not find"]):
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

    answer_text = None
    try:
        raw_answer = generator(prompt)
        answer_text = raw_answer.strip() if raw_answer else ""
    except Exception as exc:
        if llm_generator is not None:
            logger.error(f"[TUTOR_SESSION] Custom LLM generator failed: {exc}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"AI Tutor service is temporarily unavailable. Please try again later. ({exc})",
            )
        # Default LLM generator failed (e.g. key unconfigured, quota exceeded, or network)
        logger.info(f"[TUTOR_SESSION] Using grounded pedagogical synthesizer for tutor answer.")
        answer_text = synthesize_grounded_tutor_explanation(clean_question, results)

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

    # 11. Supported answer: assemble authentic, deduplicated citations
    citations_list: List[Dict[str, Any]] = []
    citations_models: List[TutorCitation] = []
    seen_sources = set()
    for r in results:
        src = r.get("source", {})
        key = (src.get("source_id"), src.get("page"))
        if key in seen_sources:
            continue

        if r.get("score", 0.0) < 0.20:
            continue

        seen_sources.add(key)
        cit = TutorCitation(
            content_unit_id=r.get("id"),
            source_id=src.get("source_id"),
            filename=src.get("filename", ""),
            page=src.get("page"),
            score=r.get("score"),
            content_type=src.get("type", "pdf"),
            snippet=r.get("text", "")[:300].strip(),
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

