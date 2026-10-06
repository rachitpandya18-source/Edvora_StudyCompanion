import json

from app.services.llm_service import generate_response
from app.services.retrieval_service import search_chunks
from app.services.question_history_service import (
    get_question_history,
    add_questions,
)
from app.services.question_similarity_service import (
    is_similar_question,
)
from app.services.question_grounding_service import (
    check_questions_grounding,
)

# ============================================================
# CONFIGURATION
# ============================================================

CANDIDATE_BUFFER = 2
MAX_GENERATION_ATTEMPTS = 2

# Similarity threshold for questions already present
# in previous quizzes.
PREVIOUS_QUESTION_SIMILARITY_THRESHOLD = 0.85

# Slightly lower threshold for questions inside
# the same newly generated quiz.
CURRENT_QUIZ_SIMILARITY_THRESHOLD = 0.80


# ============================================================
# JSON PARSING
# ============================================================

def _parse_quiz_response(response):
    cleaned_response = response.strip()

    # Remove Markdown code fences if Gemini adds them
    if cleaned_response.startswith("```"):
        lines = cleaned_response.splitlines()

        if lines and lines[0].startswith("```"):
            lines = lines[1:]

        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]

        cleaned_response = "\n".join(lines).strip()

    try:
        result = json.loads(cleaned_response)
    except json.JSONDecodeError as error:
        print("[QUIZ] Invalid JSON returned by LLM.")
        print(f"[QUIZ] Raw response: {response}")
        print(f"[QUIZ] JSON error: {error}")

        # Try to repair common accidental fields inserted by the LLM.
        import re

        repaired = re.sub(
            r'^\s*[A-Za-z_][A-Za-z0-9_]*\s*:\s*"[^"]*"\s*,?\s*$',
            "",
            cleaned_response,
            flags=re.MULTILINE,
        )

        try:
            result = json.loads(repaired)
            print("[QUIZ] JSON repaired successfully.")
        except json.JSONDecodeError:
            raise ValueError(
                "LLM returned invalid JSON while generating quiz."
            ) from error

    if not isinstance(result, dict):
        raise ValueError("Quiz response must be a JSON object.")

    questions = result.get("questions")

    if not isinstance(questions, list):
        raise ValueError(
            "Quiz response must contain a 'questions' list."
        )

    # Keep only the fields our application actually uses.
    cleaned_questions = []

    allowed_fields = {
        "question",
        "options",
        "correct_answer",
        "explanation",
        "difficulty",
    }

    for question in questions:
        if not isinstance(question, dict):
            continue

        cleaned_question = {
            key: value
            for key, value in question.items()
            if key in allowed_fields
        }

        cleaned_questions.append(cleaned_question)

    result["questions"] = cleaned_questions

    return result


# ============================================================
# QUESTION TYPE CLASSIFICATION
# ============================================================

def _classify_question_type(question_text):
    """
    Classify a question into a broad learning type.

    This is subject-independent.
    """

    text = question_text.lower()

    comparison_keywords = [
        "difference between",
        "compare",
        "comparison",
        "distinguish",
        "different from",
        "whereas",
        "versus",
        "vs.",
    ]

    application_keywords = [
        "application",
        "used for",
        "used to",
        "practical",
        "purpose",
        "applied",
        "use of",
        "use in",
    ]

    reasoning_keywords = [
        "why",
        "how does",
        "what happens",
        "what would happen",
        "reason",
        "consequence",
        "effect",
        "cause",
        "result",
    ]

    equation_keywords = [
        "equation",
        "formula",
        "calculate",
        "value of",
        "solve",
        "expression",
        "mathematical",
        "relation",
    ]

    definition_keywords = [
        "what is",
        "what are",
        "which is",
        "which of the following defines",
        "defined as",
        "refers to",
        "means",
        "definition",
    ]

    if any(
        keyword in text
        for keyword in comparison_keywords
    ):
        return "comparison"

    if any(
        keyword in text
        for keyword in application_keywords
    ):
        return "application"

    if any(
        keyword in text
        for keyword in reasoning_keywords
    ):
        return "reasoning"

    if any(
        keyword in text
        for keyword in equation_keywords
    ):
        return "equation"

    if any(
        keyword in text
        for keyword in definition_keywords
    ):
        return "definition"

    return "conceptual"


# ============================================================
# QUESTION VALIDATION
# ============================================================

def _validate_question(question):
    """
    Validate one LLM-generated MCQ.

    Returns:

        (True, "valid")

    or:

        (False, "reason")
    """

    if not isinstance(question, dict):
        return False, "question is not a dictionary"

    required_fields = [
        "question",
        "options",
        "correct_answer",
        "explanation",
        "difficulty",
    ]

    for field in required_fields:

        if field not in question:
            return False, f"missing field: {field}"

    question_text = str(
        question["question"]
    ).strip()

    if not question_text:
        return False, "empty question text"

    options = question["options"]

    if not isinstance(options, list):
        return False, "options is not a list"

    if len(options) != 4:
        return False, (
            f"expected 4 options, got {len(options)}"
        )

    normalized_options = [
        str(option).strip().lower()
        for option in options
    ]

    if len(set(normalized_options)) != 4:
        return False, "duplicate options"

    correct_answer = str(
        question["correct_answer"]
    ).strip()

    exact_options = [
        str(option).strip()
        for option in options
    ]

    if correct_answer not in exact_options:
        return False, (
            "correct_answer does not exactly match "
            "one of the options"
        )

    difficulty = str(
        question["difficulty"]
    ).strip().lower()

    if difficulty not in [
        "easy",
        "medium",
        "hard",
    ]:
        return False, (
            f"invalid difficulty: {difficulty}"
        )

    explanation = str(
        question["explanation"]
    ).strip()

    if not explanation:
        return False, "empty explanation"

    return True, "valid"


# ============================================================
# DOCUMENT-STRUCTURE QUESTION DETECTION
# ============================================================

def _is_document_structure_question(question_text):
    """
    Reject questions about PDF layout instead of
    actual academic knowledge.
    """

    text = question_text.lower()

    blocked_patterns = [
        "which page",
        "what page",
        "on page",
        "page number",
        "which section",
        "what section",
        "which heading",
        "what heading",
        "appears before",
        "appears after",
        "comes before",
        "comes after",
        "listed alongside",
        "section order",
        "heading order",
    ]

    return any(
        pattern in text
        for pattern in blocked_patterns
    )


# ============================================================
# SEMANTIC DUPLICATE CHECK
# ============================================================

def _is_similar_to_any(
    question_text,
    previous_questions,
    threshold,
):
    """
    Check whether a question is semantically similar
    to any question in a given collection.
    """

    if not previous_questions:
        return False

    return is_similar_question(
        question_text,
        previous_questions,
        threshold=threshold,
    )


# ============================================================
# QUESTION FILTERING
# ============================================================

def _filter_questions(
    generated_questions,
    previous_questions,
    accepted_question_texts,
    document_context,
):
    prefiltered = []
    rejected_texts = []

    # ---------------------------------------------
    # STEP 1: Basic validation + repetition checks
    # ---------------------------------------------

    for question in generated_questions:
        if not isinstance(question, dict):
            print("[QUIZ] Rejected non-dictionary question:", question)
            continue

        question_text = question.get("question", "").strip()

        is_valid, reason = _validate_question(question)
        if not is_valid:
            print("[QUIZ] Rejected invalid question:")
            print(question_text)
            print("[QUIZ] Reason:", reason)
            if question_text:
                rejected_texts.append(question_text)
            continue

        if _is_document_structure_question(question_text):
            print("[QUIZ] Rejected document-structure question:")
            print(question_text)
            rejected_texts.append(question_text)
            continue

        # Check against questions from previous quizzes
        if is_similar_question(
            question_text,
            previous_questions,
            threshold=PREVIOUS_QUESTION_SIMILARITY_THRESHOLD,
        ):
            print("[QUIZ] Rejected previous-question duplicate:")
            print(question_text)
            rejected_texts.append(question_text)
            continue

        # Check against questions already accepted
        # in the current quiz
        if _is_similar_to_any(
            question_text,
            accepted_question_texts,
            CURRENT_QUIZ_SIMILARITY_THRESHOLD,
        ):
            print("[QUIZ] Rejected current-quiz duplicate:")
            print(question_text)
            rejected_texts.append(question_text)
            continue

        prefiltered.append(question)

    # ---------------------------------------------
    # STEP 2: Batch grounding verification
    # ---------------------------------------------

    if not prefiltered:
        return [], rejected_texts

    print(
        f"[GROUNDING] Batch checking "
        f"{len(prefiltered)} questions..."
    )

    grounding_results = check_questions_grounding(
        prefiltered,
        document_context,
    )

    # ---------------------------------------------
    # STEP 3: Accept only grounded questions
    # ---------------------------------------------

    accepted = []

    for question, grounding_result in zip(
        prefiltered,
        grounding_results,
    ):
        question_text = question["question"]

        if not grounding_result["grounded"]:
            print("[GROUNDING] Rejected ungrounded question:")
            print(question_text)
            print(
                "[GROUNDING] Reason:",
                grounding_result["reason"],
            )

            rejected_texts.append(question_text)
            continue

        print("[GROUNDING] Question grounded successfully:")
        print(question_text)

        accepted.append(question)

        # IMPORTANT:
        # Add to current quiz history only AFTER
        # grounding succeeds.
        accepted_question_texts.append(question_text)

    return accepted, rejected_texts
# ============================================================
# PROMPT BUILDER
# ============================================================

def _build_quiz_prompt(
    topic,
    concept,
    document_context,
    questions_to_avoid,
    num_questions,
):
    """
    Build a subject-independent quiz generation prompt.
    """

    questions_to_avoid_text = "\n".join(
        f"- {question}"
        for question in questions_to_avoid
    )

    if not questions_to_avoid_text:
        questions_to_avoid_text = (
            "No previous questions."
        )

    return f"""
You are an expert adaptive educational quiz generator.

Generate {num_questions} candidate multiple-choice
questions for the requested learning concept.

TOPIC:
{topic}

CONCEPT:
{concept}

IMPORTANT:
Use ONLY the provided study material.

Do NOT use outside knowledge.

The generated questions will later be filtered by
a software system. Therefore, generate genuinely
different candidate questions rather than paraphrases
of the same fact.

==================================================
QUESTION QUALITY
==================================================

Questions should test actual understanding.

Prefer different supported learning angles such as:

- Definition / understanding
- Conceptual reasoning
- Application
- Comparison
- Cause and effect
- Equation interpretation
- Scientific or mathematical relationship
- Practical implications

Do NOT force a question type if the study material
does not support it.

==================================================
DIVERSITY
==================================================

Avoid generating several questions about the exact
same underlying fact.

For example, do NOT generate:

1. What frequency defines X?
2. What frequency range does X have?
3. Which frequency is associated with X?
4. What is the frequency limit of X?

These are essentially testing the same fact.

Instead, when the material supports it, cover
different concepts, relationships, equations,
applications, or reasoning patterns.

==================================================
NO DOCUMENT-STRUCTURE QUESTIONS
==================================================

Never ask:

- Which topic appears on page X?
- Which section comes before X?
- Which heading comes after X?
- What appears on page X?
- On which page does X appear?
- Which topic is listed alongside X?
- Which section appears before another section?
- Which heading appears immediately after another heading?

Ask about the academic material itself.

==================================================
FORMULAS AND EQUATIONS
==================================================

Preserve formulas exactly as provided in the
study material.

Do not replace:

- Superscripts
- Subscripts
- Charges
- Mathematical symbols
- Greek symbols
- Variables
- Arrows

Examples from possible scientific material:

M → Mⁿ⁺ + ne⁻
X + ne⁻ → Xⁿ⁻
Zn(s) → Zn²⁺(aq) + 2e⁻
Cu²⁺(aq) + 2e⁻ → Cu(s)
E°cell = E°cathode − E°anode
G = 1/R
Q = It
m = ZIt

These are examples only.

Do NOT assume the current document is Chemistry.

Use formulas actually present in the provided material.

==================================================
MCQ RULES
==================================================

Every question must:

- Be answerable from the provided study material.
- Have exactly 4 options.
- Have exactly one correct answer.
- Have the correct answer exactly matching one option.
- Be clear and unambiguous.
- Avoid trick wording.
- Avoid outside knowledge.
- Include a short explanation.
- Have difficulty exactly equal to:
  easy, medium, or hard.

==================================================
REPETITION
==================================================

These questions have already been generated or rejected:

{questions_to_avoid_text}

Do NOT generate questions that are identical or
substantially similar to these.

Test the same concept from a genuinely different angle
when possible.

==================================================
OUTPUT
==================================================

Return ONLY valid JSON.

Do not use Markdown.

Use exactly this structure:

{{
  "questions": [
    {{
      "question": "Question text",
      "options": [
        "Option A",
        "Option B",
        "Option C",
        "Option D"
      ],
      "correct_answer": "Option A",
      "explanation": "Short explanation based only on the study material.",
      "difficulty": "easy"
    }}
  ]
}}

==================================================
RELEVANT STUDY MATERIAL
==================================================

{document_context}
"""


# ============================================================
# SOURCE INFORMATION
# ============================================================

def _build_sources(relevant_chunks):
    """
    Build unique source references.
    """

    sources = []

    for chunk in relevant_chunks:

        source = chunk["source"]

        source_info = {
            "filename": source["filename"],
            "page": source["page"],
        }

        if source_info not in sources:
            sources.append(
                source_info
            )

    return sources


# ============================================================
# MAIN QUIZ GENERATION
# ============================================================

def generate_quiz(
    chunks,
    topic,
    concept,
    num_questions=5,
):
    """
    Generate a grounded adaptive MCQ quiz.

    Pipeline:

        Retrieve
            ↓
        Generate candidates
            ↓
        Validate
            ↓
        Remove previous duplicates
            ↓
        Remove current duplicates
            ↓
        Select final questions
            ↓
        Store history
    """

    if not chunks:
        return {
            "questions": []
        }

    if num_questions <= 0:
        return {
            "questions": []
        }

    # --------------------------------------------------------
    # Retrieve relevant study material
    # --------------------------------------------------------

    retrieval_query = (
        f"{topic}: {concept}"
    )

    relevant_chunks = search_chunks(
        chunks,
        retrieval_query,
        top_k=3,
    )

    if not relevant_chunks:
        return {
            "questions": []
        }

    # --------------------------------------------------------
    # Previous question history
    # --------------------------------------------------------

    previous_questions = get_question_history(
        topic,
        concept,
    )

    # --------------------------------------------------------
    # Build context
    # --------------------------------------------------------

    document_context = "\n\n".join(
        f"[Source: "
        f"{chunk['source']['filename']}, "
        f"Page: "
        f"{chunk['source']['page']}]\n"
        f"{chunk['text']}"
        for chunk in relevant_chunks
    )

    # --------------------------------------------------------
    # Candidate / final storage
    # --------------------------------------------------------

    accepted_questions = []

    accepted_question_texts = []

    questions_to_avoid = list(
        previous_questions
    )

    # --------------------------------------------------------
    # Generate candidates
    # --------------------------------------------------------

    for attempt in range(
        1,
        MAX_GENERATION_ATTEMPTS + 1,
    ):

        remaining = (
            num_questions
            - len(accepted_questions)
        )

        if remaining <= 0:
            break

        candidate_count = (
            remaining
            + CANDIDATE_BUFFER
        )

        print(
            f"[QUIZ] Generation attempt "
            f"{attempt}/"
            f"{MAX_GENERATION_ATTEMPTS}"
        )

        print(
            f"[QUIZ] Requesting "
            f"{candidate_count} "
            f"candidate questions"
        )

        prompt = _build_quiz_prompt(
            topic=topic,
            concept=concept,
            document_context=document_context,
            questions_to_avoid=questions_to_avoid,
            num_questions=candidate_count,
        )

        # ----------------------------------------------------
        # LLM call
        # ----------------------------------------------------

        response = generate_response(
            prompt
        )

        # ----------------------------------------------------
        # Parse JSON
        # ----------------------------------------------------

        result = _parse_quiz_response(
            response
        )

        generated_questions = result.get(
            "questions",
            [],
        )

        print(
            f"[QUIZ] LLM generated "
            f"{len(generated_questions)} "
            f"candidate questions"
        )

        # ----------------------------------------------------
        # Filter candidates
        # ----------------------------------------------------

        filtered_questions, rejected_questions = _filter_questions(
    generated_questions,
    previous_questions,
    accepted_question_texts,
    document_context,
)

        # ----------------------------------------------------
        # Add accepted candidates
        # ----------------------------------------------------

        for question in filtered_questions:

            if len(accepted_questions) >= num_questions:
                break

            accepted_questions.append(
                question
            )

        # ----------------------------------------------------
        # Update avoid list
        # ----------------------------------------------------

        for question in rejected_questions:

            if question and question not in questions_to_avoid:

                questions_to_avoid.append(
                    question
                )

        for question in accepted_question_texts:

            if (
                question
                and question not in questions_to_avoid
            ):

                questions_to_avoid.append(
                    question
                )

        print(
            f"[QUIZ] Current final count: "
            f"{len(accepted_questions)}/"
            f"{num_questions}"
        )

        # ----------------------------------------------------
        # Stop if enough questions
        # ----------------------------------------------------

        if len(accepted_questions) >= num_questions:
            break

    # ========================================================
    # FINALIZE
    # ========================================================

    # Never return more than requested.
    accepted_questions = accepted_questions[
        :num_questions
    ]

    # --------------------------------------------------------
    # Attach source information
    # --------------------------------------------------------

    # ==========================================
# Attach exact supporting source per question
# ==========================================

    # ==========================================
    # Attach exact supporting source per question
    # ==========================================

    for question in accepted_questions:

        evidence_query = (
            f"{question['question']} "
            f"Correct answer: {question['correct_answer']} "
            f"Explanation: {question['explanation']}"
        )

        supporting_chunks = search_chunks(
            chunks,
            evidence_query,
            top_k=1
        )

        question["sources"] = _build_sources(
            supporting_chunks
        )

    # ==========================================
    # Store only final questions
    # ==========================================

    add_questions(
        topic,
        concept,
        accepted_questions
    )

    print(
        f"[QUIZ] Final quiz contains "
        f"{len(accepted_questions)}/"
        f"{num_questions} unique questions."
    )

    return {
        "questions": accepted_questions
    }