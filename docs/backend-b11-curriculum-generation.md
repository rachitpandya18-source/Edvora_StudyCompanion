# Milestone B11: Automated Curriculum Ingestion & Knowledge Graph Extraction Engine

## 1. Overview & Problem Solved

Milestone B11 resolves the primary "cold-start" bottleneck in Edvora's course-grounded architecture. Previously, while Milestone B2 successfully chunked and embedded uploaded PDFs into `ContentUnit` records, a course possessed **zero** `Topic`, `Concept`, or `ConceptPrerequisite` records unless manually entered via low-level CRUD endpoints. Consequently, the entire downstream educational runtime:
- **Assessment Engine (B5)** (which requires concept IDs),
- **Bayesian Knowledge Tracing (B6)** (which tracks concept mastery),
- **Adaptive Study Planner (B7)** (which sequences concepts via prerequisite DAGs),
- **Adaptive Practice Engine (B8)** (which generates concept-targeted practice), and
- **Learner Analytics (B9)** (which aggregates topic/concept progress),

remained completely starved of structured curriculum data for any newly uploaded course materials.

Milestone B11 introduces an automated, grounded, and transactional knowledge graph extraction pipeline that analyzes indexed `ContentUnit` records and extracts an educational curriculum (Topics, Concepts, and Acyclic Prerequisite DAGs) directly from course materials.

---

## 2. Architectural Design & Invariants

```
                                [ POST /courses/{id}/curriculum/generate ]
                                                    │
                                                    ▼
                                    ┌───────────────────────────────┐
                                    │ curriculum_generator_service  │
                                    └───────────────┬───────────────┘
                                                    │
       ┌────────────────────────────────────────────┼────────────────────────────────────────────┐
       ▼                                            ▼                                            ▼
1. Material Sampling                         2. LLM Extraction                            3. DAG Cycle Pruning
- Bounded token budget (max 16K chars)       - Gemini with academic prompt                - In-memory reachability check
- Head chunks (TOC, intro, preface)          - Topic hierarchy & micro-concepts           - Kahn's topological sort
- Stratified sampling across sources         - Strict grounded output schema              - Guaranteed acyclicity
                                                    │
                                                    ▼
                                     4. Atomic DB Persistence
                                     - Replace vs. Preview modes
                                     - Active attempt guard (HTTP 409)
                                     - Atomic commit / rollback on error
```

### Architectural Invariants & Ownership Boundaries
1. **Reuses B3 Data Models Directly (Zero Migrations):**
   - Uses existing `Topic`, `Concept`, and `ConceptPrerequisite` models.
   - Preserves all cascade delete triggers and integrity constraints.
2. **Deterministic Bounded Sampling:**
   - Instead of unbounded PDF dumps, samples early structural units (TOC, intro) and evenly stratified units across the document, adhering to a strict 16,000-character budget.
3. **Strict DAG Acyclicity (No External Dependencies):**
   - Applies Kahn's topological sorting and BFS reachability checks to guarantee zero circular prerequisite dependencies without needing heavy external graph libraries.
4. **B6 Isolation Preserved:**
   - B11 strictly owns curriculum generation. It does **not** manufacture or alter BKT learner mastery probabilities ($P(L_t)$), respecting B6's on-demand initialization protocol.
5. **Safe Replace Guard:**
   - In `mode="replace"`, verifies whether existing concepts are bound to completed `AssessmentAttempt` records. If active attempts exist, rejects replacement with `HTTP 409 Conflict` to preserve academic history integrity.

---

## 3. API Contracts

### 1. `POST /courses/{course_id}/curriculum/generate`
Extracts and generates an academic curriculum from indexed course materials.

**Request (`CurriculumGenerateRequest`):**
```json
{
  "source_ids": ["f2a043c3-71e1-4a14-b725-eb1a70b99c90"], // Optional filter
  "max_topics": 5,                                        // Upper limit (1-10)
  "concepts_per_topic": 4,                                // Upper limit (1-10)
  "infer_prerequisites": true,                            // Deduce prerequisite arrows
  "mode": "preview"                                       // "preview" or "replace"
}
```

**Response (`CurriculumGenerateResponse`):**
```json
{
  "course_id": "a86cd6d7-5dd1-4a8d-961d-82fa453c685b",
  "mode": "replace",
  "status": "completed",
  "topics_count": 2,
  "concepts_count": 4,
  "prerequisites_count": 2,
  "is_acyclic": true,
  "topics": [
    {
      "id": "c1a2b3c4-...",
      "title": "Complexity Analysis",
      "description": "Techniques for analyzing algorithm efficiency",
      "order_index": 0,
      "concepts": [
        {
          "id": "e5f6g7h8-...",
          "name": "Big-O Notation",
          "description": "Upper bound asymptotic runtime behavior",
          "order_index": 0,
          "evidence": [
            {
              "source_id": "f2a043c3-...",
              "filename": "DSA_Textbook.pdf",
              "page_number": 1,
              "excerpt": "Chapter 1: Asymptotic Analysis. Big-O notation characterizes..."
            }
          ]
        }
      ]
    }
  ],
  "prerequisites": [
    {
      "concept_name": "AVL Trees",
      "prerequisite_name": "Binary Search Trees",
      "concept_id": "...",
      "prerequisite_id": "..."
    }
  ],
  "message": "Curriculum generated and persisted atomically into course."
}
```

### 2. `GET /courses/{course_id}/curriculum/status`
Returns real-time curriculum metrics and acyclicity verification.

**Response (`CurriculumStatusResponse`):**
```json
{
  "course_id": "a86cd6d7-5dd1-4a8d-961d-82fa453c685b",
  "has_curriculum": true,
  "topic_count": 2,
  "concept_count": 4,
  "prerequisite_edge_count": 2,
  "is_acyclic": true,
  "indexed_source_count": 1
}
```

---

## 4. Verification & Test Suite (`backend/test_b11_curriculum_generation.py`)

The test suite covers 17 dedicated scenarios:
1. `test_successful_curriculum_extraction_and_persistence`: Validates complete database population in `replace` mode.
2. `test_preview_mode_does_not_modify_db`: Proves `preview` mode leaves the database untouched.
3. `test_empty_course_material_handling`: Enforces `HTTP 400` without LLM invocation when 0 `ContentUnit`s exist.
4. `test_structured_llm_json_parsing_with_code_fences`: Handles markdown-fenced LLM responses.
5. `test_malformed_llm_output_handling`: Returns `HTTP 502 Bad Gateway` on invalid output.
6. `test_duplicate_concept_normalization`: Normalizes casing and eliminates duplicate concepts across topics.
7. `test_unknown_and_self_prerequisites_rejected`: Drops self-dependencies and ungrounded concept references.
8. `test_cyclic_prerequisite_output_is_never_persisted`: Prunes circular dependency edges to preserve DAG acyclicity.
9. `test_duplicate_prerequisite_edges_removed`: Ensures idempotent edge creation.
10. `test_atomic_rollback_on_persistence_failure`: Proves complete rollback if any database error occurs during commit.
11. `test_safe_replace_updates_existing_curriculum`: Verifies atomic replacement when no attempts exist.
12. `test_replace_mode_guards_against_active_student_attempts`: Enforces `HTTP 409 Conflict` when attempts exist.
13. `test_course_isolation_and_missing_course_404`: Strict 404 security boundaries.
14. `test_source_scoping_and_cross_course_source_rejection`: Enforces source filtering and rejects cross-course sources.
15. `test_large_course_sampling_remains_bounded`: Verifies prompt stays under 16,000 characters for large 100+ unit courses.
16. `test_downstream_smoke_tests_enable_b7_b8_b9`: Validates that generated curriculum directly unlocks B7 Study Planning, B8 Adaptive Practice, and B9 Learner Analytics.
17. `test_curriculum_status_endpoint`: Verifies real-time status reporting and topological acyclicity check.

