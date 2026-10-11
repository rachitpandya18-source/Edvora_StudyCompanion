# Milestone B9: Learner Analytics & Course Progress Engine

## 1. Overview & Architecture

Milestone B9 introduces a read-only, course-scoped **Learner Analytics & Course Progress Engine** to Edvora. It aggregates existing data from Milestones B3 (Curriculum DAG), B5 (Assessment Attempts & Evaluated Answers), and B6 (Bayesian Knowledge Tracing Learner Mastery) to power comprehensive executive dashboards, topic progress cards, concept breakdowns, and chronological practice velocity trends for students and instructors.

### Architectural Invariants & Ownership Boundaries
- **No Duplicate Systems:**
  - **B6** remains the sole owner of Bayesian Knowledge Tracing ($P(L_t)$ probability tracking and updates).
  - **B7** remains the sole owner of adaptive recommendation sequencing and next-step actions.
  - **B5** remains the sole owner of assessment evaluations and attempt lifecycles.
  - **B8** remains the sole owner of adaptive practice question generation.
  - **B3** remains the sole owner of topic/concept curriculum hierarchy.
- **No Invented Tracking Mechanisms:** 
  - There is no persistent learner document/reading tracking model in the architecture.
  - Syllabus completion is strictly defined by demonstrable assessment practice: a concept is deemed "completed" if and only if the learner has submitted at least one assessment attempt containing questions mapped to that concept.
- **Pure Read/Aggregate Operation:**
  - Analytics endpoints never mutate the database, execute updates, or alter student mastery states.
- **Zero Database Migrations:**
  - All metrics are calculated dynamically using existing relational models (`Course`, `Topic`, `Concept`, `LearnerConceptMastery`, `Assessment`, `Question`, `AssessmentAttempt`, `AttemptAnswer`).

---

## 2. Core Metrics & Mathematical Formulations

### A. Overall Course Mastery
Calculates the mean mastery probability across all concepts within the course:
$$\text{overall\_mastery} = \frac{\sum_{c \in C} P(L_c)}{|C|}$$
- If a concept has no record in `LearnerConceptMastery`, the default initial prior $P(L_0) = 0.10$ is applied.
- If the course has zero concepts ($|C| = 0$), `overall_mastery` evaluates to $0.0$.

### B. Syllabus Completion Rate
Defined by verified assessment attempt submission:
$$\text{completion\_rate} = \frac{\text{count of concepts with } \ge 1 \text{ completed attempt}}{|C|}$$
- Evaluates to $0.0$ if $|C| = 0$.

### C. Mastery Distribution Categories
Every concept in the course is assigned to one of five deterministic categories:
- **`mastered`**: $P(L) \ge 0.85$
- **`proficient`**: $0.70 \le P(L) < 0.85$
- **`developing`**: $0.40 \le P(L) < 0.70$
- **`struggling`**: $P(L) < 0.40$ **AND** at least one completed assessment attempt
- **`unassessed`**: Zero completed assessment attempts (regardless of prior knowledge default)

### D. Topic-Level Progress Rollups
For every topic in curriculum order (`order_index`):
- `total_concepts`: Count of concepts in this topic.
- `mastered_concepts`: Count of concepts with $P(L) \ge 0.85$.
- `average_mastery`: Mean $P(L)$ across concepts in this topic.
- `completion_percentage`: $(\text{completed concepts} / \text{total concepts}) \times 100.0$.
- `status`:
  - `not_started`: Zero concepts completed within the topic.
  - `in_progress`: At least one concept completed, but topic average mastery $< 0.85$.
  - `mastered`: Topic average mastery $\ge 0.85$.

### E. Assessment Summary
Aggregates student performance across completed attempts:
- `total_attempts`: Count of attempts with `status == "submitted"`.
- `total_questions_answered`: Count of `AttemptAnswer` records across completed attempts.
- `overall_accuracy`: $\frac{\sum \text{earned score}}{\sum \text{max score}}$ (bounded in $[0.0, 1.0]$).
- `last_practiced_at`: Most recent attempt timestamp (`submitted_at` or `created_at`).

### F. Velocity & Performance Trends
Buckets completed attempts into calendar days ($YYYY\text{-}MM\text{-}DD$) within a configurable window (default: 30 days, range: $[1, 365]$):
- `date`: Calendar date.
- `attempt_count`: Number of submitted attempts on that date.
- `average_score_percentage`: Average percentage score obtained across those attempts ($[0.0, 100.0]$).

### G. Exam Readiness Composite Score
Synthesizes comprehensive preparation into a single score bounded in $[0.0, 100.0]$:
$$\text{readiness\_score} = \Big(0.50 \times \text{overall\_mastery} + 0.30 \times \text{completion\_rate} + 0.20 \times \text{recent\_accuracy\_rate}\Big) \times 100$$
- All three components are strictly normalized in $[0.0, 1.0]$ before weighting.
- `recent_accuracy_rate` is computed from completed attempts within the configured lookback window. If no attempts occurred in that window, $0.0$ is used.
- Final readiness is clamped to $[0.0, 100.0]$.

---

## 3. API Contracts

### 1. Course Analytics Overview
- **Endpoint:** `GET /courses/{course_id}/analytics/overview`
- **Query Parameters:**
  - `learner_id` (str, default: `"default_student"`): Unique student identifier.
  - `trend_days` (int, default: `30`): Lookback window in days for recent accuracy.
- **Response Shape (`200 OK`):**
```json
{
  "course_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "learner_id": "default_student",
  "overall_mastery": 0.65,
  "syllabus_completion_rate": 0.80,
  "readiness_score": 71.5,
  "total_concepts": 5,
  "concepts_completed": 4,
  "mastery_breakdown": {
    "mastered": 2,
    "proficient": 1,
    "developing": 1,
    "struggling": 0,
    "unassessed": 1
  },
  "assessment_summary": {
    "total_attempts": 3,
    "total_questions_answered": 12,
    "overall_accuracy": 0.75,
    "last_practiced_at": "2026-10-11T12:00:00Z"
  },
  "topics": [
    {
      "topic_id": "11111111-2222-3333-4444-555555555555",
      "title": "Supply and Demand",
      "order_index": 1,
      "total_concepts": 3,
      "mastered_concepts": 2,
      "average_mastery": 0.88,
      "completion_percentage": 100.0,
      "status": "mastered"
    }
  ]
}
```

### 2. Topic Analytics Detail
- **Endpoint:** `GET /courses/{course_id}/topics/{topic_id}/analytics`
- **Query Parameters:**
  - `learner_id` (str, default: `"default_student"`)
- **Response Shape (`200 OK`):**
```json
{
  "course_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "topic_id": "11111111-2222-3333-4444-555555555555",
  "topic_title": "Supply and Demand",
  "order_index": 1,
  "learner_id": "default_student",
  "total_concepts": 3,
  "mastered_concepts": 2,
  "average_mastery": 0.88,
  "completion_percentage": 100.0,
  "status": "mastered",
  "concepts": [
    {
      "concept_id": "aaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
      "name": "Demand Curves",
      "order_index": 1,
      "mastery_probability": 0.92,
      "mastery_category": "mastered",
      "completed_attempts_count": 3,
      "observation_count": 5,
      "correct_count": 5,
      "last_practiced_at": "2026-10-11T12:00:00Z"
    }
  ]
}
```

### 3. Chronological Velocity Trends
- **Endpoint:** `GET /courses/{course_id}/analytics/trends`
- **Query Parameters:**
  - `learner_id` (str, default: `"default_student"`)
  - `days` (int, default: `30`, min: `1`, max: `365`)
- **Response Shape (`200 OK`):**
```json
{
  "course_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "learner_id": "default_student",
  "days": 30,
  "trends": [
    {
      "date": "2026-10-09",
      "attempt_count": 2,
      "average_score_percentage": 85.0
    },
    {
      "date": "2026-10-10",
      "attempt_count": 1,
      "average_score_percentage": 100.0
    }
  ]
}
```

---

## 4. Multi-Tenant Isolation & Security Rules

1. **Course Scoping:**
   - Every overview, detail, and trend query joins on `Course.id`. Non-existent course IDs return HTTP `404 Not Found`.
2. **Topic-Course Verification:**
   - Topic analytics explicitly verifies `topic.course_id == course_id`. A topic ID belonging to another course returns HTTP `404 Not Found` with an explicit ownership rejection detail.
3. **Learner Isolation:**
   - All masteries and completed attempts filter strictly on `student_id == learner_id`. Data from Student A never bleeds into Student B's mastery categories, completion counters, or score averages.

---

## 5. Verification & Test Suite Summary

- **Automated Tests:** `backend/test_b9_analytics.py` (12 test cases, all passing):
  - `test_missing_course_404`: Non-existent course returns 404.
  - `test_empty_course_analytics`: Zero topics/concepts returns mathematically safe 0.0 values.
  - `test_course_overview_with_unassessed_concepts`: Prior $P(L_0) = 0.10$ used for unassessed concepts.
  - `test_mastery_category_boundaries_and_assessments`: Exact categorizations across 0.85, 0.70, 0.40, struggling, and unassessed.
  - `test_topic_analytics_detail`: Verifies deep topic concept rollups.
  - `test_topic_status_mastered`: Confirms transition to `mastered` status when average mastery $\ge 0.85$.
  - `test_velocity_trends_calculation`: Daily bucketed attempt counts and average percentage scores.
  - `test_velocity_trends_invalid_days`: Parameter validations for $days \le 0$ or $days > 365$.
  - `test_learner_isolation`: Verifies Student A and Student B data isolation.
  - `test_topic_and_course_isolation`: Cross-course topic querying rejected with 404.
  - `test_no_mutation_on_analytics_calls`: Verifies analytics endpoints execute read-only queries with 0 side-effects.
  - `test_learner_isolation_multi_student`: Multi-learner concurrent assessment attempts in the same course maintain complete independence.
- **Milestone Regression:** All prior test suites (`test_b8_practice.py`, `test_b7_study_planner.py`, `test_b6_bkt.py`, `test_b5_assessment.py`, `test_b4_tutor.py`, `test_b3_curriculum.py`, `test_b2_content_retrieval.py`, `test_b1_courses.py`, `test_phase0_economics.py`) and frontend linting/building verified 100% green.

