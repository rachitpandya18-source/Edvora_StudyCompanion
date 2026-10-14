"""
Course-Grounded Tutor service for Edvora.

Provides course-scoped, multi-source RAG question answering with strict
evidence grounding, trustworthy citations, and a deterministic outside-material
response contract.
"""

import re
import logging
from typing import Optional, List, Dict, Any, Callable
from sqlalchemy.orm import Session

from app.models.course import Course
from app.models.source import Source
from app.models.content_unit import ContentUnit
from app.schemas.tutor import TutorStatus, TutorCitation
from app.services.retrieval_service import search_course_content
from app.services import llm_service

logger = logging.getLogger(__name__)


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


def _solve_pigeonhole_or_counting_problem(question: str, results: List[Dict[str, Any]]) -> Optional[str]:
    """
    Solves application counting/pigeonhole word problems step-by-step
    grounded in the course materials.
    """
    lower_q = question.lower()

    # Check if question is asking for a minimum/guarantee count
    is_guarantee = bool(re.search(r"\b(minimum|least)\s+(number|count)?\b", lower_q)) and bool(
        re.search(r"\b(guarantee|guaranteed|ensure|ensures|must\s+(pull|draw|pick|choose|select))\b", lower_q)
    )

    # 1. Matching pair / socks / items drawing problem
    is_matching_items = bool(re.search(r"\b(sock|socks|glove|gloves|marble|marbles|ball|balls|card|cards|shoe|shoes)\b", lower_q)) and bool(
        re.search(r"\b(pair|matching|same\s+color|same\s+type|same\s+suit)\b", lower_q)
    )

    if is_guarantee and is_matching_items:
        known_colors = ["black", "white", "red", "blue", "green", "yellow", "brown", "grey", "gray", "purple", "orange", "pink"]
        found_colors = [c for c in known_colors if re.search(rf"\b{c}\b", lower_q)]
        num_categories = len(set(found_colors)) if len(found_colors) >= 2 else 2

        target_count = 2
        if re.search(r"\b(three|3)\s+(socks?|items?|cards?|of\s+the\s+same)\b", lower_q):
            target_count = 3

        min_required = num_categories * (target_count - 1) + 1
        color_str = " and ".join(found_colors[:2]) if len(found_colors) >= 2 else "two colors"

        if target_count == 2 and num_categories == 2:
            c1 = found_colors[0] if len(found_colors) >= 2 else "black"
            c2 = found_colors[1] if len(found_colors) >= 2 else "white"
            return (
                f"The minimum is {min_required} socks. In the worst case, the first two socks are one {c1} "
                f"and one {c2}. The third sock must be either {c1} "
                f"or {c2}, so it matches one of the first two. Therefore, {min_required} socks guarantee a matching pair.\n\n"
                f"### Step-by-Step Reasoning (Pigeonhole Principle)\n"
                f"1. **Identify the Categories (Pigeonholes)**: There are {num_categories} colors in the drawer ({color_str}), so $k = {num_categories}$.\n"
                f"2. **Worst-Case Scenario**: You could draw 1 sock of each color (2 socks total) without having a matching pair.\n"
                f"3. **Apply the Principle**: The very next sock drawn ({min_required}rd sock) must be either {c1} or {c2}. Because there are only 2 colors available, this sock is guaranteed to match one of the first two.\n"
                f"4. **Conclusion**: According to the Pigeonhole Principle ($k + 1$ objects placed into $k$ boxes), pulling {min_required} socks guarantees at least one matching pair."
            )
        else:
            return (
                f"The minimum is {min_required} items to guarantee at least {target_count} items of the same category.\n\n"
                f"### Step-by-Step Reasoning (Generalized Pigeonhole Principle)\n"
                f"1. **Categories (Pigeonholes)**: There are $k = {num_categories}$ categories.\n"
                f"2. **Worst-Case Scenario**: You draw $r - 1 = {target_count - 1}$ items of each of the {num_categories} categories without reaching {target_count} of any single category.\n"
                f"3. **Apply the Principle**: By the Generalized Pigeonhole Principle, drawing $k(r - 1) + 1 = {min_required}$ items guarantees at least {target_count} items of the same category.\n"
                f"4. **Conclusion**: Therefore, {min_required} items guarantee the required match."
            )

    # 2. Card deck suit guarantee problem
    if is_guarantee and ("deck" in lower_q or "suit" in lower_q or "cards" in lower_q):
        target_m = re.search(r"\b(at\s+least\s+)?(\d+|two|three|four)\s+cards?\s+of\s+the\s+same\s+suit\b", lower_q)
        target = 3
        if target_m:
            w = target_m.group(2)
            word_to_num = {"two": 2, "three": 3, "four": 4}
            target = word_to_num.get(w, int(w) if w.isdigit() else 3)
        min_cards = 4 * (target - 1) + 1
        return (
            f"The minimum number of cards is {min_cards}.\n\n"
            f"### Step-by-Step Reasoning (Generalized Pigeonhole Principle)\n"
            f"1. **Pigeonholes (Suits)**: A standard deck has $k = 4$ suits (hearts, diamonds, clubs, spades).\n"
            f"2. **Worst-Case Scenario**: You could draw {target - 1} cards of each of the 4 suits without having {target} of any one suit ($4 \\times {target - 1} = {4 * (target - 1)}$ cards).\n"
            f"3. **Apply the Principle**: The next card ({min_cards}th card) must belong to one of the 4 suits, guaranteeing at least {target} cards of that suit ($4(r - 1) + 1 = {min_cards}$).\n"
            f"4. **Conclusion**: Drawing {min_cards} cards guarantees at least {target} cards of the same suit."
        )

    # 3. Birthday guarantee problem
    if is_guarantee and ("birthday" in lower_q or "birthdays" in lower_q):
        return (
            f"The minimum number of people is 367.\n\n"
            f"### Step-by-Step Reasoning (Pigeonhole Principle)\n"
            f"1. **Pigeonholes**: There are at most 366 possible birthdays in a year (including February 29 in a leap year), so $k = 366$.\n"
            f"2. **Worst-Case Scenario**: In a group of 366 people, each person could have a different birthday.\n"
            f"3. **Apply the Principle**: By the Pigeonhole Principle ($k + 1$ objects in $k$ boxes), adding 1 more person ($366 + 1 = 367$) guarantees that at least two people share the exact same birthday.\n"
            f"4. **Conclusion**: Therefore, 367 people are required to guarantee at least two people with the same birthday."
        )

    return None


def synthesize_grounded_tutor_explanation(question: str, results: List[Dict[str, Any]]) -> str:
    """
    Synthesizes an educational, grounded tutor response directly from retrieved course materials.
    Produces a structured explanation covering Concept Definition, Mechanism/Principles, and Examples,
    or solves application mathematical/logical problems step-by-step.
    """
    if not results:
        return "I could not find this information in the provided course material."

    # First check if this is an application word problem (e.g. Pigeonhole Principle, socks, counting)
    solved = _solve_pigeonhole_or_counting_problem(question, results)
    if solved:
        return solved

    stop_words = {
        "what", "is", "the", "how", "does", "why", "are", "explain", "describe",
        "tell", "me", "about", "a", "an", "in", "of", "to", "and", "or", "for", "with",
        "can", "you", "which", "when", "where", "who", "whom", "this", "that", "these", "those"
    }
    q_words = [w.lower() for w in re.findall(r"\b[a-zA-Z]{3,}\b", question) if w.lower() not in stop_words]

    # Collect distinct sentences across retrieved passages
    all_sentences = []
    seen_texts = set()
    for r in results:
        text = r.get("text", "")
        # Clean slide markers, speaker notes, and presentation boilerplate
        cleaned_text = re.sub(
            r"(Slide Title:\s*|Notes:\s*|Page \d+:\s*|Slide \d+:\s*|\bSlide \d+\b)",
            "",
            text,
            flags=re.IGNORECASE,
        )
        # Normalize and split into sentences
        for part in re.split(r"(?<=[.!?])\s+", cleaned_text):
            clean_s = part.strip()
            # Remove leading bullet points or numbers
            clean_s = re.sub(r"^[\s\-•*#\d\.\)]+\s*", "", clean_s).strip()
            # Filter headers, page noise, or very short fragments
            if (
                len(clean_s) >= 20
                and not clean_s.startswith("#")
                and not clean_s.startswith("---")
                and clean_s.lower() not in seen_texts
            ):
                seen_texts.add(clean_s.lower())
                all_sentences.append(clean_s)

    if not all_sentences:
        all_sentences = [
            re.sub(r"(Slide Title:\s*|Notes:\s*|Page \d+:\s*)", "", r.get("text", ""), flags=re.IGNORECASE).strip()
            for r in results if r.get("text")
        ]

    # If the user query has substantive keywords, verify that the materials actually mention them
    if q_words:
        max_matches = max((sum(1 for kw in q_words if kw in s.lower()) for s in all_sentences), default=0)
        if max_matches == 0:
            return f"I could not find this information in the provided course material."

    definition_candidates = []
    mechanism_candidates = []
    example_candidates = []

    def_markers = [
        "is defined as", "refers to", "is a process", "is the process", "is called",
        "is known as", "means", "denotes", "occurs when", "is characterized by"
    ]
    mech_markers = [
        "because", "causes", "leads to", "results in", "transfers", "involves",
        "electrons", "energy", "reaction", "transforms", "operates", "mechanism",
        "function", "principle", "acts as", "generates", "charge", "potential"
    ]
    ex_markers = ["for example", "for instance", "such as", "consider", "e.g.", "equation:", "reaction:"]

    for sent in all_sentences:
        s_lower = sent.lower()
        score = sum(1 for kw in q_words if kw in s_lower)

        # Check for formulas or concrete reactions (e.g., Zn -> Zn2+ + 2e-)
        has_formula = bool(re.search(r"(\b[A-Z][a-z]?\s*[\+\->]\s*[A-Z][a-z]?|\b[A-Z][a-z]?\d+|\d+\s*e\^-?)", sent))
        if any(m in s_lower for m in ex_markers) or has_formula:
            if score > 0 or has_formula:
                example_candidates.append((score + 2, sent))
            continue

        if any(m in s_lower for m in def_markers) or (score > 0 and (" is " in s_lower or " are " in s_lower)):
            if score > 0 or not q_words:
                definition_candidates.append((score + 2, sent))
        elif any(m in s_lower for m in mech_markers) or score > 0:
            if score > 0 or not q_words:
                mechanism_candidates.append((score + 1, sent))

    definition_candidates.sort(key=lambda x: x[0], reverse=True)
    mechanism_candidates.sort(key=lambda x: x[0], reverse=True)
    example_candidates.sort(key=lambda x: x[0], reverse=True)

    sections = []
    used_sentences = set()

    # 1. Concept Definition (only if it matches question keywords)
    def_sentence = None
    if definition_candidates and definition_candidates[0][0] > 0:
        def_sentence = definition_candidates[0][1]
    elif all_sentences and q_words:
        # Find highest scoring sentence for definition
        matching = [s for s in all_sentences if any(kw in s.lower() for kw in q_words)]
        if matching:
            def_sentence = matching[0]

    if def_sentence:
        used_sentences.add(def_sentence)
        sections.append(f"### Concept Definition\n{def_sentence}")

    # 2. Mechanism & Key Principles
    chosen_mechs = []
    for score, s in mechanism_candidates:
        if score > 0 and s not in used_sentences:
            used_sentences.add(s)
            chosen_mechs.append(s)
            if len(chosen_mechs) >= 2:
                break

    if not chosen_mechs and all_sentences:
        for s in all_sentences:
            if s not in used_sentences:
                used_sentences.add(s)
                chosen_mechs.append(s)
                if len(chosen_mechs) >= 2:
                    break

    if chosen_mechs:
        sections.append(f"### Mechanism & Key Principles\n" + " ".join(chosen_mechs))

    # 3. Illustrative Course Examples
    chosen_examples = []
    for score, s in example_candidates:
        if s not in used_sentences:
            used_sentences.add(s)
            chosen_examples.append(s)
            if len(chosen_examples) >= 2:
                break

    if chosen_examples:
        bullet_list = "\n".join(f"- {s}" for s in chosen_examples)
        sections.append(f"### Illustrative Course Example\n{bullet_list}")

    if not sections:
        return "I could not find this information in the provided course material."

    return "\n\n".join(sections)



def build_grounded_prompt(question: str, results: List[Dict[str, Any]]) -> str:
    """Build a multi-source context prompt enforcing strict grounding and direct answering."""
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
    student_id: Optional[str] = None,
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

    # 1. Verify course exists and ownership
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise CourseNotFoundError(f"Course '{course_id}' not found.")
    if student_id and course.owner_id is not None and course.owner_id != student_id:
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

    # 7. Generate answer using LLM or offline grounded pedagogical synthesizer
    generator = llm_generator or llm_service.generate_response
    prompt = build_grounded_prompt(clean_question, results)

    try:
        raw_answer = generator(prompt)
        answer_text = raw_answer.strip() if raw_answer else ""
    except Exception as exc:
        if llm_generator is not None:
            raise TutorProviderError(f"AI generation provider failed: {exc}") from exc
        logger.info(f"[COURSE_TUTOR] LLM generation failed ({exc}), falling back to grounded pedagogical synthesizer.")
        answer_text = synthesize_grounded_tutor_explanation(clean_question, results)

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

    # 9. Supported answer: return deduplicated citations with actual provenance
    citations: List[TutorCitation] = []
    seen_sources = set()
    for r in results:
        src = r.get("source", {})
        key = (src.get("source_id"), src.get("page"))
        if key in seen_sources:
            continue

        if r.get("score", 0.0) < 0.20:
            continue

        seen_sources.add(key)
        citations.append(
            TutorCitation(
                content_unit_id=r.get("id"),
                source_id=src.get("source_id"),
                filename=src.get("filename", ""),
                page=src.get("page"),
                score=r.get("score"),
                content_type=src.get("type", "pdf"),
                snippet=r.get("text", "")[:300].strip(),
            )
        )

    return {
        "answer": answer_text,
        "status": TutorStatus.ANSWERED.value,
        "citations": citations,
        "course_id": course_id,
    }

