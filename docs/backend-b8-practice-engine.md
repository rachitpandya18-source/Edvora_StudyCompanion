# Milestone B8 — Adaptive Practice Engine & Dynamic Question Generation

**Status:** Completed & Verified  
**Branch:** `rudresh/backend-b8-adaptive-practice`  
**Base:** Merged Milestones B0–B7 on `main`  

---

## 1. Overview & Architectural Role

Milestone B8 closes the end-to-end adaptive learning loop in Edvora:

$$\text{B7 Study Planner} \longrightarrow \text{B8 Practice Engine} \longrightarrow \text{B5 Assessment Engine} \longrightarrow \text{B6 BKT Mastery} \longrightarrow \text{B7 Updated Study Plan}$$

Rather than creating a parallel quiz or evaluation silo, B8 directly extends and reuses the existing B1–B7 production infrastructure:
- **Retrieval Grounding (B2):** Queries persistent course `ContentUnit`s via `search_course_content` to ground generated questions strictly in course materials.
- **LLM Question Generation:** Prompts Gemini to produce structured, concept-grounded question candidates with educational explanations.
- **Deduplication & Grounding (Phase 0):** Reuses `question_similarity_service` to reject duplicate questions against past attempts and existing banks.
- **Persistence into Assessment Engine (B5):** Persists generated sessions as `Assessment(assessment_type="practice")` with child `Question` records linked to `concept_id`.
- **Pre-populated Student Attempt (B5):** Automatically calls `assessment_service.start_attempt` to issue an active, in-progress `AssessmentAttempt` for the student.
- **Student-Safe API Contract:** Omits `correct_answer` and `explanation` from the returned practice questions, returning an explicit `submit_endpoint`.
- **Single Source of Truth for Mastery (B6):** When the student submits their attempt via the B5 endpoint, B5 evaluates answers and triggers B6's `update_mastery_from_attempt`, updating `LearnerConceptMastery` exactly once.

```mermaid
flowchart TD
    Planner["B7 Study Planner (/courses/{id}/study-plan & /study-next)"] -->|Recommended Concept & Priorities| Student["Student / Client"]

    Student -->|POST /courses/{id}/practice/generate| PracticeRouter["Practice API Router: app/api/routes/practice.py"]
    PracticeRouter --> PracticeService["Practice Service: app/services/practice_service.py"]

    subgraph Grounded Assembly Pipeline
        PracticeService --> Retrieval["B2 Persistent Retrieval: search_course_content()"]
        Retrieval --> LLM["LLM Generation / Dynamic Prompting (Gemini)"]
        LLM --> Dedup["Similarity Deduplication: is_similar_question()"]
        Dedup --> Fallback["Resilient Fallback: Deterministic Concept Grounding"]
    end

    subgraph B5 Assessment & Attempt Persistence
        Fallback --> SaveAssessment["Create Assessment(type='practice') & Questions"]
        SaveAssessment --> StartAttempt["Start Attempt: assessment_service.start_attempt()"]
    end

    StartAttempt --> Response["Student-Safe PracticeSessionResponse (submit_endpoint)"]
    Response --> StudentSubmit["Student Submits Answers via submit_endpoint"]

    subgraph Closed Learning Loop
        StudentSubmit --> B5Grading["B5 Deterministic Evaluator: evaluate_single_answer()"]
        B5Grading --> B6BKT["B6 Bayesian Knowledge Tracing: update_mastery_from_attempt()"]
        B6BKT --> DB[(LearnerConceptMastery)]
        DB --> Planner
    end
```

---

## 2. Practice Modes

B8 provides three pedagogical practice modes:

| Mode | Target Scope | Question Count | Selection Strategy |
|---|---|---|---|
| `adaptive` | Specific Concept | Default: 3–5 (configurable) | Focuses entirely on a designated `concept_id`, or automatically targets the highest-priority concept recommended by B7 Study Planner. |
| `quick` | Weak Concepts | Default: 5 | Identifies all concepts with mastery below threshold ($P(L) < 0.70$) using B6 mastery data; cycles practice questions across the weak pool. |
| `mock_test` | Curriculum Breadth | Default: 5–20 | Samples concepts broadly across all course topics in syllabus order to verify cross-topic retention. |

---

## 3. Resilient Grounding & Fallback Architecture

1. **ContentUnit Semantic Retrieval:** For each targeted concept, `search_course_content` retrieves top matching persistent chunks.
2. **LLM Structured Generation:** Gemini generates candidate questions formatted in strict JSON matching the requested question types (`mcq`, `true_false`, `short_answer`).
3. **Semantic Deduplication:** Candidates with cosine similarity $\ge 0.85$ against previously seen prompts in the session or course question bank are rejected.
4. **Deterministic Fallback:** If the LLM call fails, network times out, or quota is exhausted, the engine seamlessly generates verified, curriculum-grounded fallback questions based on concept metadata and course context. Generation **never crashes or blocks the student**.

---

## 4. API Reference

Mounted via [backend/app/api/routes/practice.py](file:///c:/Users/Rudresh%20Joshi/Desktop/Edvora_Test/Edvora_StudyCompanion/backend/app/api/routes/practice.py) into [backend/app/main.py](file:///c:/Users/Rudresh%20Joshi/Desktop/Edvora_Test/Edvora_StudyCompanion/backend/app/main.py):

### 1. `POST /courses/{course_id}/practice/generate`
- **Status:** `201 Created`
- **Request Body:** `PracticeGenerateRequest`
  ```json
  {
    "mode": "adaptive",
    "concept_id": "concept-uuid-1",
    "question_count": 3,
    "difficulty": "medium",
    "student_id": "student_1"
  }
  ```
- **Response Shape:** `PracticeSessionResponse`
  - `assessment_id`: UUID of the persisted B5 Assessment.
  - `attempt_id`: UUID of the initialized `in_progress` attempt.
  - `questions`: List of `PracticeQuestionItem` (omits correct answers, explanations, and tolerances).
  - `submit_endpoint`: `"/courses/{course_id}/assessments/{assessment_id}/attempts/{attempt_id}/submit"`

### 2. `GET /courses/{course_id}/practice/options`
- **Status:** `200 OK`
- **Response Shape:** `PracticeConfigOptions`
  - Returns course topics with concept counts, supported question types, difficulties, and the B7 recommended concept ID and name.

---

## 5. Security & Isolation Guarantees

- **Course Isolation:** Requests for `concept_id` or `topic_id` belonging to a different course are strictly rejected with HTTP `400 Bad Request`.
- **Student-Safe Question Payloads:** Question answers and explanations are stripped at serialization, preventing client-side inspection before submission.
- **Zero Database Migrations:** Uses the existing B1–B6 schema without modifying any table structures.

