# Milestone B7 — Adaptive Study Planner

**Status:** Completed & Verified  
**Branch:** `rudresh/backend-b7-adaptive-study-planner`  
**Base:** Merged Milestones B0–B6 on `main`  

---

## 1. Overview & Architectural Role

Milestone B7 delivers the **Adaptive Study Planner** for Edvora. It unifies the curriculum DAG (B3), persistent content units (B2), assessment history (B5), and Bayesian Knowledge Tracing learner mastery estimates (B6) into an explainable, multi-factor recommendation engine.

```mermaid
flowchart TD
    Client["Client / Frontend (StudyNextCard, CourseWorkspace)"] -->|GET /courses/{id}/study-next| API["FastAPI Route: app/api/routes/study_planner.py"]
    Client -->|GET /courses/{id}/study-plan| API

    API --> Service["Planner Service: app/services/study_planner_service.py"]

    subgraph Data Inputs from B1-B6
        Curriculum["Curriculum DAG (Topics, Concepts, Prerequisites)"] --> Service
        Mastery["BKT Learner Mastery (LearnerConceptMastery: P(L_t))"] --> Service
        Content["Content Units (Source Materials & Pages)"] --> Service
        Assessments["Assessments & Question Bank"] --> Service
    end

    subgraph Core Algorithmic Pipeline
        Service --> Readiness["Prerequisite Readiness Evaluator (P(L_prereq) >= 0.70)"]
        Readiness --> Scoring["Multi-Factor Priority Scoring Engine"]
        Scoring --> Categories["Categorization: REVISE_WEAK, UNBLOCK_PREREQUISITE, LEARN_NEW, REFRESH_RETENTION"]
        Categories --> Synthesis["Action Item Synthesis & Grounded Rationale"]
    end

    Synthesis --> Output["StudyNextResponse / StudyPlanResponse"]
```

---

## 2. Core Algorithmic Pipeline

### 1. Concept Readiness Evaluation
A concept is marked `is_ready: True` if and only if **all** of its direct prerequisite concepts have achieved mastery:
$$P(L_{\text{prerequisite}}) \ge 0.70$$
If any prerequisite is unmastered, the dependent concept is assigned the `BLOCKED` category, preventing cognitive overload and pointing the learner to foundational prerequisites first.

### 2. Multi-Factor Priority Scoring Engine
For all candidate concepts in a course, the planner computes a deterministic composite score:
$$S(c) = w_{\text{deficit}} \cdot (1 - P(L_c)) + w_{\text{blocker}} \cdot \text{BlockerScore}(c) + w_{\text{recency}} \cdot \text{DecayScore}(c) + w_{\text{curriculum}} \cdot \text{OrderScore}(c) + \text{StruggleBonus}(c)$$

- **Deficit Weight ($0.50$):** Drives focus toward weak concepts with low knowledge probabilities.
- **Blocker Weight ($0.30$):** Measures the number of downstream dependent concepts blocked by this concept, giving high leverage to foundational bottlenecks.
- **Recency Decay Weight ($0.15$):** Employs spaced repetition for concepts unpracticed for $\ge 7$ days to prevent knowledge retention decay.
- **Curriculum Order Score ($0.05$):** Guides learners along the syllabus sequence when mastery scores are identical.
- **Struggle Bonus ($0.10$):** Elevates concepts with attempted questions that remain below the weak threshold ($P(L) < 0.50$).

### 3. Actionable Next Steps
Every recommendation generates a 3-step structured progression matching the UI contract:
1. **Review Material:** Grounded in specific course sources and page numbers.
2. **Ask AI Tutor:** Deep-link prompt target for clarifying common pitfalls.
3. **Practice Quiz:** Targeted questions from the assessment question bank.

---

## 3. API Reference

Mounted via [backend/app/api/routes/study_planner.py](file:///c:/Users/Rudresh%20Joshi/Desktop/Edvora_Test/Edvora_StudyCompanion/backend/app/api/routes/study_planner.py) into [backend/app/main.py](file:///c:/Users/Rudresh%20Joshi/Desktop/Edvora_Test/Edvora_StudyCompanion/backend/app/main.py):

| Method | Endpoint | Query Params | Description | Response Model |
|---|---|---|---|---|
| `GET` | `/courses/{course_id}/study-next` | `student_id` (default: `"default_student"`) | Returns the single highest-leverage recommendation for the learner | `Optional[StudyNextResponse]` |
| `GET` | `/courses/{course_id}/study-plan` | `student_id` (default: `"default_student"`) | Returns complete prioritized curriculum plan categorized into Focus Next, Ready, Blocked, and Mastered | `StudyPlanResponse` |

---

## 4. Verification Results

1. **Milestone B7 Test Suite (`backend/test_b7_study_planner.py`):**
   - `test_empty_course_study_plan`: PASSED
   - `test_prerequisite_blocking_and_unblocker_priority`: PASSED
   - `test_ready_concept_progression_when_prerequisite_mastered`: PASSED
   - `test_retention_refresh_spaced_repetition`: PASSED
   - `test_course_completed_all_mastered`: PASSED
   - `test_nonexistent_course_404`: PASSED
   - `test_legacy_recommendations_backward_compatibility`: PASSED
   - Result: **7 passed in 2.97s**.

2. **Milestone B6 BKT Suite (`backend/test_b6_bkt.py`):**
   - Result: **ALL PASSED**.

3. **Milestone B1 Courses Suite (`backend/test_b1_courses.py`):**
   - Result: **6 passed in 3.57s**.

4. **Frontend Quality & Build Checks:**
   - `oxlint`: 0 warnings, 0 errors across 57 files.
   - `vite build`: Succeeded in 496ms.

